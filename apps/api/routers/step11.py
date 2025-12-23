"""Step11 Image Generation API Router.

Temporal を使わないシンプルな API 方式で画像生成フローを実装。
各フェーズを API エンドポイントで直接処理し、DB に状態を保存。

フロー:
[11A] POST /settings   → 設定保存、位置分析実行、結果返却
[11B] GET  /positions  → 位置一覧取得
      POST /positions  → 位置確認/再分析
[11C] POST /instructions → 指示保存、画像生成実行
[11D] GET  /images     → 画像一覧取得
      POST /images/retry → 個別リトライ
[11E] POST /finalize   → 挿入実行、完了
"""

import base64
import hashlib
import json
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from apps.api.auth import get_current_user
from apps.api.auth.schemas import AuthUser
from apps.api.db import AuditLogger, Run, TenantDBManager
from apps.api.llm import ImageGenerationConfig, NanoBananaClient
from apps.api.storage import ArtifactStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/runs/{run_id}/step11", tags=["step11"])


# =============================================================================
# Pydantic Models
# =============================================================================


class Step11SettingsInput(BaseModel):
    """11A: 設定入力"""

    image_count: int = Field(ge=1, le=10, default=3)
    position_request: str = Field(default="", max_length=500)


class ImagePosition(BaseModel):
    """画像挿入位置"""

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


class Step11State(BaseModel):
    """Step11 の状態"""

    phase: str = "idle"  # idle, 11A, 11B, 11C, 11D, 11E, completed, skipped
    settings: Step11SettingsInput | None = None
    positions: list[ImagePosition] = []
    instructions: list[ImageInstruction] = []
    images: list[GeneratedImage] = []
    analysis_summary: str = ""
    sections: list[dict[str, Any]] = []
    error: str | None = None


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
            raise HTTPException(status_code=404, detail="Run not found")

        # step11_state を取得（なければデフォルト）
        state_data = run.step11_state or {}
        state = Step11State(**state_data)

        return run, state


async def save_step11_state(
    run_id: str,
    tenant_id: str,
    state: Step11State,
) -> None:
    """Step11State を DB に保存"""
    db_manager = get_tenant_db_manager()

    async with db_manager.get_session(tenant_id) as session:
        query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
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

        # MinIO に保存
        image_path = f"tenants/{tenant_id}/runs/{run_id}/step11/images/image_{index}.png"
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
) -> tuple[str, str]:
    """画像を記事に挿入

    Args:
        markdown_content: 元のMarkdownコンテンツ
        images: 生成された画像リスト
        positions: 画像挿入位置リスト

    Returns:
        tuple[str, str]: (画像挿入済みMarkdown, HTML)
    """

    result_md = markdown_content
    lines = result_md.split("\n")

    # 画像をセクションに挿入（セクションタイトルを探して挿入）
    for img in images:
        if not img.image_base64 or img.status == "failed":
            continue  # 生成に失敗した画像はスキップ

        pos = img.position
        section_title = pos.section_title

        # Base64画像タグを作成
        img_tag = f"\n\n![{img.alt_text}](data:{img.mime_type};base64,{img.image_base64})\n\n"

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
        query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
        result = await session.execute(query)
        run = result.scalar_one_or_none()

        if not run:
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
        run.status = "waiting_image_input"
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

    return {
        "success": True,
        "phase": "11B",
        "positions": [p.model_dump() for p in positions],
        "sections": sections,
        "analysis_summary": summary,
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
        query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
        result = await session.execute(query)
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        state_data = run.step11_state or {}
        state = Step11State(**state_data)

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
        query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
        result = await session.execute(query)
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        state_data = run.step11_state or {}
        state = Step11State(**state_data)
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
        query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
        result = await session.execute(query)
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        state_data = run.step11_state or {}
        state = Step11State(**state_data)

        positions = [ImagePosition(**p) if isinstance(p, dict) else p for p in state.positions]

        if data.index >= len(positions):
            raise HTTPException(status_code=400, detail="Invalid image index")

        # リトライ上限チェック
        existing_images = [GeneratedImage(**img) if isinstance(img, dict) else img for img in state.images]
        current_image = next((img for img in existing_images if img.index == data.index), None)

        if current_image and current_image.retry_count >= 3:
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
        query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
        result = await session.execute(query)
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        state_data = run.step11_state or {}
        state = Step11State(**state_data)

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
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """11E: 画像挿入を確定して完了"""
    logger.info(f"Step11 finalize: run_id={run_id}")

    db_manager = get_tenant_db_manager()
    store = get_artifact_store()
    tenant_id = user.tenant_id

    async with db_manager.get_session(tenant_id) as session:
        query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
        result = await session.execute(query)
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        state_data = run.step11_state or {}
        state = Step11State(**state_data)

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

        output_path = f"tenants/{tenant_id}/runs/{run_id}/step11/output.json"
        await store.put(
            json.dumps(output_data, ensure_ascii=False).encode("utf-8"),
            output_path,
            "application/json",
        )

        # 状態を更新
        state.phase = "completed"
        run.step11_state = state.model_dump()
        run.current_step = "completed"
        run.status = "completed"
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

        await session.commit()

    return {
        "success": True,
        "phase": "completed",
        "output_path": output_path,
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
            raise HTTPException(status_code=404, detail="Run not found")

        state = Step11State(phase="skipped")
        run.step11_state = state.model_dump()
        run.current_step = "completed"
        run.status = "completed"
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

        state_data = run.step11_state or {}
        state = Step11State(**state_data)

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

        output_path = f"tenants/{tenant_id}/runs/{run_id}/step11/output.json"
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
