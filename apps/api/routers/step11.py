"""Step11 Image Generation API Router.

画像生成フローをTemporal連携で実装。
各フェーズをAPIエンドポイントで処理し、DBに状態を保存、Temporal signalで連携。

フロー:
[Start] POST /start      → Temporal signal送信で画像生成開始
[11A]   POST /settings   → 設定保存、位置分析実行、結果返却
[11B]   GET  /positions  → 位置一覧取得
        POST /positions  → 位置確認/再分析
[11C]   POST /instructions → 指示保存、画像生成実行
[11D]   GET  /images     → 画像一覧取得
        POST /images/retry → 個別リトライ
        POST /images/review → 画像レビュー
[11E]   GET  /preview    → プレビュー取得
        POST /finalize   → 挿入実行、完了（Temporal signal送信）
[Skip]  POST /skip       → スキップ（Temporal signal送信）
[Complete] POST /complete → レガシーrun対応
[AddImages] POST /add-images → 完了済みrunへの画像追加
"""

import base64
import hashlib
import json
import logging
import os
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field, ValidationError, model_validator
from sqlalchemy import select

from apps.api.auth import get_current_user
from apps.api.auth.schemas import AuthUser
from apps.api.db import Artifact as ArtifactModel
from apps.api.db import AuditLogger, Run, Step, TenantDBManager
from apps.api.llm import ImageGenerationConfig, NanoBananaClient
from apps.api.schemas.enums import RunStatus
from apps.api.storage import ArtifactStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/runs/{run_id}/step11", tags=["step11"])

# Temporal設定
TEMPORAL_TASK_QUEUE = os.getenv("TEMPORAL_TASK_QUEUE", "seo-article-queue")

# Temporalクライアント（lazy initialization）
_temporal_client: Any = None


async def get_temporal_client() -> Any:
    """Temporalクライアントを取得（lazy initialization）"""
    global _temporal_client
    if _temporal_client is None:
        from temporalio.client import Client as TemporalClient

        temporal_host = os.getenv("TEMPORAL_HOST", "localhost")
        temporal_port = os.getenv("TEMPORAL_PORT", "7233")
        _temporal_client = await TemporalClient.connect(f"{temporal_host}:{temporal_port}")
    return _temporal_client


# WebSocket manager（lazy initialization）
_ws_manager: Any = None


def get_ws_manager() -> Any:
    """WebSocket managerを取得"""
    global _ws_manager
    if _ws_manager is None:
        from apps.api.main import ws_manager

        _ws_manager = ws_manager
    return _ws_manager


# =============================================================================
# Constants
# =============================================================================

STEP11_IMAGE_COUNT_MIN = 1
STEP11_IMAGE_COUNT_MAX = 10


# =============================================================================
# Pydantic Models
# =============================================================================


class Step11StartInput(BaseModel):
    """画像生成開始入力"""

    enabled: bool = True
    image_count: int = Field(default=3, ge=STEP11_IMAGE_COUNT_MIN, le=STEP11_IMAGE_COUNT_MAX)
    position_request: str | None = None


class Step11SettingsInput(BaseModel):
    """11A: 設定入力"""

    image_count: int = Field(ge=STEP11_IMAGE_COUNT_MIN, le=STEP11_IMAGE_COUNT_MAX, default=3)
    position_request: str = Field(default="", max_length=500)


class ImagePosition(BaseModel):
    """画像挿入位置"""

    article_number: int | None = Field(default=None, description="対象記事番号（1-4）")
    section_title: str
    section_index: int
    position: str = Field(description="before or after")
    source_text: str = Field(default="", description="挿入位置の目印となるテキスト")
    description: str = Field(default="")


class PositionConfirmInput(BaseModel):
    """11B: 位置確認"""

    approved: bool
    modified_positions: list[ImagePosition] | None = None
    reanalyze: bool = False
    reanalyze_request: str = ""


class ImageInstruction(BaseModel):
    """画像ごとの指示"""

    index: int
    instruction: str


class InstructionsInput(BaseModel):
    """11C: 画像指示"""

    instructions: list[ImageInstruction]


class GeneratedImage(BaseModel):
    """生成された画像"""

    index: int
    position: ImagePosition  # 挿入位置
    user_instruction: str  # ユーザーの指示
    generated_prompt: str  # 生成に使用したプロンプト
    image_path: str  # ストレージパス
    image_digest: str = ""  # 画像のハッシュ
    image_base64: str = ""  # Base64エンコードされた画像
    alt_text: str = ""  # 代替テキスト
    mime_type: str = "image/png"  # MIMEタイプ
    file_size: int = 0  # ファイルサイズ
    retry_count: int = 0  # リトライ回数
    accepted: bool = True  # 承認済みか
    status: str = "completed"  # completed, failed, pending
    error: str | None = None
    article_number: int | None = None


class ImageRetryInput(BaseModel):
    """11D: 画像リトライ"""

    index: int
    instruction: str


class ImageReviewItem(BaseModel):
    """11D: 画像レビュー項目"""

    index: int
    accepted: bool
    retry: bool = False
    retry_instruction: str = ""


class ImageReviewInput(BaseModel):
    """11D: 画像レビュー入力"""

    reviews: list[ImageReviewItem]


class FinalizeInput(BaseModel):
    """11E: 完了確認入力"""

    confirmed: bool = True
    restart_from: Literal["11A", "11B", "11C", "11D"] | None = None


class Step11State(BaseModel):
    """Step11 の状態

    VULN-014: List型フィールドのdict/Pydantic混在修正
    - DBから読み込んだdictを適切にPydanticモデルに変換
    - 型の一貫性を保証
    """

    phase: str = "idle"  # idle, 11A, 11B, 11C, 11D, 11E, completed, skipped
    settings: Step11SettingsInput | None = None
    positions: list[ImagePosition] = Field(default_factory=list)
    instructions: list[ImageInstruction] = Field(default_factory=list)
    images: list[GeneratedImage] = Field(default_factory=list)
    analysis_summary: str = ""
    sections: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None

    @model_validator(mode="before")
    @classmethod
    def coerce_list_items(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Ensure list items are properly typed (VULN-014).

        DBから読み込んだデータでlist内の要素がdictのままの場合、
        適切なPydanticモデルに変換する。
        """
        if not isinstance(data, dict):
            return data

        # positions: list[ImagePosition]
        if "positions" in data and isinstance(data["positions"], list):
            data["positions"] = [ImagePosition(**item) if isinstance(item, dict) else item for item in data["positions"]]

        # instructions: list[ImageInstruction]
        if "instructions" in data and isinstance(data["instructions"], list):
            data["instructions"] = [ImageInstruction(**item) if isinstance(item, dict) else item for item in data["instructions"]]

        # images: list[GeneratedImage]
        if "images" in data and isinstance(data["images"], list):
            data["images"] = [GeneratedImage(**item) if isinstance(item, dict) else item for item in data["images"]]

        return data


# =============================================================================
# Dependencies
# =============================================================================

_db_manager: TenantDBManager | None = None
_artifact_store: ArtifactStore | None = None


def get_tenant_db_manager() -> TenantDBManager:
    global _db_manager
    if _db_manager is None:
        _db_manager = TenantDBManager()
    return _db_manager


def get_artifact_store() -> ArtifactStore:
    global _artifact_store
    if _artifact_store is None:
        _artifact_store = ArtifactStore()
    return _artifact_store


async def _load_step11_state(
    run: Run,
    session: Any,
    user: AuthUser,
    *,
    action: str,
) -> Step11State:
    """Load Step11State with validation and reset on corruption.

    If images in DB state show errors but MinIO has successful images,
    sync the MinIO data back to DB state.
    """
    state_data = run.step11_state or {}
    try:
        state = Step11State(**state_data)

        # Check if images need sync from MinIO
        # (DB shows failed but MinIO might have succeeded after retry)
        images_need_sync = any(img.status == "failed" or not img.image_path for img in state.images) if state.images else False

        if images_need_sync:
            store = ArtifactStore()
            try:
                images_path = store.build_path(run.tenant_id, str(run.id), "step11", "images.json")
                images_data = await store.get(images_path)
                if images_data:
                    minio_data = json.loads(images_data.decode("utf-8"))
                    minio_images = minio_data.get("generated_images", [])

                    # Check if MinIO has successful images
                    if minio_images and all(img.get("image_path") for img in minio_images):
                        # Update state with MinIO data
                        for minio_img in minio_images:
                            minio_img["status"] = "generated"
                            minio_img["error"] = None

                        state.images = [GeneratedImage(**img) for img in minio_images]

                        # Persist to DB
                        run.step11_state = state.model_dump()
                        run.updated_at = datetime.now()
                        await session.commit()

                        logger.info(
                            "Synced step11 images from MinIO to DB",
                            extra={"run_id": str(run.id), "image_count": len(minio_images)},
                        )
            except Exception as e:
                logger.warning(
                    f"Failed to sync images from MinIO: {e}",
                    extra={"run_id": str(run.id)},
                )

        return state
    except ValidationError as exc:
        logger.warning(
            "Invalid step11_state detected; resetting to default",
            extra={"run_id": str(run.id), "tenant_id": run.tenant_id, "action": action},
        )
        default_state = Step11State()
        run.step11_state = default_state.model_dump()
        run.updated_at = datetime.now()
        audit = AuditLogger(session)
        await audit.log(
            user_id=user.user_id,
            action="step11_state_reset",
            resource_type="run",
            resource_id=str(run.id),
            details={"source": action, "error": str(exc)},
        )
        return default_state


async def get_run_and_state(
    run_id: str,
    user: AuthUser,
) -> tuple[Run, Step11State]:
    """Run と Step11State を取得"""
    db_manager = get_tenant_db_manager()
    tenant_id = user.tenant_id

    async with db_manager.get_session(tenant_id) as session:
        query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
        result = await session.execute(query)
        run = result.scalar_one_or_none()

        if not run:
            logger.error(f"Run not found: run_id={run_id}, tenant_id={tenant_id}")
            raise HTTPException(status_code=404, detail="Run not found")

        state = await _load_step11_state(run, session, user, action="get_run_and_state")

        return run, state


async def save_step11_state(
    run_id: str,
    tenant_id: str,
    state: Step11State,
) -> None:
    """Step11State を DB に保存"""
    db_manager = get_tenant_db_manager()

    async with db_manager.get_session(tenant_id) as session:
        query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id).with_for_update()
        result = await session.execute(query)
        run = result.scalar_one_or_none()

        if run:
            run.step11_state = state.model_dump()
            run.updated_at = datetime.now()
            await session.commit()


# =============================================================================
# Step11 Core Functions (LLM 呼び出しなし、テスト用モック)
# =============================================================================


async def analyze_positions(
    markdown_content: str,
    settings: Step11SettingsInput,
) -> tuple[list[ImagePosition], str, list[dict[str, Any]]]:
    """位置分析（モック実装）

    TODO: 実際の LLM 呼び出しに置き換え
    """
    # 記事からセクションを抽出
    sections: list[dict[str, Any]] = []
    lines = markdown_content.split("\n")
    current_section = None

    for line in lines:
        if line.startswith("## "):
            current_section = line[3:].strip()
            sections.append({"title": current_section, "level": 2})
        elif line.startswith("### "):
            current_section = line[4:].strip()
            sections.append({"title": current_section, "level": 3})

    # モック: セクション数に応じて位置を提案
    positions = []
    target_count = min(settings.image_count, len(sections))

    for i in range(target_count):
        if i < len(sections):
            section_title = str(sections[i].get("title", ""))
            positions.append(
                ImagePosition(
                    article_number=1,
                    section_title=section_title,
                    section_index=i,
                    position="after",
                    source_text="",
                    description=f"{section_title}に関連する画像",
                )
            )

    summary = f"{len(positions)}箇所の画像挿入位置を提案しました。"

    return positions, summary, sections


def _enhance_image_prompt(base_prompt: str, section_title: str) -> str:
    """画像生成プロンプトを拡張（SEO記事向け）"""
    style_suffix = """

Style: Clean, professional, modern flat design illustration.
Colors: Vibrant but balanced color palette, suitable for blog/web content.
Composition: Clear focal point, good use of negative space.
Quality: High resolution, crisp edges, suitable for web display.
No text or watermarks in the image."""

    # 日本語プロンプトを英語に変換するヒントを追加
    if any(ord(c) > 127 for c in base_prompt):
        # 日本語が含まれている場合
        enhanced = f"Create an illustration for a blog article section titled '{section_title}'. The image should represent: {base_prompt}"
    else:
        enhanced = base_prompt

    return f"{enhanced}{style_suffix}"


# シングルトンの画像生成クライアント
_image_client: NanoBananaClient | None = None


def get_image_client() -> NanoBananaClient:
    """画像生成クライアントを取得（シングルトン）"""
    global _image_client
    if _image_client is None:
        _image_client = NanoBananaClient()
    return _image_client


async def generate_image(
    instruction: str,
    position: ImagePosition,
    run_id: str,
    tenant_id: str,
    index: int,
    retry_count: int = 0,
) -> GeneratedImage:
    """Gemini APIを使用して画像を生成

    Args:
        instruction: ユーザーの画像生成指示
        position: 画像挿入位置
        run_id: 実行ID
        tenant_id: テナントID
        index: 画像インデックス
        retry_count: リトライ回数

    Returns:
        GeneratedImage: 生成された画像情報
    """
    store = get_artifact_store()
    client = get_image_client()

    # 画像生成プロンプトを構築
    base_prompt = instruction or position.description or f"{position.section_title}に関連する画像"
    generated_prompt = _enhance_image_prompt(base_prompt, position.section_title)
    article_number = position.article_number or 1
    position.article_number = article_number

    logger.info(
        f"Generating image for section: {position.section_title}",
        extra={"prompt": generated_prompt[:100], "run_id": run_id, "index": index},
    )

    try:
        # Gemini API で画像生成
        config = ImageGenerationConfig(aspect_ratio="16:9", number_of_images=1)
        result = await client.generate_image(prompt=generated_prompt, config=config)

        if not result.images:
            raise ValueError("No image generated from API")

        # 画像データを取得
        image_bytes = result.images[0]
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        image_digest = hashlib.sha256(image_bytes).hexdigest()

        # MinIO に保存（storage/{tenant}/{run}/step11/images/ に統一）
        # build_nested_path を使用してスラッシュを含むパスを正しく処理
        image_path = store.build_nested_path(tenant_id, run_id, "step11", "images", f"image_{index}.png")
        await store.put(image_bytes, image_path, "image/png")

        logger.info(
            f"Image generated and stored: {image_path}",
            extra={"digest": image_digest[:16], "size": len(image_bytes)},
        )

        return GeneratedImage(
            index=index,
            position=position,
            user_instruction=instruction,
            generated_prompt=generated_prompt,
            image_path=image_path,
            image_digest=image_digest,
            image_base64=image_base64,
            alt_text=base_prompt,
            mime_type="image/png",
            file_size=len(image_bytes),
            retry_count=retry_count,
            accepted=True,
            status="completed",
            article_number=article_number,
        )

    except Exception as e:
        logger.error(
            f"Image generation failed: {e}",
            extra={"run_id": run_id, "index": index, "error": str(e)},
        )
        # エラー時は失敗状態の画像オブジェクトを返す
        return GeneratedImage(
            index=index,
            position=position,
            user_instruction=instruction,
            generated_prompt=generated_prompt,
            image_path="",
            image_digest="",
            image_base64="",
            alt_text=base_prompt,
            mime_type="image/png",
            file_size=0,
            retry_count=retry_count,
            accepted=False,
            status="failed",
            error=str(e),
            article_number=article_number,
        )


def _markdown_to_html(markdown_content: str) -> str:
    """MarkdownをHTMLに変換（簡易実装）"""
    import re

    html = markdown_content

    # 見出し変換
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

    # 太字・イタリック
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

    # 画像（Base64データを含む）- リンクより先に処理すること！
    # パターン: ![alt](data:mime;base64,...) または ![alt](https://...)
    def replace_image(match: re.Match[str]) -> str:
        alt = match.group(1)
        src = match.group(2)
        return f'<img src="{src}" alt="{alt}" style="max-width: 100%; height: auto; margin: 1em 0; display: block;">'

    # Base64画像（data:で始まるURL）
    html = re.sub(r"!\[([^\]]*)\]\((data:image/[^\s)]+)\)", replace_image, html)
    # 通常の画像URL
    html = re.sub(r"!\[([^\]]*)\]\((https?://[^\s)]+)\)", replace_image, html)

    # リンク（画像処理後に実行）
    html = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', html)

    # リスト
    html = re.sub(r"^- (.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)
    html = re.sub(r"(<li>.*</li>\n)+", r"<ul>\g<0></ul>", html)

    # 段落（空行で区切られたテキスト）
    paragraphs = html.split("\n\n")
    processed = []
    for p in paragraphs:
        p = p.strip()
        if p and not p.startswith("<"):
            p = f"<p>{p}</p>"
        processed.append(p)
    html = "\n".join(processed)

    return html


async def insert_images_into_article(
    markdown_content: str,
    images: list[GeneratedImage],
    positions: list[ImagePosition],
    run_id: str | None = None,
) -> tuple[str, str]:
    """画像を記事に挿入

    Args:
        markdown_content: 元のMarkdownコンテンツ
        images: 生成された画像リスト
        positions: 画像挿入位置リスト
        run_id: Run ID（API URL生成用、オプション）

    Returns:
        tuple[str, str]: (画像挿入済みMarkdown, HTML)
    """
    store = ArtifactStore()

    result_md = markdown_content
    lines = result_md.split("\n")

    # 画像をセクションに挿入（セクションタイトルを探して挿入）
    for img in images:
        if img.status == "failed":
            continue  # 生成に失敗した画像はスキップ

        # image_base64 がない場合は image_path から取得
        image_base64 = img.image_base64
        mime_type = img.mime_type or "image/png"

        if not image_base64 and img.image_path:
            try:
                image_data = await store.get_raw(img.image_path)
                if image_data:
                    image_base64 = base64.b64encode(image_data).decode("utf-8")
            except Exception as e:
                logger.warning(f"Failed to load image from path {img.image_path}: {e}")
                continue

        if not image_base64:
            continue  # 画像データがない場合はスキップ

        pos = img.position
        section_title = pos.section_title

        # Base64画像タグを作成
        img_tag = f"\n\n![{img.alt_text}](data:{mime_type};base64,{image_base64})\n\n"

        # セクションタイトルを探して挿入
        inserted = False
        for i, line in enumerate(lines):
            # 見出し行を探す（## または ### で始まる）
            if line.strip().endswith(section_title) or section_title in line:
                if pos.position == "before":
                    # 見出しの前に挿入
                    lines.insert(i, img_tag)
                else:
                    # 見出しの後に挿入（次の段落の後）
                    insert_pos = i + 1
                    # 空行をスキップして次のコンテンツの後に挿入
                    while insert_pos < len(lines) and not lines[insert_pos].strip():
                        insert_pos += 1
                    # 次の見出しまたは段落の後に挿入
                    while insert_pos < len(lines) and lines[insert_pos].strip() and not lines[insert_pos].startswith("#"):
                        insert_pos += 1
                    lines.insert(insert_pos, img_tag)
                inserted = True
                break

        # セクションが見つからなかった場合は末尾に追加
        if not inserted:
            lines.append(img_tag)

    result_md = "\n".join(lines)

    # Markdown を HTML に変換
    html_body = _markdown_to_html(result_md)

    # 完全なHTMLドキュメントを生成
    result_html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.8;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        h1 {{ font-size: 1.8em; margin-top: 1.5em; }}
        h2 {{ font-size: 1.5em; margin-top: 1.3em; border-bottom: 1px solid #eee; padding-bottom: 0.3em; }}
        h3 {{ font-size: 1.2em; margin-top: 1.2em; }}
        p {{ margin: 1em 0; }}
        img {{ max-width: 100%; height: auto; border-radius: 8px; margin: 1.5em 0; display: block; }}
        ul, ol {{ padding-left: 1.5em; }}
        li {{ margin: 0.5em 0; }}
        a {{ color: #0066cc; }}
    </style>
</head>
<body>
{html_body}
</body>
</html>"""

    return result_md, result_html


# =============================================================================
# API Endpoints
# =============================================================================


@router.post("/settings")
async def submit_settings(
    run_id: str,
    data: Step11SettingsInput,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """11A: 設定を送信し、位置分析を実行"""
    logger.info(f"Step11 settings submitted: run_id={run_id}, count={data.image_count}")

    db_manager = get_tenant_db_manager()
    store = get_artifact_store()
    tenant_id = user.tenant_id

    async with db_manager.get_session(tenant_id) as session:
        # Run を取得
        query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id).with_for_update()
        result = await session.execute(query)
        run = result.scalar_one_or_none()

        if not run:
            logger.error(f"Run not found for settings: run_id={run_id}, tenant_id={tenant_id}")
            raise HTTPException(status_code=404, detail="Run not found")

        # Step10 の出力を取得
        try:
            step10_data = await store.get_by_path(tenant_id, run_id, "step10", "output.json")
            if step10_data:
                step10_json = json.loads(step10_data.decode("utf-8"))
                markdown_content = step10_json.get("markdown_content", "")
            else:
                markdown_content = ""
        except Exception as e:
            logger.warning(f"Failed to load step10 output: {e}")
            markdown_content = ""

        if not markdown_content:
            logger.error(f"Step10 article data missing: run_id={run_id}")
            raise HTTPException(status_code=400, detail="Step10 の記事データがありません。先に記事生成を完了してください。")

        # 位置分析を実行
        positions, summary, sections = await analyze_positions(markdown_content, data)

        # 状態を更新
        state = Step11State(
            phase="11B",
            settings=data,
            positions=positions,
            analysis_summary=summary,
            sections=sections,
        )

        run.step11_state = state.model_dump()
        run.current_step = "step11_position_review"
        run.status = RunStatus.WAITING_IMAGE_INPUT.value
        run.updated_at = datetime.now()

        # 監査ログ
        audit = AuditLogger(session)
        await audit.log(
            user_id=user.user_id,
            action="step11_settings_submitted",
            resource_type="run",
            resource_id=run_id,
            details={"image_count": data.image_count},
        )

        await session.commit()

    # Send Temporal signal to start step11 workflow
    try:
        temporal_client = await get_temporal_client()
        workflow_handle = temporal_client.get_workflow_handle(run_id)
        signal_payload = {
            "image_count": data.image_count,
            "position_request": data.position_request or "",
        }
        await workflow_handle.signal("step11_start_settings", signal_payload)
        logger.info("Temporal step11_start_settings signal sent", extra={"run_id": run_id})
    except Exception as sig_error:
        # Log but don't fail - DB state is already updated
        logger.warning(f"Failed to send step11_start_settings signal (may be expected for completed runs): {sig_error}")

    return {
        "success": True,
        "phase": "11B",
        "positions": [p.model_dump() for p in positions],
        "sections": sections,
        "analysis_summary": summary,
    }


@router.get("/state")
async def get_state(
    run_id: str,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Step11の現在の状態を取得（ウィザード復元用）"""
    run, state = await get_run_and_state(run_id, user)

    return {
        "phase": state.phase,
        "settings": state.settings.model_dump() if state.settings else None,
        "positions": [p.model_dump() if isinstance(p, ImagePosition) else p for p in state.positions],
        "instructions": [i.model_dump() if isinstance(i, ImageInstruction) else i for i in state.instructions],
        "images": [img.model_dump() if isinstance(img, GeneratedImage) else img for img in state.images],
        "sections": state.sections,
        "analysis_summary": state.analysis_summary,
        "error": state.error,
    }


@router.get("/positions")
async def get_positions(
    run_id: str,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """11B: 位置一覧を取得"""
    run, state = await get_run_and_state(run_id, user)

    return {
        "positions": [p.model_dump() if isinstance(p, ImagePosition) else p for p in state.positions],
        "sections": state.sections,
        "analysis_summary": state.analysis_summary,
    }


@router.post("/positions")
async def confirm_positions(
    run_id: str,
    data: PositionConfirmInput,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """11B: 位置を確認（承認/編集/再分析）"""
    db_manager = get_tenant_db_manager()
    store = get_artifact_store()
    tenant_id = user.tenant_id

    async with db_manager.get_session(tenant_id) as session:
        query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id).with_for_update()
        result = await session.execute(query)
        run = result.scalar_one_or_none()

        if not run:
            logger.error(f"Run not found for position confirm: run_id={run_id}, tenant_id={tenant_id}")
            raise HTTPException(status_code=404, detail="Run not found")

        state = await _load_step11_state(run, session, user, action="confirm_positions")

        if data.reanalyze:
            # 再分析
            try:
                step10_data = await store.get_by_path(tenant_id, run_id, "step10", "output.json")
                if step10_data:
                    step10_json = json.loads(step10_data.decode("utf-8"))
                    markdown_content = step10_json.get("markdown_content", "")
                else:
                    markdown_content = ""
            except Exception:
                markdown_content = ""

            settings = state.settings or Step11SettingsInput()
            positions, summary, sections = await analyze_positions(markdown_content, settings)

            state.positions = positions
            state.analysis_summary = summary + f" (再分析: {data.reanalyze_request})"
            state.sections = sections

        elif data.modified_positions:
            # 編集された位置を適用
            state.positions = data.modified_positions

        if data.approved and not data.reanalyze:
            # 承認 → 11C へ
            state.phase = "11C"
            run.current_step = "step11_image_instructions"

        run.step11_state = state.model_dump()
        run.updated_at = datetime.now()

        # Temporal signalを送信してWorkflowを再開
        try:
            temporal_client = await get_temporal_client()
            workflow_handle = temporal_client.get_workflow_handle(run_id)
            payload = {
                "approved": data.approved,
                "reanalyze": data.reanalyze,
                "reanalyze_request": data.reanalyze_request,
                "modified_positions": [p.model_dump() if isinstance(p, ImagePosition) else p for p in state.positions]
                if data.modified_positions
                else None,
            }
            await workflow_handle.signal("step11_confirm_positions", payload)
            logger.info("Temporal step11_confirm_positions signal sent", extra={"run_id": run_id})
        except Exception as sig_error:
            logger.error(f"Failed to send step11_confirm_positions signal: {sig_error}", exc_info=True)
            raise HTTPException(status_code=503, detail=f"Failed to send signal to workflow: {sig_error}")

        await session.commit()

    return {
        "success": True,
        "phase": state.phase,
        "positions": [p.model_dump() if isinstance(p, ImagePosition) else p for p in state.positions],
    }


@router.post("/instructions")
async def submit_instructions(
    run_id: str,
    data: InstructionsInput,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """11C: 画像指示を送信し、画像生成を実行"""
    logger.info(f"Step11 instructions submitted: run_id={run_id}")

    db_manager = get_tenant_db_manager()
    tenant_id = user.tenant_id

    async with db_manager.get_session(tenant_id) as session:
        query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id).with_for_update()
        result = await session.execute(query)
        run = result.scalar_one_or_none()

        if not run:
            logger.error(f"Run not found for instructions: run_id={run_id}, tenant_id={tenant_id}")
            raise HTTPException(status_code=404, detail="Run not found")

        state = await _load_step11_state(run, session, user, action="submit_instructions")
        state.instructions = data.instructions

        # 画像生成を実行
        images = []
        positions = [ImagePosition(**p) if isinstance(p, dict) else p for p in state.positions]

        for instr in data.instructions:
            if instr.index < len(positions):
                img = await generate_image(
                    instruction=instr.instruction,
                    position=positions[instr.index],
                    run_id=run_id,
                    tenant_id=tenant_id,
                    index=instr.index,
                )
                images.append(img)

        state.images = images
        state.phase = "11D"

        run.step11_state = state.model_dump()
        run.current_step = "step11_image_review"
        run.updated_at = datetime.now()

        # Temporal signalを送信してWorkflowを再開
        try:
            temporal_client = await get_temporal_client()
            workflow_handle = temporal_client.get_workflow_handle(run_id)
            payload = {
                "instructions": [instr.model_dump() for instr in data.instructions],
            }
            await workflow_handle.signal("step11_submit_instructions", payload)
            logger.info("Temporal step11_submit_instructions signal sent", extra={"run_id": run_id})
        except Exception as sig_error:
            logger.error(f"Failed to send step11_submit_instructions signal: {sig_error}", exc_info=True)
            raise HTTPException(status_code=503, detail=f"Failed to send signal to workflow: {sig_error}")

        await session.commit()

    return {
        "success": True,
        "phase": "11D",
        "images": [img.model_dump() for img in images],
    }


@router.get("/images")
async def get_images(
    run_id: str,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """11D: 画像一覧を取得"""
    run, state = await get_run_and_state(run_id, user)

    # 警告を生成
    warnings: list[str] = []
    if not state.images:
        warnings.append("画像がまだ生成されていません")

    return {
        "images": [img.model_dump() if isinstance(img, GeneratedImage) else img for img in state.images],
        "warnings": warnings,
    }


@router.get("/images/{index}/content")
async def get_image_content(
    run_id: str,
    index: int,
    user: AuthUser = Depends(get_current_user),
) -> Response:
    """11D: 画像バイナリを取得"""
    run, state = await get_run_and_state(run_id, user)

    if index < 0 or index >= len(state.images):
        raise HTTPException(status_code=404, detail="Image not found")

    image = state.images[index]
    image_path = image.image_path if isinstance(image, GeneratedImage) else image.get("image_path")

    if not image_path:
        raise HTTPException(status_code=404, detail="Image path not found")

    # MinIO から画像を取得
    store = ArtifactStore()
    try:
        image_data = await store.get_raw(image_path)
        if not image_data:
            raise HTTPException(status_code=404, detail="Image not found in storage")

        # MIME typeを判定
        mime_type = "image/png"
        if image_path.endswith(".jpg") or image_path.endswith(".jpeg"):
            mime_type = "image/jpeg"
        elif image_path.endswith(".webp"):
            mime_type = "image/webp"

        return Response(content=image_data, media_type=mime_type)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get image from storage: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve image") from e


@router.post("/images/retry")
async def retry_image(
    run_id: str,
    data: ImageRetryInput,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """11D: 画像をリトライ"""
    db_manager = get_tenant_db_manager()
    tenant_id = user.tenant_id

    async with db_manager.get_session(tenant_id) as session:
        query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id).with_for_update()
        result = await session.execute(query)
        run = result.scalar_one_or_none()

        if not run:
            logger.error(f"Run not found for image retry: run_id={run_id}, tenant_id={tenant_id}")
            raise HTTPException(status_code=404, detail="Run not found")

        state = await _load_step11_state(run, session, user, action="retry_image")

        positions = [ImagePosition(**p) if isinstance(p, dict) else p for p in state.positions]

        if data.index >= len(positions):
            logger.error(f"Invalid image index for retry: run_id={run_id}, index={data.index}, positions_count={len(positions)}")
            raise HTTPException(status_code=400, detail="Invalid image index")

        # リトライ上限チェック
        existing_images = [GeneratedImage(**img) if isinstance(img, dict) else img for img in state.images]
        current_image = next((img for img in existing_images if img.index == data.index), None)

        if current_image and current_image.retry_count >= 3:
            logger.warning(f"Retry limit reached: run_id={run_id}, index={data.index}, retry_count={current_image.retry_count}")
            raise HTTPException(status_code=400, detail="リトライ上限（3回）に達しました")

        # 画像を再生成
        new_retry_count = (current_image.retry_count if current_image else 0) + 1
        new_image = await generate_image(
            instruction=data.instruction,
            position=positions[data.index],
            run_id=run_id,
            tenant_id=tenant_id,
            index=data.index,
            retry_count=new_retry_count,
        )

        # 既存の画像を置き換え
        images = [img for img in existing_images if img.index != data.index]
        images.append(new_image)
        images.sort(key=lambda x: x.index)

        state.images = images
        run.step11_state = state.model_dump()
        run.updated_at = datetime.now()
        await session.commit()

    return {
        "success": True,
        "image": new_image.model_dump(),
    }


@router.post("/images/review")
async def review_images(
    run_id: str,
    data: ImageReviewInput,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """11D: 画像レビューを送信"""
    logger.info(f"Step11 image review: run_id={run_id}, reviews={len(data.reviews)}")

    db_manager = get_tenant_db_manager()
    tenant_id = user.tenant_id

    async with db_manager.get_session(tenant_id) as session:
        query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id).with_for_update()
        result = await session.execute(query)
        run = result.scalar_one_or_none()

        if not run:
            logger.error(f"Run not found for image review: run_id={run_id}, tenant_id={tenant_id}")
            raise HTTPException(status_code=404, detail="Run not found")

        state = await _load_step11_state(run, session, user, action="review_images")

        positions = [ImagePosition(**p) if isinstance(p, dict) else p for p in state.positions]
        existing_images = [GeneratedImage(**img) if isinstance(img, dict) else img for img in state.images]

        # リトライが必要な画像を再生成
        has_retries = False
        for review in data.reviews:
            if review.retry and review.index < len(positions):
                has_retries = True
                # 既存画像のリトライ回数を取得
                current_image = next((img for img in existing_images if img.index == review.index), None)
                if current_image and current_image.retry_count >= 3:
                    continue  # リトライ上限に達している場合はスキップ

                new_retry_count = (current_image.retry_count if current_image else 0) + 1
                new_image = await generate_image(
                    instruction=review.retry_instruction,
                    position=positions[review.index],
                    run_id=run_id,
                    tenant_id=tenant_id,
                    index=review.index,
                    retry_count=new_retry_count,
                )

                # 既存の画像を置き換え
                existing_images = [img for img in existing_images if img.index != review.index]
                existing_images.append(new_image)

        # 画像をインデックス順にソート
        existing_images.sort(key=lambda x: x.index)

        # 承認状態を更新
        for review in data.reviews:
            for img in existing_images:
                if img.index == review.index:
                    img.accepted = review.accepted

        state.images = existing_images

        # リトライがなければ次のフェーズへ
        if not has_retries:
            state.phase = "11E"

        run.step11_state = state.model_dump()
        run.updated_at = datetime.now()

        # Temporal signalを送信してWorkflowを再開
        try:
            temporal_client = await get_temporal_client()
            workflow_handle = temporal_client.get_workflow_handle(run_id)
            payload = {
                "reviews": [r.model_dump() for r in data.reviews],
            }
            await workflow_handle.signal("step11_review_images", payload)
            logger.info("Temporal step11_review_images signal sent", extra={"run_id": run_id})
        except Exception as sig_error:
            logger.error(f"Failed to send step11_review_images signal: {sig_error}", exc_info=True)
            raise HTTPException(status_code=503, detail=f"Failed to send signal to workflow: {sig_error}")

        await session.commit()

    return {
        "success": True,
        "has_retries": has_retries,
        "phase": state.phase,
    }


@router.get("/preview")
async def get_preview(
    run_id: str,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """11E: プレビューを取得"""
    run, state = await get_run_and_state(run_id, user)

    store = get_artifact_store()
    tenant_id = user.tenant_id

    # Step10 の記事を取得
    try:
        step10_data = await store.get_by_path(tenant_id, run_id, "step10", "output.json")
        if step10_data:
            step10_json = json.loads(step10_data.decode("utf-8"))
            markdown_content = step10_json.get("markdown_content", "")
        else:
            markdown_content = ""
    except Exception:
        markdown_content = ""

    if not markdown_content:
        return {
            "preview_html": "<p>プレビューを生成できませんでした。記事データがありません。</p>",
            "preview_available": False,
        }

    # 画像を挿入したプレビューを生成
    positions = [ImagePosition(**p) if isinstance(p, dict) else p for p in state.positions]
    images = [GeneratedImage(**img) if isinstance(img, dict) else img for img in state.images]

    result_md, result_html = await insert_images_into_article(markdown_content, images, positions)

    return {
        "preview_html": result_html,
        "preview_available": True,
    }


@router.post("/finalize")
async def finalize_images(
    run_id: str,
    data: FinalizeInput,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """11E: 画像挿入を確定して完了"""
    logger.info(f"Step11 finalize: run_id={run_id}, confirmed={data.confirmed}, restart_from={data.restart_from}")

    db_manager = get_tenant_db_manager()
    store = get_artifact_store()
    tenant_id = user.tenant_id

    async with db_manager.get_session(tenant_id) as session:
        query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id).with_for_update()
        result = await session.execute(query)
        run = result.scalar_one_or_none()

        if not run:
            logger.error(f"Run not found for finalize: run_id={run_id}, tenant_id={tenant_id}")
            raise HTTPException(status_code=404, detail="Run not found")

        # restart_from が指定された場合は状態をリセット
        if data.restart_from:
            restart_phase = data.restart_from
            logger.info(f"Step11 restart from phase: {restart_phase}")

            # フェーズに応じた状態リセット
            state = await _load_step11_state(run, session, user, action="finalize_restart")

            if restart_phase == "11A":
                # 最初からやり直し
                state.phase = "idle"
                state.positions = []
                state.instructions = []
                state.images = []
                state.analysis_summary = ""
            elif restart_phase == "11B":
                # 位置確認からやり直し
                state.phase = "11A"
                state.instructions = []
                state.images = []
            elif restart_phase == "11C":
                # 指示入力からやり直し
                state.phase = "11B"
                state.images = []
            elif restart_phase == "11D":
                # 画像レビューからやり直し
                state.phase = "11C"

            run.step11_state = state.model_dump()
            await session.commit()

            return {"success": True, "restarted_from": restart_phase, "phase": state.phase}

        # 確認されていない場合はエラー
        if not data.confirmed:
            logger.warning(f"Finalize without confirmation: run_id={run_id}")
            raise HTTPException(status_code=400, detail="Confirmation required")

        state = await _load_step11_state(run, session, user, action="finalize")

        # Step10 の記事を取得
        try:
            step10_data = await store.get_by_path(tenant_id, run_id, "step10", "output.json")
            if step10_data:
                step10_json = json.loads(step10_data.decode("utf-8"))
                markdown_content = step10_json.get("markdown_content", "")
            else:
                markdown_content = ""
        except Exception:
            markdown_content = ""

        # 画像を挿入
        positions = [ImagePosition(**p) if isinstance(p, dict) else p for p in state.positions]
        images = [GeneratedImage(**img) if isinstance(img, dict) else img for img in state.images]

        final_md, final_html = await insert_images_into_article(markdown_content, images, positions)

        # 結果を保存
        output_data = {
            "markdown_with_images": final_md,
            "html_with_images": final_html,
            "images": [img.model_dump() for img in images],
            "positions": [p.model_dump() for p in positions],
        }

        # ArtifactStore.build_path()で標準パスを構築（storage/{tenant}/{run}/step11/output.json）
        output_path = store.build_path(tenant_id, run_id, "step11", "output.json")
        await store.put(
            json.dumps(output_data, ensure_ascii=False).encode("utf-8"),
            output_path,
            "application/json",
        )

        # 状態を更新
        # Note: Run status should remain "running" until Step12 completes
        # Only update step11_state, not the overall run status
        state.phase = "completed"
        run.step11_state = state.model_dump()
        run.current_step = "step11"  # Keep at step11, Workflow will advance to step12
        run.status = RunStatus.RUNNING.value  # Keep running, not completed
        run.updated_at = datetime.now()

        # Step11のステータスを更新（step_statusテーブル）
        import uuid

        from apps.api.db import Step as StepModel

        # 既存のStep11レコードを探す
        step_query = select(StepModel).where(StepModel.run_id == run_id, StepModel.step_name == "step11")
        step_result = await session.execute(step_query)
        step_record = step_result.scalar_one_or_none()

        if step_record:
            # 既存レコードを更新
            step_record.status = "completed"
            step_record.completed_at = datetime.now()
        else:
            # 新規レコードを作成
            new_step = StepModel(
                id=str(uuid.uuid4()),
                run_id=run_id,
                step_name="step11",
                status="completed",
                started_at=datetime.now(),
                completed_at=datetime.now(),
                retry_count=0,
            )
            session.add(new_step)

        # 監査ログ
        audit = AuditLogger(session)
        await audit.log(
            user_id=user.user_id,
            action="step11_completed",
            resource_type="run",
            resource_id=run_id,
            details={"image_count": len(images)},
        )

        # Temporal signalを送信してWorkflowを再開
        signal_error = None
        workflow_already_completed = False
        try:
            temporal_client = await get_temporal_client()
            workflow_handle = temporal_client.get_workflow_handle(run_id)
            payload = {
                "confirmed": True,
                "image_count": len(images),
            }
            await workflow_handle.signal("step11_finalize", payload)
            logger.info("Temporal step11_finalize signal sent", extra={"run_id": run_id})
        except Exception as sig_error:
            error_msg = str(sig_error)
            # ワークフローが既に完了している場合は、成果物が保存されていれば成功とする
            if "already completed" in error_msg.lower() or "workflow execution already completed" in error_msg.lower():
                workflow_already_completed = True
                logger.warning(
                    f"Workflow already completed, but artifacts saved successfully: {sig_error}",
                    extra={"run_id": run_id},
                )
                # エラー情報をアーティファクトとして保存
                error_artifact = {
                    "type": "workflow_signal_error",
                    "message": error_msg,
                    "timestamp": datetime.now().isoformat(),
                    "context": "step11_finalize signal failed but artifacts were saved",
                    "recovery_action": "artifacts_preserved",
                }
                error_path = store.build_path(tenant_id, run_id, "step11", "signal_error.json")
                try:
                    await store.put(
                        json.dumps(error_artifact, ensure_ascii=False).encode("utf-8"),
                        error_path,
                        "application/json",
                    )
                    logger.info(f"Signal error artifact saved: {error_path}")
                except Exception as store_error:
                    logger.warning(f"Failed to save signal error artifact: {store_error}")
            else:
                # それ以外のエラーは従来通り例外を投げる
                logger.error(f"Failed to send step11_finalize signal: {sig_error}", exc_info=True)
                signal_error = sig_error

        # シグナルエラーがあり、ワークフロー完了以外の理由の場合はエラーを投げる
        if signal_error and not workflow_already_completed:
            raise HTTPException(status_code=503, detail=f"Failed to send signal to workflow: {signal_error}")

        await session.commit()

    return {
        "success": True,
        "phase": "completed",
        "output_path": output_path,
        "workflow_already_completed": workflow_already_completed,
    }


@router.post("/skip")
async def skip_image_generation(
    run_id: str,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """画像生成をスキップ"""
    db_manager = get_tenant_db_manager()
    tenant_id = user.tenant_id

    async with db_manager.get_session(tenant_id) as session:
        query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
        result = await session.execute(query)
        run = result.scalar_one_or_none()

        if not run:
            logger.error(f"Run not found for skip: run_id={run_id}, tenant_id={tenant_id}")
            raise HTTPException(status_code=404, detail="Run not found")

        state = Step11State(phase="skipped")
        run.step11_state = state.model_dump()
        # Note: Run status should remain "running" until Step12 completes
        # Only update step11_state, not the overall run status
        run.current_step = "step11"  # Keep at step11, Workflow will advance to step12
        run.status = RunStatus.RUNNING.value  # Keep running, not completed
        run.updated_at = datetime.now()

        # 監査ログ
        audit = AuditLogger(session)
        await audit.log(
            user_id=user.user_id,
            action="step11_skipped",
            resource_type="run",
            resource_id=run_id,
            details={},
        )

        # Temporal signalを送信してWorkflowを再開
        try:
            temporal_client = await get_temporal_client()
            workflow_handle = temporal_client.get_workflow_handle(run_id)
            await workflow_handle.signal("step11_skip")
            logger.info("Temporal step11_skip signal sent", extra={"run_id": run_id})
        except Exception as sig_error:
            logger.error(f"Failed to send step11_skip signal: {sig_error}", exc_info=True)
            raise HTTPException(status_code=503, detail=f"Failed to send signal to workflow: {sig_error}")

        await session.commit()

    return {"success": True, "phase": "skipped"}


@router.post("/regenerate")
async def regenerate_output(
    run_id: str,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """完了済みのStep11出力を再生成（HTML変換の修正適用）"""
    logger.info(f"Step11 regenerate: run_id={run_id}")

    db_manager = get_tenant_db_manager()
    store = get_artifact_store()
    tenant_id = user.tenant_id

    async with db_manager.get_session(tenant_id) as session:
        query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
        result = await session.execute(query)
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        state = await _load_step11_state(run, session, user, action="regenerate_output")

        if state.phase != "completed":
            raise HTTPException(status_code=400, detail="Step11 is not completed yet")

        # Step10 の記事を取得
        try:
            step10_data = await store.get_by_path(tenant_id, run_id, "step10", "output.json")
            if step10_data:
                step10_json = json.loads(step10_data.decode("utf-8"))
                markdown_content = step10_json.get("markdown_content", "")
            else:
                markdown_content = ""
        except Exception:
            markdown_content = ""

        if not markdown_content:
            raise HTTPException(status_code=400, detail="Step10 の記事データがありません")

        # 画像を再挿入してHTMLを再生成
        positions = [ImagePosition(**p) if isinstance(p, dict) else p for p in state.positions]
        images = [GeneratedImage(**img) if isinstance(img, dict) else img for img in state.images]

        final_md, final_html = await insert_images_into_article(markdown_content, images, positions)

        # 結果を保存
        output_data = {
            "markdown_with_images": final_md,
            "html_with_images": final_html,
            "images": [img.model_dump() for img in images],
            "positions": [p.model_dump() for p in positions],
        }

        # ArtifactStore.build_path()で標準パスを構築（storage/{tenant}/{run}/step11/output.json）
        output_path = store.build_path(tenant_id, run_id, "step11", "output.json")
        await store.put(
            json.dumps(output_data, ensure_ascii=False).encode("utf-8"),
            output_path,
            "application/json",
        )

        # 監査ログ
        audit = AuditLogger(session)
        await audit.log(
            user_id=user.user_id,
            action="step11_regenerated",
            resource_type="run",
            resource_id=run_id,
            details={"image_count": len(images)},
        )

        await session.commit()

    return {
        "success": True,
        "output_path": output_path,
        "message": "HTML出力を再生成しました",
    }


# =============================================================================
# Temporal連携エンドポイント（main.pyから移植）
# =============================================================================


@router.post("/start")
async def start_image_generation(
    run_id: str,
    data: Step11StartInput,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, bool | str]:
    """画像生成を開始（Temporal signal送信）"""
    db_manager = get_tenant_db_manager()
    tenant_id = user.tenant_id

    logger.info(
        "Starting image generation",
        extra={
            "run_id": run_id,
            "tenant_id": tenant_id,
            "enabled": data.enabled,
            "image_count": data.image_count,
            "user_id": user.user_id,
        },
    )

    try:
        async with db_manager.get_session(tenant_id) as session:
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id).with_for_update()
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            allowed_statuses = [RunStatus.WAITING_APPROVAL.value, RunStatus.WAITING_IMAGE_INPUT.value]
            if run.status not in allowed_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"Run is not waiting for image generation decision (current status: {run.status})",
                )

            # 監査ログ
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="start_image_generation",
                resource_type="run",
                resource_id=run_id,
                details={
                    "enabled": data.enabled,
                    "image_count": data.image_count,
                    "position_request": data.position_request,
                },
            )

            # Temporal signalを送信
            try:
                temporal_client = await get_temporal_client()
                workflow_handle = temporal_client.get_workflow_handle(run_id)
                config = {
                    "enabled": data.enabled,
                    "step11_image_count": data.image_count,
                    "step11_position_request": data.position_request or "",
                }
                await workflow_handle.signal("start_image_generation", config)
                logger.info("Temporal start_image_generation signal sent", extra={"run_id": run_id})
            except Exception as sig_error:
                logger.error(f"Failed to send start_image_generation signal: {sig_error}", exc_info=True)
                raise HTTPException(status_code=503, detail=f"Failed to send signal to workflow: {sig_error}")

            # Run状態を更新
            run.status = RunStatus.RUNNING.value
            run.updated_at = datetime.now()

            await session.commit()

            # WebSocket broadcast
            try:
                ws_manager = get_ws_manager()
                await ws_manager.broadcast_run_update(
                    run_id=run_id,
                    event_type="run.image_generation_started",
                    status=RunStatus.RUNNING.value,
                    tenant_id=tenant_id,
                )
            except Exception as ws_error:
                logger.warning(f"WebSocket broadcast failed: {ws_error}")

            return {"success": True, "message": "Image generation started"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start image generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to start image generation") from e


@router.post("/complete")
async def complete_step11(
    run_id: str,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, bool]:
    """Step11を完了としてマーク（レガシーrun対応）

    既にStep11実装前に完了したrunや、画像生成をスキップしたrunに対して
    Step11を完了状態にマークする。
    """
    db_manager = get_tenant_db_manager()
    tenant_id = user.tenant_id

    logger.info(
        "Marking step11 as completed",
        extra={"run_id": run_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    try:
        async with db_manager.get_session(tenant_id) as session:
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id).with_for_update()
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # 既存ステップを取得
            all_steps_query = select(Step).where(Step.run_id == run_id)
            all_steps_result = await session.execute(all_steps_query)
            existing_steps = {s.step_name: s for s in all_steps_result.scalars().all()}

            # レガシーrun対応: completedだがステップがない場合はバックフィル
            if run.status == RunStatus.COMPLETED.value and len(existing_steps) == 0:
                import uuid

                all_step_names = [
                    "step-1",
                    "step0",
                    "step1",
                    "step2",
                    "step3",
                    "step3a",
                    "step3b",
                    "step3c",
                    "step4",
                    "step5",
                    "step6",
                    "step6.5",
                    "step7a",
                    "step7b",
                    "step8",
                    "step9",
                    "step10",
                ]
                now = datetime.now()
                for step_name in all_step_names:
                    step = Step(
                        id=str(uuid.uuid4()),
                        run_id=run_id,
                        step_name=step_name,
                        status="completed",
                        started_at=now,
                        completed_at=now,
                        retry_count=0,
                    )
                    session.add(step)
                    existing_steps[step_name] = step
                logger.info("Backfilled missing steps for legacy run", extra={"run_id": run_id})

            # Step11レコードを更新/作成
            step11 = existing_steps.get("step11")
            if step11:
                step11.status = "completed"
                step11.completed_at = datetime.now()
            else:
                import uuid

                step11 = Step(
                    id=str(uuid.uuid4()),
                    run_id=run_id,
                    step_name="step11",
                    status="completed",
                    started_at=datetime.now(),
                    completed_at=datetime.now(),
                    retry_count=0,
                )
                session.add(step11)

            # 監査ログ
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="complete_step11",
                resource_type="run",
                resource_id=run_id,
                details={"skipped": True},
            )

            await session.flush()

            # WebSocket broadcast
            try:
                ws_manager = get_ws_manager()
                await ws_manager.broadcast_run_update(
                    run_id=run_id,
                    event_type="step_completed",
                    status=run.status,
                    current_step="step11",
                    tenant_id=tenant_id,
                )
            except Exception as ws_error:
                logger.warning(f"WebSocket broadcast failed: {ws_error}")

            await session.commit()
            return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete step11: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to complete step11") from e


@router.post("/add-images")
async def add_images_to_completed_run(
    run_id: str,
    data: Step11SettingsInput,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, bool | str]:
    """完了済みrunに画像を追加

    既に完了したrunに対して画像生成を実行する。
    ImageAdditionWorkflowを起動して画像生成フローを開始する。
    """
    db_manager = get_tenant_db_manager()
    store = get_artifact_store()
    tenant_id = user.tenant_id

    logger.info(
        "Adding images to completed run",
        extra={
            "run_id": run_id,
            "tenant_id": tenant_id,
            "image_count": data.image_count,
            "user_id": user.user_id,
        },
    )

    try:
        async with db_manager.get_session(tenant_id) as session:
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id).with_for_update()
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            if run.status != RunStatus.COMPLETED.value:
                raise HTTPException(
                    status_code=400,
                    detail=f"Run must be completed to add images (current status: {run.status})",
                )

            # 既存のstep11アーティファクトを確認
            step11_query = select(Step).where(Step.run_id == run_id, Step.step_name == "step11")
            step11_result = await session.execute(step11_query)
            step11 = step11_result.scalar_one_or_none()

            if step11 and step11.status == "completed":
                artifact_query = select(ArtifactModel).where(ArtifactModel.run_id == run_id, ArtifactModel.step_id == step11.id)
                artifact_result = await session.execute(artifact_query)
                artifacts = artifact_result.scalars().all()

                if artifacts and len(artifacts) > 0:
                    logger.warning(
                        "Attempting to add images to run that already has step11 artifacts",
                        extra={"run_id": run_id, "artifact_count": len(artifacts)},
                    )

            # Run状態を更新
            run.status = RunStatus.WAITING_APPROVAL.value
            run.current_step = "waiting_image_generation"
            run.updated_at = datetime.now()

            # Step11をリセット/作成
            if step11:
                step11.status = "pending"
                step11.started_at = None
                step11.completed_at = None
            else:
                import uuid

                step11 = Step(
                    id=str(uuid.uuid4()),
                    run_id=run_id,
                    step_name="step11",
                    status="pending",
                    retry_count=0,
                )
                session.add(step11)

            # 監査ログ
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="step11_add_images_initiated",
                resource_type="run",
                resource_id=run_id,
                details={
                    "image_count": data.image_count,
                    "position_request": data.position_request,
                    "previous_status": "completed",
                },
            )

            await session.flush()

            # 設定をMinIOに保存（storage/{tenant}/{run}/step11/ に統一）
            settings_path = store.build_path(tenant_id, run_id, "step11", "settings.json")
            settings_data = {
                "image_count": data.image_count,
                "position_request": data.position_request,
                "initiated_at": datetime.now().isoformat(),
                "initiated_by": user.user_id,
            }
            await store.put(json.dumps(settings_data).encode("utf-8"), settings_path, "application/json")

            # Step10出力を取得
            try:
                step10_data = await store.get_by_path(tenant_id, run_id, "step10")
                if step10_data:
                    step10_output = json.loads(step10_data.decode("utf-8"))
                    article_markdown = step10_output.get("markdown", "")
                else:
                    article_markdown = ""
            except Exception as e:
                logger.warning(f"Failed to read step10 output: {e}")
                article_markdown = ""

            # ImageAdditionWorkflowを起動
            try:
                temporal_client = await get_temporal_client()
                workflow_config = {
                    "image_count": data.image_count,
                    "position_request": data.position_request,
                    "article_markdown": article_markdown,
                }

                await temporal_client.start_workflow(
                    "ImageAdditionWorkflow",
                    args=[tenant_id, run_id, workflow_config],
                    id=f"image-addition-{run_id}",
                    task_queue=TEMPORAL_TASK_QUEUE,
                )

                logger.info(
                    "Started ImageAdditionWorkflow",
                    extra={
                        "run_id": run_id,
                        "workflow_id": f"image-addition-{run_id}",
                    },
                )
            except Exception as wf_error:
                logger.error(f"Failed to start ImageAdditionWorkflow: {wf_error}", exc_info=True)
                raise HTTPException(status_code=503, detail=f"Failed to start workflow: {wf_error}")

            # WebSocket broadcast
            try:
                ws_manager = get_ws_manager()
                await ws_manager.broadcast_run_update(
                    run_id=run_id,
                    event_type="run.add_images_initiated",
                    status=RunStatus.RUNNING.value,
                    current_step="step11_analyzing",
                    tenant_id=tenant_id,
                )
            except Exception as ws_error:
                logger.warning(f"WebSocket broadcast failed: {ws_error}")

            await session.commit()

            return {
                "success": True,
                "message": "Image generation workflow started.",
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add images to completed run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to initiate image generation") from e
