"""Events router.

Handles audit log/events listing for runs.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
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


class EventResponse(BaseModel):
    """Event response for audit log."""

    id: str
    event_type: str
    payload: dict[str, Any]
    created_at: str


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/api/runs/{run_id}/events", response_model=list[EventResponse])
async def list_events(
    run_id: str,
    step: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    user: AuthUser = Depends(get_current_user),
) -> list[EventResponse]:
    """List events/audit logs for a run."""
    tenant_id = user.tenant_id
    logger.debug(
        "Listing events",
        extra={
            "run_id": run_id,
            "tenant_id": tenant_id,
            "step": step,
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
            logs = await audit.get_logs(
                resource_type="run",
                resource_id=run_id,
                limit=limit,
            )

            # Also get artifact-related logs for this run
            artifact_logs = await audit.get_logs(
                resource_type="artifact",
                limit=limit,
            )
            # Filter artifact logs that belong to this run
            artifact_logs = [log for log in artifact_logs if log.details and log.details.get("run_id") == run_id]

            # Combine and sort by created_at
            all_logs = logs + artifact_logs
            all_logs.sort(key=lambda x: x.created_at, reverse=True)

            # Apply step filter if provided
            if step:
                all_logs = [log for log in all_logs if log.details and log.details.get("step") == step]

            return [
                EventResponse(
                    id=str(log.id),
                    event_type=log.action,
                    payload={
                        "user_id": log.user_id,
                        "resource_type": log.resource_type,
                        "resource_id": log.resource_id,
                        "details": log.details,
                        "entry_hash": log.entry_hash[:16] + "...",
                    },
                    created_at=log.created_at.isoformat(),
                )
                for log in all_logs[:limit]
            ]

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to list events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list events") from e
