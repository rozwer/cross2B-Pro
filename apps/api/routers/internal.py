"""Internal API router.

Handles internal endpoints for Worker communication.
These endpoints are called by Temporal Worker and assume Docker network isolation.
"""

import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from apps.api.db import AuditLogger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/internal", tags=["internal"])


# =============================================================================
# Lazy imports to avoid circular dependencies
# =============================================================================


def _get_tenant_db_manager() -> Any:
    """Get tenant DB manager."""
    from apps.api.db.tenant import get_tenant_manager

    return get_tenant_manager()


def _get_ws_manager() -> Any:
    """Get WebSocket manager from main module."""
    from apps.api.main import ws_manager

    return ws_manager


# =============================================================================
# Pydantic Models
# =============================================================================


class StepUpdateRequest(BaseModel):
    """Request to update step status (internal API)."""

    run_id: str
    tenant_id: str  # Required: Worker must always provide tenant_id for multi-tenant isolation
    step_name: str
    status: Literal["running", "completed", "failed"]
    error_code: str | None = None  # ErrorCategory enum value (RETRYABLE, NON_RETRYABLE, etc.)
    error_message: str | None = None
    retry_count: int = 0


class WSBroadcastRequest(BaseModel):
    """Request to broadcast WebSocket event (internal API)."""

    run_id: str
    step: str
    event_type: str = "step_progress"
    status: str = "in_progress"
    progress: int = 0
    message: str = ""
    details: dict[str, Any] | None = None


class AuditLogRequest(BaseModel):
    """Request to write audit log (internal API)."""

    tenant_id: str
    run_id: str
    step_name: str
    action: str
    details: dict[str, Any] | None = None


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/steps/update")
async def update_step_status(request: StepUpdateRequest) -> dict[str, bool]:
    """Update step status in DB (internal API for Worker).

    This endpoint is called by Temporal Worker to record step progress.
    No authentication required - assumes Docker network isolation.
    """
    logger.info(
        "Updating step status",
        extra={
            "run_id": request.run_id,
            "step_name": request.step_name,
            "status": request.status,
        },
    )

    db_manager = _get_tenant_db_manager()

    try:
        # tenant_id is now required - no fallback to ensure multi-tenant isolation
        tenant_id = request.tenant_id

        async with db_manager.get_session(tenant_id) as session:
            # UPSERT step record
            # Note: Cast :status to VARCHAR to avoid asyncpg type inference issues
            # (inconsistent types: text vs character varying)
            await session.execute(
                text("""
                    INSERT INTO steps (id, run_id, step_name, status, started_at, retry_count, error_code)
                    VALUES (
                        gen_random_uuid(),
                        CAST(:run_id AS UUID),
                        CAST(:step_name AS VARCHAR),
                        CAST(:status AS VARCHAR),
                        CASE WHEN CAST(:status AS VARCHAR) = 'running' THEN NOW() ELSE NULL END,
                        :retry_count,
                        CAST(:error_code AS VARCHAR)
                    )
                    ON CONFLICT (run_id, step_name)
                    DO UPDATE SET
                        status = CAST(:status AS VARCHAR),
                        started_at = CASE
                            WHEN CAST(:status AS VARCHAR) = 'running' THEN NOW()
                            ELSE steps.started_at
                        END,
                        completed_at = CASE
                            WHEN CAST(:status AS VARCHAR) IN ('completed', 'failed') THEN NOW()
                            ELSE NULL
                        END,
                        error_code = CAST(:error_code AS VARCHAR),
                        error_message = :error_message,
                        retry_count = :retry_count
                """),
                {
                    "run_id": request.run_id,
                    "step_name": request.step_name,
                    "status": request.status,
                    "error_code": request.error_code,
                    "error_message": request.error_message,
                    "retry_count": request.retry_count,
                },
            )
            await session.commit()

        return {"ok": True}

    except Exception as e:
        logger.error(f"Failed to update step status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update step status") from e


@router.post("/ws/broadcast")
async def broadcast_ws_event(request: WSBroadcastRequest) -> dict[str, bool]:
    """Broadcast WebSocket event (internal API for Worker).

    Enables Temporal Worker to send real-time progress updates to connected clients.
    """
    ws_manager = _get_ws_manager()

    try:
        await ws_manager.broadcast_step_event(
            run_id=request.run_id,
            step=request.step,
            event_type=request.event_type,
            status=request.status,
            progress=request.progress,
            message=request.message,
            details=request.details,
        )
        return {"ok": True}
    except Exception as e:
        logger.error(f"Failed to broadcast WS event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to broadcast event") from e


@router.post("/audit/log")
async def write_audit_log(request: AuditLogRequest) -> dict[str, bool]:
    """Write audit log entry (internal API for Worker).

    Records audit events with per-article output_digest for step10.
    Uses AuditLogger to ensure chain hash integrity.
    """
    db_manager = _get_tenant_db_manager()

    try:
        async with db_manager.get_session(request.tenant_id) as session:
            audit = AuditLogger(session)
            await audit.log(
                user_id="system",
                action=request.action,
                resource_type="step",
                resource_id=request.step_name,
                details={
                    "run_id": request.run_id,
                    "tenant_id": request.tenant_id,
                    **(request.details or {}),
                },
            )
            await session.commit()
        return {"ok": True}
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to write audit log") from e
