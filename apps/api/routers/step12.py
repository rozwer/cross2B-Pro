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

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from apps.api.auth import get_current_user
from apps.api.auth.schemas import AuthUser
from apps.api.db import Run, TenantDBManager
from apps.api.storage import ArtifactStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/runs/{run_id}/step12", tags=["step12"])


# =============================================================================
# Pydantic Models
# =============================================================================


class ArticleMetadata(BaseModel):
    """記事メタデータ."""

    title: str = ""
    meta_description: str = ""
    focus_keyword: str = ""
    word_count: int = 0
    slug: str = ""


class WordPressArticleResponse(BaseModel):
    """WordPress記事レスポンス."""

    article_number: int
    filename: str
    gutenberg_blocks: str
    metadata: ArticleMetadata


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
    """Step12の出力データを取得."""
    try:
        data = await store.get_by_path(tenant_id, run_id, "step12", "output.json")
        if data:
            try:
                return json.loads(data.decode("utf-8"))
            except json.JSONDecodeError as e:
                logger.error(f"Corrupted step12 output JSON for run {run_id}: {e}")
                return None
    except Exception as e:
        logger.warning(f"Failed to load step12 output: {e}")
    return None


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
    user: AuthUser = Depends(get_current_user),
) -> Step12PreviewResponse:
    """Step12のプレビューを取得."""
    db_manager = get_tenant_db_manager()
    store = get_artifact_store()
    tenant_id = user.tenant_id

    async with db_manager.get_session(tenant_id) as session:
        query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
        result = await session.execute(query)
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

    # 既存のStep12出力を確認
    step12_data = await _get_step12_data(tenant_id, run_id, store)

    if not step12_data:
        # Step10から生成
        try:
            step12_data = await _generate_wordpress_html_from_step10(tenant_id, run_id, store)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    # レスポンスを構築
    articles = []
    for article in step12_data.get("articles", []):
        articles.append(
            WordPressArticleResponse(
                article_number=article.get("article_number", 1),
                filename=article.get("filename", ""),
                gutenberg_blocks=article.get("gutenberg_blocks", ""),
                metadata=ArticleMetadata(**article.get("metadata", {})),
            )
        )

    return Step12PreviewResponse(
        articles=articles,
        common_assets=step12_data.get("common_assets", {}),
        generation_metadata=step12_data.get("generation_metadata", {}),
    )


@router.get("/preview/{article_number}")
async def get_article_preview(
    run_id: str,
    article_number: int,
    user: AuthUser = Depends(get_current_user),
) -> WordPressArticleResponse:
    """特定の記事のプレビューを取得."""
    preview = await get_preview(run_id, user)

    for article in preview.articles:
        if article.article_number == article_number:
            return article

    raise HTTPException(status_code=404, detail=f"Article {article_number} not found")


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
            raise HTTPException(status_code=404, detail="Run not found")

    # Step12データを取得または生成
    step12_data = await _get_step12_data(tenant_id, run_id, store)

    if not step12_data:
        try:
            step12_data = await _generate_wordpress_html_from_step10(tenant_id, run_id, store)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    # ZIPファイルを作成
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for article in step12_data.get("articles", []):
            filename = article.get("filename", f"article_{article.get('article_number', 1)}.html")
            content = article.get("gutenberg_blocks", "")
            zip_file.writestr(filename, content)

        # メタデータも含める
        metadata = {
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
        zip_file.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2))

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=wordpress_articles_{run_id}.zip"},
    )


@router.get("/download/{article_number}")
async def download_article(
    run_id: str,
    article_number: int,
    user: AuthUser = Depends(get_current_user),
) -> StreamingResponse:
    """特定の記事をダウンロード."""
    preview = await get_preview(run_id, user)

    for article in preview.articles:
        if article.article_number == article_number:
            content = article.gutenberg_blocks.encode("utf-8")
            return StreamingResponse(
                BytesIO(content),
                media_type="text/html",
                headers={
                    "Content-Disposition": f"attachment; filename={article.filename}",
                },
            )

    raise HTTPException(status_code=404, detail=f"Article {article_number} not found")


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
            raise HTTPException(status_code=404, detail="Run not found")

    # Step10から生成
    try:
        step12_data = await _generate_wordpress_html_from_step10(tenant_id, run_id, store)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Storageに保存
    output_path = f"tenants/{tenant_id}/runs/{run_id}/step12/output.json"
    await store.put(
        json.dumps(step12_data, ensure_ascii=False).encode("utf-8"),
        output_path,
        "application/json",
    )

    # 個別記事も保存
    for article in step12_data.get("articles", []):
        article_path = f"tenants/{tenant_id}/runs/{run_id}/step12/{article.get('filename')}"
        await store.put(
            article.get("gutenberg_blocks", "").encode("utf-8"),
            article_path,
            "text/html",
        )

    return {
        "success": True,
        "output_path": output_path,
        "articles_count": len(step12_data.get("articles", [])),
        "message": "WordPress用HTMLを生成しました",
    }
