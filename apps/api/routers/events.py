"""Events router.

Handles audit log/events listing for runs.
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from apps.api.auth import get_current_user
from apps.api.auth.schemas import AuthUser
from apps.api.db import AuditLogger, Run, TenantIdValidationError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["events"])


# =============================================================================
# Lazy imports to avoid circular dependencies
# =============================================================================


def _get_tenant_db_manager() -> Any:
    """Get tenant DB manager."""
    from apps.api.db.tenant import get_tenant_manager

    return get_tenant_manager()


# =============================================================================
# Pydantic Models
# =============================================================================


class EventDetails(BaseModel):
    """Event details with structured information."""

    run_id: str | None = None
    step: str | None = None
    tenant_id: str | None = None
    attempt: int | None = None
    duration_ms: int | None = None
    error: str | None = None
    error_category: str | None = None
    reason: str | None = None
    timestamp: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class EventResponse(BaseModel):
    """Event response for audit log."""

    id: str
    event_type: str
    step: str | None = None
    payload: dict[str, Any]
    details: EventDetails | None = None
    created_at: str


# =============================================================================
# Endpoints
# =============================================================================


def _extract_event_details(log_details: dict[str, Any] | None) -> EventDetails:
    """Extract structured details from audit log."""
    if not log_details:
        return EventDetails()

    payload = log_details.get("payload", {})

    return EventDetails(
        run_id=log_details.get("run_id"),
        step=log_details.get("step") or payload.get("step"),
        tenant_id=log_details.get("tenant_id"),
        attempt=payload.get("attempt"),
        duration_ms=payload.get("duration_ms"),
        error=payload.get("error"),
        error_category=payload.get("category"),
        reason=payload.get("reason"),
        timestamp=log_details.get("timestamp"),
        extra={k: v for k, v in payload.items() if k not in ["attempt", "duration_ms", "error", "category", "reason", "step"]},
    )


def _get_step_from_log(log: Any) -> str | None:
    """Extract step name from audit log."""
    if log.resource_type == "step":
        return log.resource_id
    if log.details:
        return log.details.get("step") or log.details.get("payload", {}).get("step")
    return None


@router.get("/api/runs/{run_id}/events", response_model=list[EventResponse])
async def list_events(
    run_id: str,
    step: str | None = None,
    event_type: str | None = Query(default=None, description="Filter by event type (e.g., step.started, step.failed)"),
    since: datetime | None = Query(default=None, description="Return events after this timestamp"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: AuthUser = Depends(get_current_user),
) -> list[EventResponse]:
    """List events/audit logs for a run.

    Returns all events related to a run, including:
    - Run lifecycle events (created, started, completed, failed)
    - Step events (started, succeeded, failed, retrying)
    - Repair events (applied, failed)
    - Artifact events (upload, download)

    Events are sorted by created_at in descending order (newest first).
    """
    tenant_id = user.tenant_id
    logger.debug(
        "Listing events",
        extra={
            "run_id": run_id,
            "tenant_id": tenant_id,
            "step": step,
            "event_type": event_type,
            "since": since.isoformat() if since else None,
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

            # Query audit logs for this run
            audit = AuditLogger(session)

            # Get run-level events
            logs = await audit.get_logs(
                resource_type="run",
                resource_id=run_id,
                action=event_type,
                limit=limit * 2,  # Get more to account for filtering
            )

            # Get step-level events for this run
            step_logs = await audit.get_logs(
                resource_type="step",
                action=event_type,
                limit=limit * 2,
            )
            # Filter step logs that belong to this run
            step_logs = [log for log in step_logs if log.details and log.details.get("run_id") == run_id]

            # Also get artifact-related logs for this run
            artifact_logs = await audit.get_logs(
                resource_type="artifact",
                limit=limit,
            )
            # Filter artifact logs that belong to this run
            artifact_logs = [log for log in artifact_logs if log.details and log.details.get("run_id") == run_id]

            # Combine all logs
            all_logs = logs + step_logs + artifact_logs

            # Apply since filter
            if since:
                all_logs = [log for log in all_logs if log.created_at >= since]

            # Apply step filter if provided
            if step:
                all_logs = [log for log in all_logs if _get_step_from_log(log) == step]

            # Sort by created_at descending
            all_logs.sort(key=lambda x: x.created_at, reverse=True)

            # Apply pagination
            paginated_logs = all_logs[offset : offset + limit]

            return [
                EventResponse(
                    id=str(log.id),
                    event_type=log.action,
                    step=_get_step_from_log(log),
                    payload={
                        "user_id": log.user_id,
                        "resource_type": log.resource_type,
                        "resource_id": log.resource_id,
                        "details": log.details,
                        "entry_hash": log.entry_hash[:16] + "..." if log.entry_hash else None,
                    },
                    details=_extract_event_details(log.details),
                    created_at=log.created_at.isoformat(),
                )
                for log in paginated_logs
            ]

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to list events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list events") from e
