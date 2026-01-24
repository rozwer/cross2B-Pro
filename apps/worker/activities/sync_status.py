"""Activity for synchronizing workflow state with API DB.

This activity is called at the end of workflow execution to ensure
the API database reflects the final workflow state.
"""

import logging
from datetime import datetime
from typing import Any

from temporalio import activity

logger = logging.getLogger(__name__)

# Valid state transitions for run status
# Each key is the current state, and values are allowed next states
VALID_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"running", "cancelled", "failed"},
    "workflow_starting": {"running", "failed", "cancelled"},
    "running": {"waiting_approval", "waiting_step1_approval", "waiting_image_input", "paused", "completed", "failed", "cancelled"},
    "paused": {"running", "completed", "failed", "cancelled"},  # Can resume, complete, fail, or cancel
    "waiting_approval": {"running", "paused", "completed", "failed", "cancelled"},
    "waiting_step1_approval": {
        "running",
        "paused",
        "completed",
        "failed",
        "cancelled",
    },  # Step1 approval after competitor/related KW extraction
    "waiting_image_input": {"running", "paused", "completed", "failed", "cancelled"},
    "completed": set(),  # Terminal state - no transitions allowed
    "failed": set(),  # Terminal state - no transitions allowed
    "cancelled": set(),  # Terminal state - no transitions allowed
}


@activity.defn
async def sync_run_status(args: dict[str, Any]) -> dict[str, Any]:
    """Synchronize run status with API database.

    This activity updates the Run record in the API database to reflect
    the final workflow state. It is called at workflow completion.

    Args:
        args: Activity arguments containing:
            - tenant_id: Tenant identifier
            - run_id: Run identifier
            - status: Final status (completed, failed, cancelled)
            - current_step: Final step reached
            - error_code: Optional error code if failed
            - error_message: Optional error message if failed
            - artifact_refs: Optional dict of artifact references

    Returns:
        dict with success status and updated fields
    """
    tenant_id = args["tenant_id"]
    run_id = args["run_id"]
    status = args.get("status", "completed")
    current_step = args.get("current_step", "completed")
    error_code = args.get("error_code")
    error_message = args.get("error_message")

    logger.info(f"Syncing run status: run_id={run_id}, status={status}, step={current_step}")

    try:
        # Import DB components
        from apps.api.db import Run, TenantDBManager

        db_manager = TenantDBManager()

        async with db_manager.get_session(tenant_id) as session:
            from sqlalchemy import select

            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                logger.warning(f"Run not found for sync: {run_id}")
                return {"success": False, "error": "Run not found"}

            now = datetime.now()
            updated_fields = []

            # Update status with state transition validation
            if run.status != status:
                current_status = run.status
                allowed_transitions = VALID_STATUS_TRANSITIONS.get(current_status, set())

                if status in allowed_transitions:
                    run.status = status
                    updated_fields.append("status")
                else:
                    # Log invalid transition but don't fail - the workflow's state is authoritative
                    logger.warning(
                        f"Invalid state transition skipped: {current_status} -> {status} "
                        f"(run_id={run_id}). Allowed: {allowed_transitions or 'none (terminal state)'}"
                    )

            # Update current_step
            if run.current_step != current_step:
                run.current_step = current_step
                updated_fields.append("current_step")

            # Update completion timestamp for terminal states
            if status in ("completed", "failed", "cancelled"):
                if run.completed_at is None:
                    run.completed_at = now
                    updated_fields.append("completed_at")

            # Update error fields if provided
            if error_code and run.error_code != error_code:
                run.error_code = error_code
                updated_fields.append("error_code")

            if error_message and run.error_message != error_message:
                run.error_message = error_message
                updated_fields.append("error_message")

            # Always update timestamp
            run.updated_at = now

            await session.flush()

            if updated_fields:
                logger.info(f"Run status synced: run_id={run_id}, updated={updated_fields}")
            else:
                logger.debug(f"Run status sync no-op: run_id={run_id}, status already={status}")

            return {
                "success": True,
                "run_id": run_id,
                "status": status,
                "updated_fields": updated_fields,
            }

    except Exception as e:
        logger.error(f"Failed to sync run status: {e}", exc_info=True)
        # フォールバック禁止: 例外を ApplicationError として raise し、Activity 失敗とする
        from temporalio.exceptions import ApplicationError

        raise ApplicationError(
            f"Failed to sync run status for run_id={run_id}: {e}",
            type="SYNC_STATUS_FAILED",
            non_retryable=True,  # リトライはWorkflow側で管理
        ) from e
