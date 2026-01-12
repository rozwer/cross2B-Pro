"""Run management API router.

Endpoints for creating, listing, and managing workflow runs.
"""

import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from apps.api.auth import get_current_user
from apps.api.auth.schemas import AuthUser
from apps.api.db import AuditLogger, Run, Step, TenantIdValidationError
from apps.api.db.models import Artifact as ArtifactModel
from apps.api.schemas.enums import RunStatus, StepStatus
from apps.api.schemas.runs import (
    CreateRunInput,
    ModelConfig,
    RejectRunInput,
    RunResponse,
)
from apps.api.services.runs import (
    get_steps_from_storage,
    run_orm_to_response,
    sync_run_with_temporal,
)
from apps.api.storage import ArtifactStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/runs", tags=["runs"])


# =============================================================================
# Lazy imports to avoid circular dependencies
# =============================================================================


def _get_temporal_client() -> Any:
    """Get Temporal client from main module."""
    from apps.api.main import temporal_client

    return temporal_client


def _get_ws_manager() -> Any:
    """Get WebSocket manager from main module."""
    from apps.api.main import ws_manager

    return ws_manager


def _get_temporal_task_queue() -> str:
    """Get Temporal task queue name."""
    from apps.api.main import TEMPORAL_TASK_QUEUE

    return TEMPORAL_TASK_QUEUE


def _get_tenant_db_manager() -> Any:
    """Get tenant DB manager."""
    from apps.api.db.tenant import get_tenant_manager

    return get_tenant_manager()


def _get_artifact_store() -> Any:
    """Get artifact store instance."""
    from apps.api.main import get_artifact_store

    return get_artifact_store()


# =============================================================================
# Additional Pydantic Models
# =============================================================================


class CloneRunInput(BaseModel):
    """Request body for cloning a run with optional overrides."""

    keyword: str | None = None
    target_audience: str | None = None
    competitor_urls: list[str] | None = None
    additional_requirements: str | None = None
    model_config_override: ModelConfig | None = Field(None, alias="model_config")
    start_workflow: bool = True

    class Config:
        populate_by_name = True


class BulkDeleteRequest(BaseModel):
    """Request body for bulk delete."""

    run_ids: list[str]


class BulkDeleteResponse(BaseModel):
    """Response for bulk delete."""

    deleted: list[str]
    failed: list[dict[str, str]]  # [{"id": "...", "error": "..."}]


# =============================================================================
# Run Management Endpoints
# =============================================================================


@router.post("", response_model=RunResponse)
async def create_run(
    data: CreateRunInput,
    start_workflow: bool = Query(default=True, description="Whether to start the Temporal workflow immediately"),
    user: AuthUser = Depends(get_current_user),
) -> RunResponse:
    """Create a new workflow run and optionally start Temporal workflow.

    Args:
        data: Run configuration
        start_workflow: If True, starts Temporal workflow immediately (default: True)
        user: Authenticated user
    """
    tenant_id = user.tenant_id
    run_id = str(uuid.uuid4())
    now = datetime.now()

    # Prepare JSON data for storage using normalized input
    input_data = data.get_normalized_input()
    effective_keyword = data.get_effective_keyword()

    # Extract legacy-compatible fields for workflow
    target_audience = input_data.get("target_audience")
    competitor_urls = input_data.get("competitor_urls")
    additional_requirements = input_data.get("additional_requirements")

    # Build workflow config
    workflow_config = {
        "model_config": data.model_config_data.model_dump(),
        "step_configs": [sc.model_dump() for sc in data.step_configs] if data.step_configs else None,
        "tool_config": data.tool_config.model_dump() if data.tool_config else None,
        "options": data.options.model_dump() if data.options else None,
        "pack_id": "default",
        "input": input_data,
        "keyword": effective_keyword,
        "target_audience": target_audience,
        "competitor_urls": competitor_urls,
        "additional_requirements": additional_requirements,
    }

    db_manager = _get_tenant_db_manager()
    temporal_client = _get_temporal_client()
    ws_manager = _get_ws_manager()
    task_queue = _get_temporal_task_queue()

    try:
        # Phase 1: Create run record and commit to DB
        run_response: RunResponse | None = None
        async with db_manager.get_session(tenant_id) as session:
            # Create Run ORM instance
            run_orm = Run(
                id=run_id,
                tenant_id=tenant_id,
                status=RunStatus.PENDING.value,
                current_step=None,
                input_data=input_data,
                config=workflow_config,
                created_at=now,
                updated_at=now,
            )
            session.add(run_orm)

            # Log audit entry
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="create",
                resource_type="run",
                resource_id=run_id,
                details={"keyword": effective_keyword, "start_workflow": start_workflow},
            )

            # Commit is done automatically when exiting context manager
            run_response = run_orm_to_response(run_orm)

        logger.info("Run created and committed", extra={"run_id": run_id, "tenant_id": tenant_id})

        # Phase 2: Start Temporal workflow AFTER DB commit
        if start_workflow and temporal_client is not None:
            try:
                await temporal_client.start_workflow(
                    "ArticleWorkflow",
                    args=[tenant_id, run_id, workflow_config, None],
                    id=run_id,
                    task_queue=task_queue,
                )

                # Update run status in separate transaction
                async with db_manager.get_session(tenant_id) as session:
                    result = await session.execute(select(Run).where(Run.id == run_id))
                    run_orm = result.scalar_one()
                    run_orm.status = RunStatus.RUNNING.value
                    run_orm.started_at = now
                    run_orm.updated_at = now
                    run_response = run_orm_to_response(run_orm)

                logger.info(
                    "Temporal workflow started",
                    extra={"run_id": run_id, "tenant_id": tenant_id, "task_queue": task_queue},
                )

                await ws_manager.broadcast_run_update(
                    run_id=run_id,
                    event_type="run.started",
                    status=RunStatus.RUNNING.value,
                )

            except Exception as wf_error:
                logger.error(f"Failed to start Temporal workflow: {wf_error}", exc_info=True)
                # Update run status to failed in separate transaction
                async with db_manager.get_session(tenant_id) as session:
                    result = await session.execute(select(Run).where(Run.id == run_id))
                    run_orm = result.scalar_one()
                    run_orm.status = RunStatus.FAILED.value
                    run_orm.error_code = "WORKFLOW_START_FAILED"
                    run_orm.error_message = str(wf_error)
                    run_orm.updated_at = now
                    run_response = run_orm_to_response(run_orm)

        elif start_workflow and temporal_client is None:
            logger.warning(
                "Temporal client not available, workflow not started",
                extra={"run_id": run_id, "tenant_id": tenant_id},
            )

        return run_response

    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to create run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create run") from e


@router.get("")
async def list_runs(
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List runs with optional filtering."""
    tenant_id = user.tenant_id
    offset = (page - 1) * limit

    db_manager = _get_tenant_db_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            query = select(Run).where(Run.tenant_id == tenant_id)

            if status:
                query = query.where(Run.status == status)

            count_query = select(func.count()).select_from(query.subquery())
            total_result = await session.execute(count_query)
            total = total_result.scalar() or 0

            query = query.order_by(Run.created_at.desc()).offset(offset).limit(limit)
            result = await session.execute(query)
            runs = result.scalars().all()

            runs_summary = []
            for r in runs:
                input_data = r.input_data or {}
                config = r.config or {}
                model_config_data = config.get("model_config", {})

                runs_summary.append(
                    {
                        "id": str(r.id),
                        "status": r.status,
                        "current_step": r.current_step,
                        "keyword": input_data.get("keyword", ""),
                        "model_config": model_config_data,
                        "created_at": r.created_at.isoformat(),
                        "updated_at": r.updated_at.isoformat(),
                    }
                )

            return {"runs": runs_summary, "total": total, "limit": limit, "offset": offset}

    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to list runs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list runs") from e


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, user: AuthUser = Depends(get_current_user)) -> RunResponse:
    """Get run details with Temporal state synchronization."""
    tenant_id = user.tenant_id

    db_manager = _get_tenant_db_manager()
    temporal_client = _get_temporal_client()
    artifact_store = _get_artifact_store()

    try:
        async with db_manager.get_session(tenant_id) as session:
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id).options(selectinload(Run.steps))
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # Sync with Temporal state if workflow is active
            db_updated = False
            if run.status in (RunStatus.RUNNING.value, RunStatus.WAITING_APPROVAL.value, RunStatus.PENDING.value):
                db_updated = await sync_run_with_temporal(run, temporal_client)

            if db_updated:
                await session.flush()
                await session.refresh(run)

            # If no steps in DB, try to infer from storage
            db_steps = list(run.steps)
            if not db_steps:
                storage_steps = await get_steps_from_storage(tenant_id, run_id, run.current_step, run.status, artifact_store)
                response = run_orm_to_response(run, steps=[])
                response.steps = storage_steps
                return response

            return run_orm_to_response(run, steps=db_steps)

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to get run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get run") from e


@router.post("/{run_id}/approve")
async def approve_run(
    run_id: str,
    comment: str | None = None,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, bool]:
    """Approve a run waiting for approval."""
    tenant_id = user.tenant_id
    logger.info(
        "Approving run",
        extra={"run_id": run_id, "tenant_id": tenant_id, "comment": comment, "user_id": user.user_id},
    )

    db_manager = _get_tenant_db_manager()
    temporal_client = _get_temporal_client()
    ws_manager = _get_ws_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            if run.status != RunStatus.WAITING_APPROVAL.value:
                raise HTTPException(status_code=400, detail=f"Run is not waiting for approval (current status: {run.status})")

            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="approve",
                resource_type="run",
                resource_id=run_id,
                details={"comment": comment, "previous_status": run.status},
            )

            if temporal_client is not None:
                try:
                    workflow_handle = temporal_client.get_workflow_handle(run_id)
                    await workflow_handle.signal("approve")
                    logger.info("Temporal approval signal sent", extra={"run_id": run_id})
                except Exception as sig_error:
                    logger.error(f"Failed to send approval signal: {sig_error}", exc_info=True)
                    raise HTTPException(status_code=503, detail=f"Failed to send approval signal to workflow: {sig_error}")
            else:
                logger.warning("Temporal client not available, signal not sent", extra={"run_id": run_id})
                raise HTTPException(status_code=503, detail="Temporal service unavailable")

            run.status = RunStatus.RUNNING.value
            run.updated_at = datetime.now()

            await session.flush()
            logger.info("Run approved", extra={"run_id": run_id, "tenant_id": tenant_id})

            await ws_manager.broadcast_run_update(
                run_id=run_id,
                event_type="run.approved",
                status=RunStatus.RUNNING.value,
            )

            return {"success": True}

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to approve run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to approve run") from e


@router.post("/{run_id}/reject")
async def reject_run(
    run_id: str,
    data: RejectRunInput,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, bool]:
    """Reject a run waiting for approval."""
    reason = data.reason
    tenant_id = user.tenant_id
    logger.info(
        "Rejecting run",
        extra={"run_id": run_id, "tenant_id": tenant_id, "reason": reason, "user_id": user.user_id},
    )

    db_manager = _get_tenant_db_manager()
    temporal_client = _get_temporal_client()
    ws_manager = _get_ws_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            if run.status != RunStatus.WAITING_APPROVAL.value:
                raise HTTPException(status_code=400, detail=f"Run is not waiting for approval (current status: {run.status})")

            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="reject",
                resource_type="run",
                resource_id=run_id,
                details={"reason": reason, "previous_status": run.status},
            )

            if temporal_client is not None:
                try:
                    workflow_handle = temporal_client.get_workflow_handle(run_id)
                    await workflow_handle.signal("reject", reason or "Rejected by reviewer")
                    logger.info("Temporal rejection signal sent", extra={"run_id": run_id})
                except Exception as sig_error:
                    logger.error(f"Failed to send rejection signal: {sig_error}", exc_info=True)
                    raise HTTPException(status_code=503, detail=f"Failed to send rejection signal to workflow: {sig_error}")
            else:
                logger.warning("Temporal client not available, signal not sent", extra={"run_id": run_id})
                raise HTTPException(status_code=503, detail="Temporal service unavailable")

            run.status = RunStatus.FAILED.value
            run.error_code = "REJECTED"
            run.error_message = reason or "Rejected by reviewer"
            run.updated_at = datetime.now()
            run.completed_at = datetime.now()

            await session.flush()
            logger.info("Run rejected", extra={"run_id": run_id, "tenant_id": tenant_id})

            await ws_manager.broadcast_run_update(
                run_id=run_id,
                event_type="run.rejected",
                status=RunStatus.FAILED.value,
                error={"code": "REJECTED", "message": reason or "Rejected by reviewer"},
            )

            return {"success": True}

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to reject run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to reject run") from e


@router.post("/{run_id}/retry/{step}")
async def retry_step(
    run_id: str,
    step: str,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Retry a failed step."""
    tenant_id = user.tenant_id
    logger.info(
        "Retrying step",
        extra={"run_id": run_id, "step": step, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    # ステップ順序（前ステップデータ読み込み用）
    step_order = [
        "step0",
        "step1",
        "step1_5",
        "step2",
        "step3a",
        "step3b",
        "step3c",
        "step3_5",
        "step4",
        "step5",
        "step6",
        "step6_5",
        "step7a",
        "step7b",
        "step8",
        "step9",
        "step10",
        "step12",
    ]

    valid_steps = step_order  # リトライ可能なステップ = 全ステップ

    normalized_step = step.replace(".", "_")
    if normalized_step not in valid_steps:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid step: {step}. Valid steps: {', '.join(valid_steps)}",
        )

    db_manager = _get_tenant_db_manager()
    temporal_client = _get_temporal_client()
    ws_manager = _get_ws_manager()
    task_queue = _get_temporal_task_queue()
    artifact_store = ArtifactStore()

    try:
        async with db_manager.get_session(tenant_id) as session:
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            if run.status != RunStatus.FAILED.value:
                raise HTTPException(status_code=400, detail=f"Run must be in failed status to retry (current status: {run.status})")

            # Use underscore format for step_name (matches Worker step_id format)
            step_query = select(Step).where(
                Step.run_id == run_id,
                Step.step_name == normalized_step,
            )
            step_result = await session.execute(step_query)
            step_record = step_result.scalar_one_or_none()

            new_attempt_id = str(uuid.uuid4())
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="retry",
                resource_type="step",
                resource_id=f"{run_id}/{step}",
                details={
                    "new_attempt_id": new_attempt_id,
                    "previous_status": run.status,
                },
            )

            if temporal_client is None:
                raise HTTPException(status_code=503, detail="Temporal client not available")

            try:
                loaded_config = dict(run.config) if run.config else {}
                new_workflow_id = f"{run_id}-retry-{new_attempt_id[:8]}"

                # 失敗したステップの成果物を削除（リトライ時にクリーンな状態で実行）
                deleted_count = await artifact_store.delete_step_artifacts(
                    tenant_id=tenant_id,
                    run_id=run_id,
                    step=normalized_step,
                )
                if deleted_count > 0:
                    logger.info(
                        f"Deleted {deleted_count} artifacts for retry",
                        extra={"run_id": run_id, "step": normalized_step},
                    )

                # 前ステップデータの確認（Activityは load_step_data で storage から読むため config に追加は不要）
                # ただしログ用に読み込み状況を確認
                if normalized_step in step_order:
                    step_index = step_order.index(normalized_step)
                    steps_to_load = step_order[:step_index]
                    loaded_steps = []

                    for prev_step in steps_to_load:
                        artifact_data = await artifact_store.get_by_path(
                            tenant_id=tenant_id,
                            run_id=run_id,
                            step=prev_step,
                        )
                        if artifact_data:
                            loaded_steps.append(prev_step)

                    if loaded_steps:
                        logger.info(
                            "Previous step data available for retry",
                            extra={
                                "run_id": run_id,
                                "retry_step": normalized_step,
                                "available_steps": loaded_steps,
                            },
                        )
                    else:
                        logger.warning(
                            "No previous step data found for retry - this may cause issues",
                            extra={
                                "run_id": run_id,
                                "retry_step": normalized_step,
                                "expected_steps": steps_to_load,
                            },
                        )

                # First, update DB status and commit
                run.status = RunStatus.RUNNING.value
                run.current_step = normalized_step
                run.error_message = None  # エラーメッセージをクリア
                run.error_code = None  # エラーコードをクリア
                run.updated_at = datetime.now()

                retry_count = 1
                if step_record:
                    step_record.status = StepStatus.RUNNING.value
                    step_record.retry_count = (step_record.retry_count or 0) + 1
                    step_record.error_message = None  # ステップのエラーメッセージもクリア
                    retry_count = step_record.retry_count

                # Commit DB changes before starting workflow
                await session.commit()
                logger.info("Step retry DB update committed", extra={"run_id": run_id, "step": step})

            except Exception as db_error:
                logger.error(f"Failed to update DB for retry: {db_error}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Failed to update DB for retry: {db_error}")

        # Start Temporal workflow AFTER DB commit (outside session context)
        try:
            await temporal_client.start_workflow(
                "ArticleWorkflow",
                args=[tenant_id, run_id, loaded_config, normalized_step],
                id=new_workflow_id,
                task_queue=task_queue,
            )
            logger.info(
                "Temporal retry workflow started",
                extra={"run_id": run_id, "step": step, "new_workflow_id": new_workflow_id},
            )
        except Exception as wf_error:
            logger.error(f"Failed to start retry workflow: {wf_error}", exc_info=True)
            # Revert status to failed if workflow start fails
            async with db_manager.get_session(tenant_id) as session:
                result = await session.execute(select(Run).where(Run.id == run_id))
                run = result.scalar_one()
                run.status = RunStatus.FAILED.value
                run.error_message = f"Retry workflow start failed: {wf_error}"
            raise HTTPException(status_code=503, detail=f"Failed to start retry workflow: {wf_error}")

        await ws_manager.broadcast_step_event(
            run_id=run_id,
            step=step,
            event_type="step_retrying",
            status=StepStatus.RUNNING.value,
            message=f"Retrying step {step}",
            attempt=retry_count,
        )

        return {"success": True, "new_attempt_id": new_attempt_id}

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to retry step: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retry step") from e


@router.post("/{run_id}/resume/{step}")
async def resume_from_step(
    run_id: str,
    step: str,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Resume/restart workflow from a specific step."""
    tenant_id = user.tenant_id
    logger.info(
        "Resuming run",
        extra={"run_id": run_id, "step": step, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    step_order = [
        "step0",
        "step1",
        "step1_5",
        "step2",
        "step3a",
        "step3b",
        "step3c",
        "step3_5",
        "step4",
        "step5",
        "step6",
        "step6_5",
        "step7a",
        "step7b",
        "step8",
        "step9",
        "step10",
        "step12",
    ]

    if step not in step_order:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid step: {step}. Valid steps: {', '.join(step_order)}",
        )

    db_manager = _get_tenant_db_manager()
    temporal_client = _get_temporal_client()
    task_queue = _get_temporal_task_queue()
    artifact_store = ArtifactStore()

    try:
        async with db_manager.get_session(tenant_id) as session:
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            original_run = result.scalar_one_or_none()

            if not original_run:
                raise HTTPException(status_code=404, detail="Run not found")

            step_index = step_order.index(step)
            steps_to_load = step_order[:step_index]

            loaded_config = dict(original_run.config) if original_run.config else {}

            # Store artifact REFERENCES only, not full data (to avoid gRPC size limits)
            # Activities should load full data from storage via load_step_data()
            artifact_refs: dict[str, dict[str, str]] = {}
            for prev_step in steps_to_load:
                artifact_path = artifact_store.build_path(tenant_id, run_id, prev_step)
                exists = await artifact_store.exists(artifact_path)
                if exists:
                    artifact_refs[prev_step] = {
                        "path": artifact_path,
                        "step": prev_step,
                    }
                    logger.debug(f"Artifact reference recorded for {prev_step}")

            # Store only references in config (not full step data)
            loaded_config["resume_artifact_refs"] = artifact_refs
            logger.info(
                "Resume artifact references prepared",
                extra={
                    "run_id": run_id,
                    "resume_from": step,
                    "artifact_refs_count": len(artifact_refs),
                },
            )

            steps_to_delete = step_order[step_index:]
            steps_to_delete_with_step11 = steps_to_delete + ["step11"]

            deleted_artifacts_count = 0
            for step_to_delete in steps_to_delete_with_step11:
                count = await artifact_store.delete_step_artifacts(
                    tenant_id=tenant_id,
                    run_id=run_id,
                    step=step_to_delete,
                )
                deleted_artifacts_count += count

            if deleted_artifacts_count > 0:
                logger.info(
                    f"Deleted {deleted_artifacts_count} artifacts for resume",
                    extra={
                        "run_id": run_id,
                        "resume_from": step,
                        "deleted_steps": steps_to_delete_with_step11,
                    },
                )

            await session.execute(
                sql_delete(Step).where(
                    Step.run_id == run_id,
                    Step.step_name.in_(steps_to_delete_with_step11),
                )
            )

            for prev_step in steps_to_load:
                step_query = select(Step).where(
                    Step.run_id == run_id,
                    Step.step_name == prev_step,
                )
                step_result = await session.execute(step_query)
                step_record = step_result.scalar_one_or_none()

                if step_record:
                    step_record.status = StepStatus.COMPLETED.value
                    if not step_record.completed_at:
                        step_record.completed_at = datetime.now()
                else:
                    new_step = Step(
                        run_id=run_id,
                        step_name=prev_step,
                        status=StepStatus.COMPLETED.value,
                        started_at=datetime.now(),
                        completed_at=datetime.now(),
                        retry_count=0,
                    )
                    session.add(new_step)

            logger.info(
                "Updated step statuses for resume",
                extra={
                    "run_id": run_id,
                    "completed_steps": steps_to_load,
                    "deleted_step_records": steps_to_delete_with_step11,
                },
            )

            if temporal_client is None:
                raise HTTPException(status_code=503, detail="Temporal client not available")

            new_workflow_id = f"{run_id}-resume-{uuid.uuid4().hex[:8]}"

            # First, update DB and commit BEFORE starting workflow
            now = datetime.now()
            original_run.status = RunStatus.RUNNING.value
            original_run.current_step = step
            original_run.error_message = None
            original_run.error_code = None
            original_run.completed_at = None
            original_run.updated_at = now

            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="resume",
                resource_type="run",
                resource_id=run_id,
                details={
                    "resume_from": step,
                    "workflow_id": new_workflow_id,
                    "deleted_artifacts_count": deleted_artifacts_count,
                    "deleted_steps": steps_to_delete_with_step11,
                },
            )

            await session.commit()
            logger.info("Resume DB update committed", extra={"run_id": run_id, "step": step})

        # Start Temporal workflow AFTER DB commit (outside session context)
        try:
            await temporal_client.start_workflow(
                "ArticleWorkflow",
                args=[tenant_id, run_id, loaded_config, step],
                id=new_workflow_id,
                task_queue=task_queue,
            )

            logger.info(
                "Run resumed",
                extra={
                    "run_id": run_id,
                    "resume_from": step,
                    "workflow_id": new_workflow_id,
                    "loaded_steps": steps_to_load,
                },
            )
        except Exception as wf_error:
            logger.error(f"Failed to start resume workflow: {wf_error}", exc_info=True)
            # Revert status to failed if workflow start fails
            async with db_manager.get_session(tenant_id) as session:
                result = await session.execute(select(Run).where(Run.id == run_id))
                run = result.scalar_one()
                run.status = RunStatus.FAILED.value
                run.error_message = f"Resume workflow start failed: {wf_error}"
            raise HTTPException(status_code=503, detail=f"Failed to start resume workflow: {wf_error}")

        return {
            "success": True,
            "new_run_id": run_id,
            "resume_from": step,
            "workflow_id": new_workflow_id,
            "loaded_steps": steps_to_load,
            "deleted_artifacts_count": deleted_artifacts_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to resume run: {e}") from e


@router.post("/{run_id}/clone", response_model=RunResponse)
async def clone_run(
    run_id: str,
    data: CloneRunInput | None = None,
    user: AuthUser = Depends(get_current_user),
) -> RunResponse:
    """Clone an existing run with optional config overrides."""
    tenant_id = user.tenant_id
    logger.info(
        "Cloning run",
        extra={"run_id": run_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    db_manager = _get_tenant_db_manager()
    temporal_client = _get_temporal_client()
    ws_manager = _get_ws_manager()
    task_queue = _get_temporal_task_queue()

    try:
        async with db_manager.get_session(tenant_id) as session:
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            original_run = result.scalar_one_or_none()

            if not original_run:
                raise HTTPException(status_code=404, detail="Run not found")

            original_input = original_run.input_data or {}
            original_config = original_run.config or {}

            new_input = {
                "keyword": (data.keyword if data and data.keyword else original_input.get("keyword", "")),
                "target_audience": (data.target_audience if data and data.target_audience else original_input.get("target_audience")),
                "competitor_urls": (data.competitor_urls if data and data.competitor_urls else original_input.get("competitor_urls")),
                "additional_requirements": (
                    data.additional_requirements if data and data.additional_requirements else original_input.get("additional_requirements")
                ),
            }

            if data and data.model_config_override:
                new_model_config = data.model_config_override.model_dump()
            else:
                new_model_config = original_config.get(
                    "model_config",
                    {
                        "platform": "gemini",
                        "model": "gemini-1.5-pro",
                        "options": {},
                    },
                )

            new_workflow_config = {
                "model_config": new_model_config,
                "step_configs": original_config.get("step_configs"),
                "tool_config": original_config.get("tool_config"),
                "options": original_config.get("options"),
                "pack_id": original_config.get("pack_id", "default"),
                "input": new_input,
                "keyword": new_input["keyword"],
                "target_audience": new_input.get("target_audience"),
                "competitor_urls": new_input.get("competitor_urls"),
                "additional_requirements": new_input.get("additional_requirements"),
            }

            new_run_id = str(uuid.uuid4())
            now = datetime.now()

            new_run = Run(
                id=new_run_id,
                tenant_id=tenant_id,
                status=RunStatus.PENDING.value,
                current_step=None,
                input_data=new_input,
                config=new_workflow_config,
                created_at=now,
                updated_at=now,
            )
            session.add(new_run)

            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="clone",
                resource_type="run",
                resource_id=new_run_id,
                details={
                    "source_run_id": run_id,
                    "keyword": new_input["keyword"],
                    "start_workflow": data.start_workflow if data else True,
                },
            )

            await session.flush()
            logger.info(
                "Run cloned",
                extra={"new_run_id": new_run_id, "source_run_id": run_id, "tenant_id": tenant_id},
            )

            start_workflow = data.start_workflow if data else True
            if start_workflow and temporal_client is not None:
                try:
                    await temporal_client.start_workflow(
                        "ArticleWorkflow",
                        args=[tenant_id, new_run_id, new_workflow_config, None],
                        id=new_run_id,
                        task_queue=task_queue,
                    )

                    new_run.status = RunStatus.RUNNING.value
                    new_run.started_at = now
                    new_run.updated_at = now

                    logger.info(
                        "Cloned workflow started",
                        extra={"run_id": new_run_id, "task_queue": task_queue},
                    )

                    await ws_manager.broadcast_run_update(
                        run_id=new_run_id,
                        event_type="run.started",
                        status=RunStatus.RUNNING.value,
                    )

                except Exception as wf_error:
                    logger.error(f"Failed to start cloned workflow: {wf_error}", exc_info=True)
                    new_run.status = RunStatus.FAILED.value
                    new_run.error_code = "WORKFLOW_START_FAILED"
                    new_run.error_message = str(wf_error)
                    new_run.updated_at = now

            return run_orm_to_response(new_run)

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to clone run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to clone run") from e


@router.delete("/{run_id}")
async def cancel_run(run_id: str, user: AuthUser = Depends(get_current_user)) -> dict[str, bool]:
    """Cancel a running workflow."""
    tenant_id = user.tenant_id
    logger.info(
        "Cancelling run",
        extra={"run_id": run_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    db_manager = _get_tenant_db_manager()
    temporal_client = _get_temporal_client()
    ws_manager = _get_ws_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            cancellable_statuses = [
                RunStatus.PENDING.value,
                RunStatus.RUNNING.value,
                RunStatus.WAITING_APPROVAL.value,
            ]
            if run.status not in cancellable_statuses:
                raise HTTPException(status_code=400, detail=f"Run cannot be cancelled (current status: {run.status})")

            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="cancel",
                resource_type="run",
                resource_id=run_id,
                details={"previous_status": run.status},
            )

            if temporal_client is not None:
                try:
                    workflow_handle = temporal_client.get_workflow_handle(run_id)
                    await workflow_handle.cancel()
                    logger.info("Temporal workflow cancelled", extra={"run_id": run_id})
                except Exception as cancel_error:
                    logger.warning(f"Failed to cancel Temporal workflow: {cancel_error}")
            else:
                logger.warning("Temporal client not available, workflow not cancelled", extra={"run_id": run_id})

            run.status = RunStatus.CANCELLED.value
            run.updated_at = datetime.now()
            run.completed_at = datetime.now()

            await session.flush()
            logger.info("Run cancelled", extra={"run_id": run_id, "tenant_id": tenant_id})

            await ws_manager.broadcast_run_update(
                run_id=run_id,
                event_type="run.cancelled",
                status=RunStatus.CANCELLED.value,
            )

            return {"success": True}

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to cancel run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to cancel run") from e


@router.delete("/{run_id}/delete")
async def delete_run(run_id: str, user: AuthUser = Depends(get_current_user)) -> dict[str, bool]:
    """Delete a completed, failed, or cancelled run."""
    tenant_id = user.tenant_id
    logger.info(
        "Deleting run",
        extra={"run_id": run_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    db_manager = _get_tenant_db_manager()
    store = _get_artifact_store()

    try:
        async with db_manager.get_session(tenant_id) as session:
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            deletable_statuses = [
                RunStatus.COMPLETED.value,
                RunStatus.FAILED.value,
                RunStatus.CANCELLED.value,
                RunStatus.WAITING_IMAGE_INPUT.value,
                RunStatus.WAITING_APPROVAL.value,
            ]
            if run.status not in deletable_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"Run cannot be deleted while in progress (current status: {run.status}). Cancel it first.",
                )

            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="delete",
                resource_type="run",
                resource_id=run_id,
                details={"status": run.status, "keyword": run.input_data.get("keyword") if run.input_data else None},
            )

            try:
                deleted_count = await store.delete_run_artifacts(tenant_id, run_id)
                logger.info(f"Deleted {deleted_count} artifacts from storage", extra={"run_id": run_id})
            except Exception as storage_error:
                logger.warning(f"Failed to delete some artifacts from storage: {storage_error}")

            await session.execute(sql_delete(ArtifactModel).where(ArtifactModel.run_id == run_id))
            await session.execute(sql_delete(Step).where(Step.run_id == run_id))
            await session.delete(run)

            await session.flush()
            logger.info("Run deleted", extra={"run_id": run_id, "tenant_id": tenant_id})

            return {"success": True}

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to delete run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete run") from e


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_runs(
    request: BulkDeleteRequest,
    user: AuthUser = Depends(get_current_user),
) -> BulkDeleteResponse:
    """Delete multiple runs. Running/pending/waiting runs are cancelled first."""
    tenant_id = user.tenant_id
    logger.info(
        "Bulk deleting runs",
        extra={"run_ids": request.run_ids, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    db_manager = _get_tenant_db_manager()
    store = _get_artifact_store()
    temporal_client = _get_temporal_client()

    deleted: list[str] = []
    failed: list[dict[str, str]] = []

    cancellable_statuses = [
        RunStatus.PENDING.value,
        RunStatus.RUNNING.value,
        RunStatus.WAITING_APPROVAL.value,
    ]

    try:
        async with db_manager.get_session(tenant_id) as session:
            for run_id in request.run_ids:
                try:
                    query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
                    result = await session.execute(query)
                    run = result.scalar_one_or_none()

                    if not run:
                        failed.append({"id": run_id, "error": "Run not found"})
                        continue

                    if run.status in cancellable_statuses:
                        if temporal_client is not None:
                            try:
                                workflow_handle = temporal_client.get_workflow_handle(run_id)
                                await workflow_handle.cancel()
                                logger.info("Temporal workflow cancelled for bulk delete", extra={"run_id": run_id})
                            except Exception as cancel_error:
                                logger.warning(f"Failed to cancel Temporal workflow {run_id}: {cancel_error}")

                        run.status = RunStatus.CANCELLED.value
                        run.updated_at = datetime.utcnow()
                        await session.flush()

                        audit = AuditLogger(session)
                        await audit.log(
                            user_id=user.user_id,
                            action="cancel",
                            resource_type="run",
                            resource_id=run_id,
                            details={"previous_status": run.status, "bulk": True, "reason": "bulk_delete"},
                        )

                    audit = AuditLogger(session)
                    await audit.log(
                        user_id=user.user_id,
                        action="delete",
                        resource_type="run",
                        resource_id=run_id,
                        details={"status": run.status, "bulk": True},
                    )

                    try:
                        await store.delete_run_artifacts(tenant_id, run_id)
                    except Exception as storage_error:
                        logger.warning(f"Failed to delete artifacts for {run_id}: {storage_error}")

                    await session.execute(sql_delete(ArtifactModel).where(ArtifactModel.run_id == run_id))
                    await session.execute(sql_delete(Step).where(Step.run_id == run_id))
                    await session.delete(run)

                    deleted.append(run_id)

                except Exception as e:
                    logger.error(f"Failed to delete run {run_id}: {e}")
                    failed.append({"id": run_id, "error": str(e)})

            await session.flush()

        logger.info(f"Bulk delete completed: {len(deleted)} deleted, {len(failed)} failed")
        return BulkDeleteResponse(deleted=deleted, failed=failed)

    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to bulk delete runs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to bulk delete runs") from e
