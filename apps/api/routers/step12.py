"""Step12 WordPress HTML Generation API Router.

WordPress用HTML（Gutenbergブロック形式）のプレビューとダウンロードを提供。
step10の記事とstep11の画像を組み合わせてWordPress用HTMLを生成。
"""

import json
import logging
import zipfile
from datetime import datetime
from io import BytesIO
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from apps.api.auth import get_current_user
from apps.api.auth.schemas import AuthUser
from apps.api.db import AuditLogger, Run, Step, TenantDBManager
from apps.api.storage import ArtifactStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/runs/{run_id}/step12", tags=["step12"])


# =============================================================================
# Pydantic Models
# =============================================================================


class ArticleMetadata(BaseModel):
    """記事メタデータ.

    VULN-018: ダウンロード時は必須フィールドが設定されている必要がある
    - titleは必須（空文字でもWordPress投稿は可能だが推奨されない）
    - slugは必須（WordPressのURL生成に必要）
    """

    title: str = ""
    meta_description: str = ""
    focus_keyword: str = ""
    word_count: int = 0
    slug: str = ""

    def is_complete_for_download(self) -> bool:
        """Check if metadata is complete for download/export."""
        return bool(self.title and self.slug)

    def validate_for_download(self) -> list[str]:
        """Validate metadata for download and return list of issues.

        VULN-018: ダウンロード前の検証
        """
        issues: list[str] = []
        if not self.title:
            issues.append("title is required")
        if not self.slug:
            issues.append("slug is required")
        if self.word_count <= 0:
            issues.append("word_count should be positive")
        return issues


class WordPressArticleResponse(BaseModel):
    """WordPress記事レスポンス."""

    article_number: int
    filename: str
    gutenberg_blocks: str
    metadata: ArticleMetadata = Field(default_factory=ArticleMetadata)


class Step12PreviewResponse(BaseModel):
    """Step12プレビューレスポンス."""

    articles: list[WordPressArticleResponse]
    common_assets: dict[str, Any] = Field(default_factory=dict)
    generation_metadata: dict[str, Any] = Field(default_factory=dict)
    preview_available: bool = True


class Step12StatusResponse(BaseModel):
    """Step12ステータスレスポンス."""

    status: str
    phase: str
    articles_count: int = 0
    generated_at: str | None = None


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


# =============================================================================
# Helper Functions
# =============================================================================


def _markdown_to_html(markdown_content: str) -> str:
    """MarkdownをHTMLに変換（簡易実装）."""
    import re

    html = markdown_content

    # 見出し変換
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

    # 太字・イタリック
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)

    # リンク
    html = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', html)

    # リスト
    html = re.sub(r"^- (.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)
    html = re.sub(r"(<li>.*</li>\n)+", r"<ul>\g<0></ul>", html)

    # 段落
    paragraphs = html.split("\n\n")
    processed = []
    for p in paragraphs:
        p = p.strip()
        if p and not p.startswith("<"):
            p = f"<p>{p}</p>"
        processed.append(p)
    html = "\n".join(processed)

    return html


def _convert_to_gutenberg(html_content: str) -> str:
    """HTMLをWordPress Gutenbergブロック形式に変換."""
    lines = html_content.split("\n")
    gutenberg_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 見出しブロック
        if line.startswith("<h1"):
            gutenberg_lines.append('<!-- wp:heading {"level":1} -->')
            gutenberg_lines.append(line)
            gutenberg_lines.append("<!-- /wp:heading -->")
        elif line.startswith("<h2"):
            gutenberg_lines.append("<!-- wp:heading -->")
            gutenberg_lines.append(line)
            gutenberg_lines.append("<!-- /wp:heading -->")
        elif line.startswith("<h3"):
            gutenberg_lines.append('<!-- wp:heading {"level":3} -->')
            gutenberg_lines.append(line)
            gutenberg_lines.append("<!-- /wp:heading -->")
        # 段落ブロック
        elif line.startswith("<p"):
            gutenberg_lines.append("<!-- wp:paragraph -->")
            gutenberg_lines.append(line)
            gutenberg_lines.append("<!-- /wp:paragraph -->")
        # リストブロック
        elif line.startswith("<ul"):
            gutenberg_lines.append("<!-- wp:list -->")
            gutenberg_lines.append(line)
            gutenberg_lines.append("<!-- /wp:list -->")
        elif line.startswith("<ol"):
            gutenberg_lines.append('<!-- wp:list {"ordered":true} -->')
            gutenberg_lines.append(line)
            gutenberg_lines.append("<!-- /wp:list -->")
        # 画像ブロック
        elif line.startswith("<img") or line.startswith("<figure"):
            gutenberg_lines.append("<!-- wp:image -->")
            gutenberg_lines.append(f'<figure class="wp-block-image">{line}</figure>')
            gutenberg_lines.append("<!-- /wp:image -->")
        else:
            gutenberg_lines.append(line)

    return "\n".join(gutenberg_lines)


async def _get_step12_data(
    tenant_id: str,
    run_id: str,
    store: ArtifactStore,
) -> dict[str, Any] | None:
    """Step12の出力データを取得.

    Uses ArtifactStore.get_by_path for direct path-based retrieval.
    """
    try:
        # Use get_by_path for direct path-based retrieval (not get which expects ArtifactRef)
        data = await store.get_by_path(tenant_id, run_id, "step12", "output.json")
        if data:
            try:
                return json.loads(data.decode("utf-8"))
            except json.JSONDecodeError as e:
                logger.error(f"Corrupted step12 output JSON for run {run_id}: {e}")
                raise HTTPException(status_code=500, detail="Step12 data corrupted") from e
    except Exception as e:
        logger.warning(f"Failed to load step12 output: {e}")
    return None


async def _ensure_step12_completed(session: Any, run_id: str) -> None:
    """Ensure step12 is completed when step records exist."""
    step_query = select(Step).where(Step.run_id == run_id, Step.step_name == "step12")
    step_result = await session.execute(step_query)
    step_record = step_result.scalar_one_or_none()

    if step_record and step_record.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Step12 has not been completed. Please wait for workflow completion.",
        )


async def _generate_wordpress_html_from_step10(
    tenant_id: str,
    run_id: str,
    store: ArtifactStore,
) -> dict[str, Any]:
    """Step10の出力からWordPress用HTMLを生成."""
    # Step10の出力を取得
    try:
        step10_data = await store.get_by_path(tenant_id, run_id, "step10", "output.json")
        if not step10_data:
            raise ValueError("Step10 output not found")
        step10_json = json.loads(step10_data.decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Failed to load step10 output: {e}") from e

    # Step11の出力を取得（オプション）
    step11_json = {}
    try:
        step11_data = await store.get_by_path(tenant_id, run_id, "step11", "output.json")
        if step11_data:
            step11_json = json.loads(step11_data.decode("utf-8"))
    except Exception:
        pass

    # 記事データを取得
    articles_data = step10_json.get("articles", [])

    # 後方互換性: 単一記事の場合
    if not articles_data and step10_json.get("markdown_content"):
        articles_data = [
            {
                "article_number": 1,
                "title": step10_json.get("article_title", ""),
                "content": step10_json.get("markdown_content", ""),
                "html_content": step10_json.get("html_content", ""),
                "meta_description": step10_json.get("meta_description", ""),
            }
        ]

    # 各記事をWordPress用HTMLに変換
    wordpress_articles = []
    for article in articles_data:
        article_number = article.get("article_number", 1)
        title = article.get("title", "")
        content = article.get("content", "")
        html_content = article.get("html_content", "")
        meta_description = article.get("meta_description", "")

        # HTMLがなければMarkdownから変換
        if not html_content and content:
            html_content = _markdown_to_html(content)

        # Gutenbergブロック形式に変換
        gutenberg_html = _convert_to_gutenberg(html_content)

        wordpress_articles.append(
            {
                "article_number": article_number,
                "filename": f"article_{article_number}.html",
                "gutenberg_blocks": gutenberg_html,
                "metadata": {
                    "title": title,
                    "meta_description": meta_description,
                    "focus_keyword": step10_json.get("keyword", ""),
                    "word_count": len(content) if content else len(html_content),
                    "slug": "",
                },
            }
        )

    return {
        "articles": wordpress_articles,
        "common_assets": {
            "css_classes": [
                "wp-block-paragraph",
                "wp-block-heading",
                "wp-block-image",
                "wp-block-list",
            ],
            "recommended_plugins": ["Yoast SEO"],
        },
        "generation_metadata": {
            "generated_at": datetime.now().isoformat(),
            "wordpress_version_target": "6.0+",
            "total_articles": len(wordpress_articles),
            "total_images": len(step11_json.get("images", [])),
        },
    }


# =============================================================================
# API Endpoints
# =============================================================================


@router.get("/status")
async def get_status(
    run_id: str,
    user: AuthUser = Depends(get_current_user),
) -> Step12StatusResponse:
    """Step12のステータスを取得."""
    db_manager = get_tenant_db_manager()
    store = get_artifact_store()
    tenant_id = user.tenant_id

    async with db_manager.get_session(tenant_id) as session:
        query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
        result = await session.execute(query)
        run = result.scalar_one_or_none()

        if not run:
            logger.error(f"Run not found for status: run_id={run_id}, tenant_id={tenant_id}")
            raise HTTPException(status_code=404, detail="Run not found")

    # Step12の出力を確認
    step12_data = await _get_step12_data(tenant_id, run_id, store)

    if step12_data:
        return Step12StatusResponse(
            status="completed",
            phase="completed",
            articles_count=len(step12_data.get("articles", [])),
            generated_at=step12_data.get("generation_metadata", {}).get("generated_at"),
        )

    # Step10の出力があればpending
    try:
        step10_data = await store.get_by_path(tenant_id, run_id, "step10", "output.json")
        if step10_data:
            return Step12StatusResponse(
                status="pending",
                phase="ready_to_generate",
                articles_count=0,
            )
    except Exception:
        pass

    return Step12StatusResponse(
        status="not_ready",
        phase="waiting_for_step10",
        articles_count=0,
    )


@router.get("/preview")
async def get_preview(
    run_id: str,
    article: int | None = Query(default=None, ge=1, le=4, description="記事番号（1-4）"),
    user: AuthUser = Depends(get_current_user),
) -> Step12PreviewResponse:
    """Step12のプレビューを取得.

    Args:
        run_id: ワークフロー実行ID
        article: 記事番号（省略時は全記事）
        user: 認証ユーザー
    """
    db_manager = get_tenant_db_manager()
    store = get_artifact_store()
    tenant_id = user.tenant_id

    async with db_manager.get_session(tenant_id) as session:
        query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
        result = await session.execute(query)
        run = result.scalar_one_or_none()

        if not run:
            logger.error(f"Run not found for preview: run_id={run_id}, tenant_id={tenant_id}")
            raise HTTPException(status_code=404, detail="Run not found")

        # Step12完了チェック
        await _ensure_step12_completed(session, run_id)
        step12_data = await _get_step12_data(tenant_id, run_id, store)

        if not step12_data:
            logger.warning(f"Step12 not completed yet: run_id={run_id}")
            raise HTTPException(
                status_code=400,
                detail="Step12 has not been completed. Please wait for workflow completion.",
            )

        # 監査ログを記録
        audit = AuditLogger(session)
        await audit.log(
            user_id=user.user_id,
            action="preview",
            resource_type="step12",
            resource_id=run_id,
            details={
                "articles_count": len(step12_data.get("articles", [])),
                "article_filter": article,
            },
        )
        await session.commit()

    # レスポンスを構築
    articles_response = []
    for article_data in step12_data.get("articles", []):
        article_number = article_data.get("article_number", 1)
        # article パラメータが指定されている場合はフィルタリング
        if article is not None and article_number != article:
            continue
        articles_response.append(
            WordPressArticleResponse(
                article_number=article_number,
                filename=article_data.get("filename", ""),
                gutenberg_blocks=article_data.get("gutenberg_blocks", ""),
                metadata=ArticleMetadata(**article_data.get("metadata", {})),
            )
        )

    if article is not None and not articles_response:
        logger.error(f"Article not found: run_id={run_id}, article_number={article}")
        raise HTTPException(status_code=404, detail=f"Article {article} not found")

    return Step12PreviewResponse(
        articles=articles_response,
        common_assets=step12_data.get("common_assets", {}),
        generation_metadata=step12_data.get("generation_metadata", {}),
    )


@router.get("/preview/{article_number}")
async def get_article_preview(
    run_id: str,
    article_number: int = Path(..., ge=1, le=4, description="記事番号（1-4）"),
    user: AuthUser = Depends(get_current_user),
) -> WordPressArticleResponse:
    """特定の記事のプレビューを取得."""
    # Use article parameter to filter at source level
    preview = await get_preview(run_id, article=article_number, user=user)

    if not preview.articles:
        logger.error(f"Article preview not found: run_id={run_id}, article_number={article_number}")
        raise HTTPException(status_code=404, detail=f"Article {article_number} not found")

    return preview.articles[0]


@router.get("/download")
async def download_all(
    run_id: str,
    user: AuthUser = Depends(get_current_user),
) -> StreamingResponse:
    """全記事をZIPでダウンロード."""
    db_manager = get_tenant_db_manager()
    store = get_artifact_store()
    tenant_id = user.tenant_id

    async with db_manager.get_session(tenant_id) as session:
        query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
        result = await session.execute(query)
        run = result.scalar_one_or_none()

        if not run:
            logger.error(f"Run not found for download: run_id={run_id}, tenant_id={tenant_id}")
            raise HTTPException(status_code=404, detail="Run not found")

        # Step12完了チェック
        await _ensure_step12_completed(session, run_id)
        step12_data = await _get_step12_data(tenant_id, run_id, store)

        if not step12_data:
            logger.warning(f"Step12 not completed for download: run_id={run_id}")
            raise HTTPException(
                status_code=400,
                detail="Step12 has not been completed. Please wait for workflow completion.",
            )

        # VULN-018: メタデータの検証
        validation_warnings: list[str] = []
        for article in step12_data.get("articles", []):
            metadata_dict = article.get("metadata", {})
            metadata = ArticleMetadata(**metadata_dict) if metadata_dict else ArticleMetadata()
            issues = metadata.validate_for_download()
            if issues:
                article_num = article.get("article_number", "?")
                validation_warnings.extend([f"Article {article_num}: {issue}" for issue in issues])

        if validation_warnings:
            logger.warning(
                f"Metadata validation warnings for download: run_id={run_id}",
                extra={"warnings": validation_warnings},
            )
            # 警告のみ - ダウンロードは許可（ワークフロー完了後のデータなので）

        # 監査ログを記録
        audit = AuditLogger(session)
        await audit.log(
            user_id=user.user_id,
            action="download",
            resource_type="step12",
            resource_id=run_id,
            details={
                "articles_count": len(step12_data.get("articles", [])),
                "download_type": "all",
            },
        )
        await session.commit()

    # ZIPファイルを作成
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for article in step12_data.get("articles", []):
            filename = article.get("filename", f"article_{article.get('article_number', 1)}.html")
            content = article.get("gutenberg_blocks", "")
            zip_file.writestr(filename, content)

        # メタデータも含める
        zip_metadata = {
            "run_id": run_id,
            "generated_at": step12_data.get("generation_metadata", {}).get("generated_at", ""),
            "wordpress_version_target": "6.0+",
            "articles": [
                {
                    "filename": a.get("filename"),
                    "title": a.get("metadata", {}).get("title", ""),
                }
                for a in step12_data.get("articles", [])
            ],
        }
        zip_file.writestr("metadata.json", json.dumps(zip_metadata, ensure_ascii=False, indent=2))

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=wordpress_articles_{run_id}.zip"},
    )


@router.get("/download/{article_number}")
async def download_article(
    run_id: str,
    article_number: int = Path(..., ge=1, le=4, description="記事番号（1-4）"),
    user: AuthUser = Depends(get_current_user),
) -> StreamingResponse:
    """特定の記事をダウンロード."""
    db_manager = get_tenant_db_manager()
    store = get_artifact_store()
    tenant_id = user.tenant_id

    async with db_manager.get_session(tenant_id) as session:
        query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
        result = await session.execute(query)
        run = result.scalar_one_or_none()

        if not run:
            logger.error(f"Run not found for article download: run_id={run_id}, tenant_id={tenant_id}")
            raise HTTPException(status_code=404, detail="Run not found")

        # Step12完了チェック
        await _ensure_step12_completed(session, run_id)
        step12_data = await _get_step12_data(tenant_id, run_id, store)

        if not step12_data:
            logger.warning(f"Step12 not completed for article download: run_id={run_id}")
            raise HTTPException(
                status_code=400,
                detail="Step12 has not been completed. Please wait for workflow completion.",
            )

        # 記事を検索
        article_data = None
        for a in step12_data.get("articles", []):
            if a.get("article_number") == article_number:
                article_data = a
                break

        if not article_data:
            logger.error(f"Article not found for download: run_id={run_id}, article_number={article_number}")
            raise HTTPException(status_code=404, detail=f"Article {article_number} not found")

        # 監査ログを記録
        audit = AuditLogger(session)
        await audit.log(
            user_id=user.user_id,
            action="download",
            resource_type="step12",
            resource_id=run_id,
            details={
                "article_number": article_number,
                "download_type": "single",
            },
        )
        await session.commit()

    content = article_data.get("gutenberg_blocks", "").encode("utf-8")
    filename = article_data.get("filename", f"article_{article_number}.html")

    return StreamingResponse(
        BytesIO(content),
        media_type="text/html",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )


@router.post("/generate")
async def generate_wordpress_html(
    run_id: str,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """WordPress用HTMLを生成してStorageに保存."""
    db_manager = get_tenant_db_manager()
    store = get_artifact_store()
    tenant_id = user.tenant_id

    async with db_manager.get_session(tenant_id) as session:
        query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
        result = await session.execute(query)
        run = result.scalar_one_or_none()

        if not run:
            logger.error(f"Run not found for generate: run_id={run_id}, tenant_id={tenant_id}")
            raise HTTPException(status_code=404, detail="Run not found")

        # Step10から生成
        try:
            step12_data = await _generate_wordpress_html_from_step10(tenant_id, run_id, store)
        except ValueError as e:
            logger.error(f"Failed to generate WordPress HTML: run_id={run_id}, error={e}")
            raise HTTPException(status_code=400, detail=str(e)) from e

        # Use build_path for consistent path generation
        output_path = store.build_path(tenant_id, run_id, "step12", "output.json")
        await store.put(
            json.dumps(step12_data, ensure_ascii=False).encode("utf-8"),
            output_path,
            "application/json",
        )

        # 個別記事も保存 (using build_path)
        for article in step12_data.get("articles", []):
            filename = article.get("filename", f"article_{article.get('article_number', 1)}.html")
            article_path = store.build_path(tenant_id, run_id, "step12", filename)
            await store.put(
                article.get("gutenberg_blocks", "").encode("utf-8"),
                article_path,
                "text/html",
            )

        # 監査ログを記録
        audit = AuditLogger(session)
        await audit.log(
            user_id=user.user_id,
            action="generate",
            resource_type="step12",
            resource_id=run_id,
            details={
                "articles_count": len(step12_data.get("articles", [])),
                "output_path": output_path,
            },
        )
        await session.commit()

    return {
        "success": True,
        "output_path": output_path,
        "articles_count": len(step12_data.get("articles", [])),
        "message": "WordPress用HTMLを生成しました",
    }
