"""Artifacts router.

Handles artifact listing, retrieval, and preview endpoints.
"""

import base64
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select

from apps.api.auth import get_current_user
from apps.api.auth.schemas import AuthUser
from apps.api.db import (
    Artifact as ArtifactModel,
)
from apps.api.db import (
    AuditLogger,
    Run,
    Step,
    TenantIdValidationError,
)
from apps.api.storage import (
    ArtifactNotFoundError,
    ArtifactStoreError,
)
from apps.api.storage import (
    ArtifactRef as StorageArtifactRef,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["artifacts"])


# =============================================================================
# Lazy imports to avoid circular dependencies
# =============================================================================


def _get_tenant_db_manager() -> Any:
    """Get tenant DB manager."""
    from apps.api.db.tenant import get_tenant_manager

    return get_tenant_manager()


def _get_artifact_store() -> Any:
    """Get artifact store instance."""
    from apps.api.main import get_artifact_store

    return get_artifact_store()


# =============================================================================
# Pydantic Models
# =============================================================================


class ArtifactRef(BaseModel):
    """Artifact reference matching UI ArtifactRef."""

    id: str
    step_id: str
    step_name: str = ""  # Human-readable step name for display
    ref_path: str
    digest: str
    content_type: str
    size_bytes: int
    created_at: str


class ArtifactContent(BaseModel):
    """Artifact content matching UI ArtifactContent."""

    ref: ArtifactRef
    content: str
    encoding: str = "utf-8"  # utf-8 or base64


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/api/runs/{run_id}/files", response_model=list[ArtifactRef])
async def list_artifacts(run_id: str, user: AuthUser = Depends(get_current_user)) -> list[ArtifactRef]:
    """List all artifacts for a run.

    Falls back to MinIO listing if DB artifacts table is empty.
    """
    tenant_id = user.tenant_id
    logger.debug(
        "Listing artifacts",
        extra={"run_id": run_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    db_manager = _get_tenant_db_manager()
    store = _get_artifact_store()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # Verify run belongs to tenant
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # Build step_id -> step_name mapping
            steps_query = select(Step).where(Step.run_id == run_id)
            steps_result = await session.execute(steps_query)
            steps = steps_result.scalars().all()
            step_id_to_name = {str(s.id): s.step_name for s in steps}

            # Query artifacts from DB
            artifact_query = select(ArtifactModel).where(ArtifactModel.run_id == run_id)
            artifact_result = await session.execute(artifact_query)
            artifacts = artifact_result.scalars().all()

            # If DB has artifacts, return them
            if artifacts:
                return [
                    ArtifactRef(
                        id=str(a.id),
                        step_id=str(a.step_id) if a.step_id else "",
                        step_name=step_id_to_name.get(str(a.step_id), "") if a.step_id else "",
                        ref_path=a.ref_path,
                        digest=a.digest or "",
                        content_type=a.content_type or a.artifact_type,
                        size_bytes=a.size_bytes or 0,
                        created_at=a.created_at.isoformat(),
                    )
                    for a in artifacts
                ]

            # Fallback: List artifacts directly from MinIO storage
            logger.info(f"No artifacts in DB for run {run_id}, listing from MinIO")
            try:
                paths = await store.list_run_artifacts(tenant_id, run_id)
                artifact_refs = []

                for path in paths:
                    # Parse path: storage/{tenant_id}/{run_id}/{step}/{filename}
                    parts = path.split("/")
                    if len(parts) >= 5:
                        step_name = parts[3]
                        filename = parts[4]

                        # Skip non-output files (checkpoints, metadata)
                        if filename.startswith("checkpoint_") or filename == "metadata.json":
                            continue
                        # Only include output files (output.json, .html, .md)
                        if not (filename.endswith(".json") or filename.endswith(".html") or filename.endswith(".md")):
                            continue

                        # Get file stat from MinIO for size
                        try:
                            stat = store.client.stat_object(store.bucket, path)
                            size_bytes = stat.size if stat.size is not None else 0
                            created_at = stat.last_modified.isoformat() if stat.last_modified else datetime.now().isoformat()
                        except Exception:
                            size_bytes = 0
                            created_at = datetime.now().isoformat()

                        # Determine content type
                        content_type = "application/json"
                        if filename.endswith(".html"):
                            content_type = "text/html"
                        elif filename.endswith(".md"):
                            content_type = "text/markdown"

                        artifact_refs.append(
                            ArtifactRef(
                                id=f"{run_id}:{step_name}:{filename}",  # Synthetic ID
                                step_id="",
                                step_name=step_name,
                                ref_path=path,
                                digest="",  # Not available without reading file
                                content_type=content_type,
                                size_bytes=size_bytes,
                                created_at=created_at,
                            )
                        )

                return artifact_refs
            except Exception as e:
                logger.warning(f"Failed to list from MinIO: {e}")
                return []

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to list artifacts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list artifacts") from e


@router.get("/api/runs/{run_id}/files/{step}", response_model=list[ArtifactRef])
async def get_step_artifacts(
    run_id: str,
    step: str,
    user: AuthUser = Depends(get_current_user),
) -> list[ArtifactRef]:
    """Get artifacts for a specific step."""
    tenant_id = user.tenant_id
    logger.debug(
        "Getting step artifacts",
        extra={
            "run_id": run_id,
            "step": step,
            "tenant_id": tenant_id,
            "user_id": user.user_id,
        },
    )

    db_manager = _get_tenant_db_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # Verify run belongs to tenant
            run_query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            run_result = await session.execute(run_query)
            run = run_result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # Build step_id -> step_name mapping
            steps_query = select(Step).where(Step.run_id == run_id)
            steps_result = await session.execute(steps_query)
            steps = steps_result.scalars().all()
            step_id_to_name = {str(s.id): s.step_name for s in steps}

            # Query artifacts for specific step (via step_id -> steps.step_name)
            # First, find step by name
            step_query = select(Step).where(
                Step.run_id == run_id,
                Step.step_name == step,
            )
            step_result = await session.execute(step_query)
            step_record = step_result.scalar_one_or_none()

            if step_record:
                # Query artifacts by step_id
                artifact_query = select(ArtifactModel).where(
                    ArtifactModel.run_id == run_id,
                    ArtifactModel.step_id == step_record.id,
                )
            else:
                # Fallback: query all artifacts and filter by artifact_type containing step name
                artifact_query = select(ArtifactModel).where(
                    ArtifactModel.run_id == run_id,
                )

            artifact_result = await session.execute(artifact_query)
            artifacts = artifact_result.scalars().all()

            return [
                ArtifactRef(
                    id=str(a.id),
                    step_id=str(a.step_id) if a.step_id else "",
                    step_name=step_id_to_name.get(str(a.step_id), "") if a.step_id else "",
                    ref_path=a.ref_path,
                    digest=a.digest or "",
                    content_type=a.content_type or a.artifact_type,
                    size_bytes=a.size_bytes or 0,
                    created_at=a.created_at.isoformat(),
                )
                for a in artifacts
            ]

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to get step artifacts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get step artifacts") from e


@router.get("/api/runs/{run_id}/files/{artifact_id}/content", response_model=ArtifactContent)
async def get_artifact_content(
    run_id: str,
    artifact_id: str,
    user: AuthUser = Depends(get_current_user),
) -> ArtifactContent:
    """Get artifact content by ID.

    Supports both DB artifact IDs (UUID) and synthetic MinIO IDs ({run_id}:{step}:{filename}).
    """
    tenant_id = user.tenant_id
    logger.debug(
        "Getting artifact content",
        extra={
            "run_id": run_id,
            "artifact_id": artifact_id,
            "tenant_id": tenant_id,
            "user_id": user.user_id,
        },
    )

    db_manager = _get_tenant_db_manager()
    store = _get_artifact_store()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # Verify run belongs to tenant
            run_query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            run_result = await session.execute(run_query)
            run = run_result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # Check if artifact_id is a synthetic MinIO ID (format: {run_id}:{step}:{filename})
            if ":" in artifact_id:
                # Parse synthetic ID
                parts = artifact_id.split(":", 2)
                if len(parts) == 3:
                    _, step_name, filename = parts
                    ref_path = f"storage/{tenant_id}/{run_id}/{step_name}/{filename}"

                    # Get content directly from MinIO
                    try:
                        content_bytes = await store.get_by_path(tenant_id, run_id, step_name, filename)
                        if content_bytes is None:
                            raise HTTPException(status_code=404, detail="Artifact not found in storage")
                    except ArtifactStoreError:
                        raise HTTPException(status_code=404, detail="Artifact not found in storage")

                    # Decode content
                    try:
                        content = content_bytes.decode("utf-8")
                        encoding = "utf-8"
                    except UnicodeDecodeError:
                        content = base64.b64encode(content_bytes).decode("ascii")
                        encoding = "base64"

                    # Determine content type
                    content_type = "application/json"
                    if filename.endswith(".html"):
                        content_type = "text/html"
                    elif filename.endswith(".md"):
                        content_type = "text/markdown"

                    # Get file stat for size
                    try:
                        stat = store.client.stat_object(store.bucket, ref_path)
                        size_bytes = stat.size if stat.size is not None else len(content_bytes)
                        created_at = stat.last_modified.isoformat() if stat.last_modified else datetime.now().isoformat()
                    except Exception:
                        size_bytes = len(content_bytes)
                        created_at = datetime.now().isoformat()

                    return ArtifactContent(
                        ref=ArtifactRef(
                            id=artifact_id,
                            step_id="",
                            step_name=step_name,
                            ref_path=ref_path,
                            digest="",
                            content_type=content_type,
                            size_bytes=size_bytes,
                            created_at=created_at,
                        ),
                        content=content,
                        encoding=encoding,
                    )

            # Standard DB artifact lookup
            artifact_query = (
                select(ArtifactModel)
                .join(Run, ArtifactModel.run_id == Run.id)
                .where(
                    ArtifactModel.id == artifact_id,
                    Run.id == run_id,
                    Run.tenant_id == tenant_id,
                )
            )
            artifact_result = await session.execute(artifact_query)
            artifact = artifact_result.scalar_one_or_none()

            if not artifact:
                raise HTTPException(status_code=404, detail="Artifact not found")

            # Get content from storage with tenant check
            storage_ref = StorageArtifactRef(
                path=artifact.ref_path,
                digest=artifact.digest or "",
                content_type=artifact.content_type or artifact.artifact_type,
                size_bytes=artifact.size_bytes or 0,
                created_at=artifact.created_at,
            )

            try:
                content_bytes = await store.get_with_tenant_check(
                    tenant_id=tenant_id,
                    ref=storage_ref,
                    verify=True,
                )
            except ArtifactNotFoundError:
                raise HTTPException(status_code=404, detail="Artifact content not found in storage")

            try:
                content = content_bytes.decode("utf-8")
                encoding = "utf-8"
            except UnicodeDecodeError:
                content = base64.b64encode(content_bytes).decode("ascii")
                encoding = "base64"

            # Log download for audit
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="download",
                resource_type="artifact",
                resource_id=artifact_id,
                details={"run_id": run_id, "step_id": artifact.step_id},
            )

            # Get step_name if step_id is available
            step_name = ""
            if artifact.step_id:
                step_query = select(Step).where(Step.id == artifact.step_id)
                step_result = await session.execute(step_query)
                step_record = step_result.scalar_one_or_none()
                if step_record:
                    step_name = step_record.step_name

            return ArtifactContent(
                ref=ArtifactRef(
                    id=str(artifact.id),
                    step_id=str(artifact.step_id) if artifact.step_id else "",
                    step_name=step_name,
                    ref_path=artifact.ref_path,
                    digest=artifact.digest or "",
                    content_type=artifact.content_type or artifact.artifact_type,
                    size_bytes=artifact.size_bytes or 0,
                    created_at=artifact.created_at.isoformat(),
                ),
                content=content,
                encoding=encoding,
            )

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except ArtifactStoreError as e:
        logger.error(f"Storage error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve artifact content") from e
    except Exception as e:
        logger.error(f"Failed to get artifact content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get artifact content") from e


@router.get("/api/runs/{run_id}/preview", response_class=HTMLResponse)
async def get_run_preview(
    run_id: str,
    article: int = Query(default=1, ge=1, le=4, description="記事番号 (1-4)"),
    user: AuthUser = Depends(get_current_user),
) -> HTMLResponse:
    """Get HTML preview of generated article.

    Args:
        run_id: Run ID
        article: Article number (1-4) for multi-article support
        user: Authenticated user
    """
    import json

    tenant_id = user.tenant_id
    logger.debug(
        "Getting preview",
        extra={"run_id": run_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    db_manager = _get_tenant_db_manager()
    store = _get_artifact_store()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # Verify run belongs to tenant
            run_query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            run_result = await session.execute(run_query)
            run = run_result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            html_content = None

            # First priority: Step12 output (if completed)
            try:
                step12_bytes = await store.get_by_path(
                    tenant_id=tenant_id,
                    run_id=run_id,
                    step="step12",
                    filename="output.json",
                )
                if step12_bytes:
                    step12_data = json.loads(step12_bytes.decode("utf-8"))
                    step12_articles = step12_data.get("articles", [])
                    if step12_articles and article <= len(step12_articles):
                        target_article = step12_articles[article - 1]
                        html_content = target_article.get("html_content", target_article.get("gutenberg_blocks", ""))
                        if html_content:
                            logger.debug(f"Found HTML for article {article} at step12/output.json")
            except Exception as e:
                logger.debug(f"Could not get step12 output: {e}")

            # Second priority: Step11 output with images (if completed)
            if not html_content:
                step11_state = run.step11_state or {}
                if step11_state.get("phase") == "completed":
                    try:
                        step11_bytes = await store.get_by_path(
                            tenant_id=tenant_id,
                            run_id=run_id,
                            step="step11",
                            filename="output.json",
                        )

                        if step11_bytes:
                            step11_data = json.loads(step11_bytes.decode("utf-8"))
                            # Multi-article support: Step11 stores per-article preview HTMLs
                            # Images are filtered by article_number in step12; here we use html_with_images
                            step11_images = step11_data.get("images", [])
                            # For legacy single article or when images exist, use html_with_images directly
                            if article == 1 or not step11_images:
                                html_content = step11_data.get("html_with_images")
                            if html_content:
                                logger.debug(f"Found HTML for article {article} at step11/output.json")
                    except Exception as e:
                        logger.debug(f"Could not get step11 output: {e}")

            # Third priority: step10/preview.html
            if not html_content:
                try:
                    content_bytes = await store.get_by_path(
                        tenant_id=tenant_id,
                        run_id=run_id,
                        step="step10",
                        filename="preview.html",
                    )
                    if content_bytes:
                        html_content = content_bytes.decode("utf-8")
                        logger.debug("Found HTML preview at step10/preview.html")
                except Exception:
                    # Fallback: look for HTML artifact in DB (legacy support)
                    logger.debug("No preview.html at step10, checking DB artifacts")

            if not html_content:
                # Look for HTML artifact from final step in DB
                artifact_query = (
                    select(ArtifactModel)
                    .where(
                        ArtifactModel.run_id == run_id,
                        ArtifactModel.content_type.in_(["text/html", "html"]),
                    )
                    .order_by(ArtifactModel.created_at.desc())
                    .limit(1)
                )
                artifact_result = await session.execute(artifact_query)
                artifact = artifact_result.scalar_one_or_none()

                if not artifact:
                    # Final fallback: try to extract html_content from step10/output.json
                    try:
                        output_bytes = await store.get_by_path(
                            tenant_id=tenant_id,
                            run_id=run_id,
                            step="step10",
                            filename="output.json",
                        )
                        if output_bytes:
                            output_data = json.loads(output_bytes.decode("utf-8"))

                            # Multi-article support: check for articles array
                            articles = output_data.get("articles", [])
                            if articles and article <= len(articles):
                                # Get specific article by number
                                target_article = articles[article - 1]
                                html_content = target_article.get("html_content", target_article.get("content", ""))
                                if html_content:
                                    logger.debug(f"Extracted article {article} html_content from step10/output.json")
                            elif not articles:
                                # Fallback to legacy single article format
                                html_content = output_data.get("html_content")
                                if html_content:
                                    logger.debug("Extracted html_content from step10/output.json (legacy)")
                    except Exception as e:
                        logger.debug(f"Could not extract from output.json: {e}")

                if not html_content and artifact:
                    # Get content from DB artifact reference
                    storage_ref = StorageArtifactRef(
                        path=artifact.ref_path,
                        digest=artifact.digest or "",
                        content_type=artifact.content_type or "text/html",
                        size_bytes=artifact.size_bytes or 0,
                        created_at=artifact.created_at,
                    )

                    try:
                        content_bytes = await store.get_with_tenant_check(
                            tenant_id=tenant_id,
                            ref=storage_ref,
                            verify=True,
                        )
                        html_content = content_bytes.decode("utf-8")
                    except ArtifactNotFoundError:
                        pass

            if not html_content:
                raise HTTPException(status_code=404, detail="Preview not available")

            return HTMLResponse(content=html_content)

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to get preview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get preview") from e
