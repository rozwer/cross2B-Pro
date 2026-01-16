"""Articles API router.

Endpoints for managing completed articles with Claude Code review and GitHub integration.
"""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from apps.api.auth import get_current_user
from apps.api.auth.schemas import AuthUser
from apps.api.db import Run
from apps.api.schemas.enums import RunStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/articles", tags=["articles"])


# =============================================================================
# Lazy imports
# =============================================================================


def _get_tenant_db_manager() -> "TenantDBManager":
    """Get tenant DB manager."""
    from apps.api.db.tenant import get_tenant_manager

    return get_tenant_manager()


def _get_artifact_store() -> "ArtifactStore":
    """Get artifact store instance."""
    from apps.api.main import get_artifact_store

    return get_artifact_store()


# Type alias for lazy import
TenantDBManager = object
ArtifactStore = object


# =============================================================================
# Response Models
# =============================================================================


class ArticleSummary(BaseModel):
    """Summary of a completed article."""

    id: str
    keyword: str
    status: str
    created_at: str
    completed_at: str | None = None
    has_images: bool = False
    article_count: int = 1
    review_status: str | None = None  # pending, completed, none
    github_repo_url: str | None = None


class ArticleListResponse(BaseModel):
    """Response for article list endpoint."""

    articles: list[ArticleSummary]
    total: int
    limit: int
    offset: int


class ArticleContent(BaseModel):
    """Content from a specific step."""

    step: str
    content: dict[str, Any] | None = None
    available: bool = False


class ArticleDetail(BaseModel):
    """Detailed article information with content."""

    id: str
    keyword: str
    status: str
    created_at: str
    completed_at: str | None = None
    github_repo_url: str | None = None
    github_dir_path: str | None = None
    # Article metadata from step10
    title: str | None = None
    description: str | None = None
    article_count: int = 1
    # Content availability
    has_step10: bool = False  # Markdown content
    has_step11: bool = False  # Images
    has_step12: bool = False  # WordPress HTML
    # Review status
    review_status: str | None = None
    # Input data
    input_data: dict[str, Any] | None = None


class ArticlePreviewResponse(BaseModel):
    """Response for article preview."""

    html: str
    article_number: int | None = None


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=ArticleListResponse)
async def list_articles(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    keyword: str | None = Query(default=None, description="Filter by keyword (partial match)"),
    has_review: bool | None = Query(default=None, description="Filter by review status"),
    user: AuthUser = Depends(get_current_user),
) -> ArticleListResponse:
    """List completed articles with filtering and pagination.

    Returns articles where status is 'completed'.
    """
    tenant_id = user.tenant_id
    offset = (page - 1) * limit
    db_manager = _get_tenant_db_manager()
    store = _get_artifact_store()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # Base query: only completed runs
            query = select(Run).where(
                Run.tenant_id == tenant_id,
                Run.status == RunStatus.COMPLETED.value,
            )

            # Keyword filter (partial match)
            if keyword:
                # Filter using JSON field
                query = query.where(Run.input_data["keyword"].astext.ilike(f"%{keyword}%"))

            # Count total
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await session.execute(count_query)
            total = total_result.scalar() or 0

            # Apply pagination
            query = query.order_by(Run.completed_at.desc().nullsfirst(), Run.created_at.desc())
            query = query.offset(offset).limit(limit)
            result = await session.execute(query)
            runs = result.scalars().all()

            # Build article summaries
            articles: list[ArticleSummary] = []
            for run in runs:
                input_data = run.input_data or {}

                # Check for images (step11 state)
                has_images = False
                if run.step11_state:
                    images = run.step11_state.get("images", [])
                    has_images = len(images) > 0

                # Check review status from MinIO (use storage/ prefix to match actual MinIO paths)
                review_status: str | None = None
                review_path = f"storage/{tenant_id}/{run.id}/step10/review.json"
                if await store.exists_by_path(review_path):
                    review_status = "completed"

                # Get article count from input data
                article_count = 1
                articles_input = input_data.get("articles", [])
                if articles_input:
                    article_count = len(articles_input)

                articles.append(
                    ArticleSummary(
                        id=str(run.id),
                        keyword=input_data.get("keyword", ""),
                        status=run.status,
                        created_at=run.created_at.isoformat(),
                        completed_at=run.completed_at.isoformat() if run.completed_at else None,
                        has_images=has_images,
                        article_count=article_count,
                        review_status=review_status,
                        github_repo_url=run.github_repo_url,
                    )
                )

            # Filter by review status if requested
            if has_review is not None:
                if has_review:
                    articles = [a for a in articles if a.review_status == "completed"]
                else:
                    articles = [a for a in articles if a.review_status is None]
                total = len(articles)

            return ArticleListResponse(
                articles=articles,
                total=total,
                limit=limit,
                offset=offset,
            )

    except Exception as e:
        logger.error(f"Failed to list articles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list articles") from e


@router.get("/{run_id}", response_model=ArticleDetail)
async def get_article(
    run_id: UUID,
    user: AuthUser = Depends(get_current_user),
) -> ArticleDetail:
    """Get detailed article information.

    Returns article metadata and content availability.
    """
    tenant_id = user.tenant_id
    db_manager = _get_tenant_db_manager()
    store = _get_artifact_store()

    try:
        async with db_manager.get_session(tenant_id) as session:
            result = await session.execute(
                select(Run).where(
                    Run.id == run_id,
                    Run.tenant_id == tenant_id,
                )
            )
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Article not found")

            input_data = run.input_data or {}

            # Check content availability (use storage/ prefix to match actual MinIO paths)
            has_step10 = await store.exists_by_path(f"storage/{tenant_id}/{run_id}/step10/output.json")
            has_step11 = await store.exists_by_path(f"storage/{tenant_id}/{run_id}/step11/output.json")
            has_step12 = await store.exists_by_path(f"storage/{tenant_id}/{run_id}/step12/output.json")

            # Check review status
            review_status: str | None = None
            review_path = f"storage/{tenant_id}/{run_id}/step10/review.json"
            if await store.exists_by_path(review_path):
                review_status = "completed"

            # Get article count
            article_count = 1
            articles_input = input_data.get("articles", [])
            if articles_input:
                article_count = len(articles_input)

            # Try to get title and article count from step10 output
            title: str | None = None
            description: str | None = None
            if has_step10:
                try:
                    step10_content = await store.get_by_path(
                        tenant_id=tenant_id,
                        run_id=str(run_id),
                        step="step10",
                    )
                    if step10_content:
                        import json

                        step10_data = json.loads(step10_content.decode("utf-8"))
                        # Handle both single article and multi-article format
                        if "articles" in step10_data:
                            articles_list = step10_data["articles"]
                            article_count = len(articles_list) if articles_list else 1
                            first_article = articles_list[0] if articles_list else {}
                            title = first_article.get("title")
                            description = first_article.get("meta_description")
                        else:
                            title = step10_data.get("title")
                            description = step10_data.get("meta_description")
                except Exception as e:
                    logger.warning(f"Failed to parse step10 content: {e}")

            return ArticleDetail(
                id=str(run.id),
                keyword=input_data.get("keyword", ""),
                status=run.status,
                created_at=run.created_at.isoformat(),
                completed_at=run.completed_at.isoformat() if run.completed_at else None,
                github_repo_url=run.github_repo_url,
                github_dir_path=run.github_dir_path,
                title=title,
                description=description,
                article_count=article_count,
                has_step10=has_step10,
                has_step11=has_step11,
                has_step12=has_step12,
                review_status=review_status,
                input_data=input_data,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get article: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get article") from e


@router.get("/{run_id}/content/{step}")
async def get_article_content(
    run_id: UUID,
    step: str,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get article content from a specific step.

    Valid steps: step10 (markdown), step11 (images), step12 (wordpress html)
    """
    tenant_id = user.tenant_id
    store = _get_artifact_store()

    valid_steps = {"step10", "step11", "step12"}
    if step not in valid_steps:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid step: {step}. Valid steps: {', '.join(valid_steps)}",
        )

    try:
        content = await store.get_by_path(
            tenant_id=tenant_id,
            run_id=str(run_id),
            step=step,
        )

        if not content:
            raise HTTPException(status_code=404, detail=f"Content not found for step {step}")

        import json

        return json.loads(content.decode("utf-8"))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get article content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get article content") from e
