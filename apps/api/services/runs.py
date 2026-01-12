"""Run-related service functions.

Helper functions for converting ORM models to Pydantic responses,
inferring step status from storage, and syncing with Temporal.
"""

import logging
from datetime import datetime
from typing import Any

from apps.api.db import Run, Step
from apps.api.schemas.enums import RunStatus, StepStatus
from apps.api.schemas.runs import (
    ArtifactRef,
    ModelConfig,
    ModelConfigOptions,
    RunError,
    RunInput,
    RunOptions,
    RunResponse,
    StepModelConfig,
    StepResponse,
    ToolConfig,
)

logger = logging.getLogger(__name__)


def run_orm_to_response(run: Run, steps: list[Step] | None = None) -> RunResponse:
    """Convert Run ORM model to RunResponse Pydantic model."""
    # Parse stored JSON configs
    input_data = run.input_data or {}
    config = run.config or {}

    run_input = RunInput(
        keyword=input_data.get("keyword", ""),
        target_audience=input_data.get("target_audience"),
        competitor_urls=input_data.get("competitor_urls"),
        additional_requirements=input_data.get("additional_requirements"),
    )

    model_config_data = config.get("model_config", {})
    model_config = ModelConfig(
        platform=model_config_data.get("platform", "gemini"),
        model=model_config_data.get("model", "gemini-1.5-pro"),
        options=ModelConfigOptions(**model_config_data.get("options", {})),
    )

    tool_config_data = config.get("tool_config")
    tool_config = ToolConfig(**tool_config_data) if tool_config_data else None

    options_data = config.get("options")
    options = RunOptions(**options_data) if options_data else None

    # Parse step_configs
    step_configs_data = config.get("step_configs")
    step_configs: list[StepModelConfig] | None = None
    if step_configs_data:
        step_configs = [StepModelConfig(**sc) for sc in step_configs_data]

    # Convert steps if provided
    step_responses: list[StepResponse] = []
    if steps:
        for step_orm in steps:
            step_responses.append(
                StepResponse(
                    id=str(step_orm.id),
                    run_id=str(step_orm.run_id),
                    step_name=step_orm.step_name,  # DB column is step_name
                    status=StepStatus(step_orm.status),
                    attempts=[],
                    started_at=step_orm.started_at.isoformat() if step_orm.started_at else None,
                    completed_at=step_orm.completed_at.isoformat() if step_orm.completed_at else None,
                    error_code=step_orm.error_code,
                    error_message=step_orm.error_message,
                )
            )

    # Build error if present
    error = None
    if run.error_message:
        error = RunError(
            code=run.error_code or "UNKNOWN",
            message=run.error_message,
            step=run.current_step,
        )

    return RunResponse(
        id=str(run.id),
        tenant_id=run.tenant_id,
        status=RunStatus(run.status),
        current_step=run.current_step,
        input=run_input,
        model_config=model_config,
        step_configs=step_configs,
        tool_config=tool_config,
        options=options,
        steps=step_responses,
        created_at=run.created_at.isoformat(),
        updated_at=run.updated_at.isoformat(),
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        error=error,
    )


async def get_steps_from_storage(
    tenant_id: str,
    run_id: str,
    current_step: str | None,
    run_status: str | None = None,
    artifact_store: Any = None,
) -> list[StepResponse]:
    """Build step responses from storage artifacts.

    When DB doesn't have step records, we infer step status from storage.
    If a step has output.json in storage, it's considered completed.
    Also builds artifact refs for each step.

    Args:
        tenant_id: Tenant ID
        run_id: Run ID
        current_step: Current step name from Temporal
        run_status: Overall run status (e.g., "failed", "running", "completed")
        artifact_store: ArtifactStore instance (passed from caller to avoid circular import)
    """
    if artifact_store is None:
        return []

    try:
        artifact_paths = await artifact_store.list_run_artifacts(tenant_id, run_id)
    except Exception as e:
        logger.warning(f"Failed to list artifacts for steps: {e}")
        return []

    # Extract step names and artifacts from paths like: storage/tenant/run/step0/output.json
    completed_steps: set[str] = set()
    step_artifacts: dict[str, list[str]] = {}  # step_name -> list of artifact paths

    for path in artifact_paths:
        parts = path.split("/")
        if len(parts) >= 4:
            step_name = parts[-2]
            # Track artifacts per step
            if step_name not in step_artifacts:
                step_artifacts[step_name] = []
            step_artifacts[step_name].append(path)
            # Mark step as completed if it has output.json
            if parts[-1] == "output.json":
                completed_steps.add(step_name)

    # Define all workflow steps in order
    # Note: step6_5 in storage corresponds to step6.5 in UI
    # step-1 is the input step (always completed when workflow starts)
    # step3 is a parent step whose status is derived from step3a/b/c
    all_steps = [
        "step-1",
        "step0",
        "step1",
        "step1_5",
        "step2",
        "step3",
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
        "step11",
        "step12",
    ]

    # Steps that are always completed once workflow starts (no artifact needed)
    always_completed_steps = {"step-1", "step0"}

    # Define parent steps with their children (parent status derived from children)
    parent_child_groups = {
        "step3": ["step3a", "step3b", "step3c"],
    }

    # Define parallel step groups (these steps run in parallel, not sequentially)
    parallel_groups = {
        "step3a": {"step3a", "step3b", "step3c"},
        "step3b": {"step3a", "step3b", "step3c"},
        "step3c": {"step3a", "step3b", "step3c"},
        "step7a": {"step7a", "step7b"},
        "step7b": {"step7a", "step7b"},
    }

    # Define steps after each parallel group (used for inference)
    steps_after_parallel = {
        "step3a": "step3_5",
        "step3b": "step3_5",
        "step3c": "step3_5",
        "step7a": "step8",
        "step7b": "step8",
    }

    step_responses: list[StepResponse] = []
    for i, step_name in enumerate(all_steps):
        # Normalize step name (step6_5 -> step6.5 for display consistency)
        display_name = step_name.replace("_", ".")

        # Determine status
        status = _determine_step_status(
            step_name=step_name,
            display_name=display_name,
            completed_steps=completed_steps,
            current_step=current_step,
            run_status=run_status,
            always_completed_steps=always_completed_steps,
            parent_child_groups=parent_child_groups,
            parallel_groups=parallel_groups,
            steps_after_parallel=steps_after_parallel,
            all_steps=all_steps,
            step_index=i,
        )

        # Build artifact refs for this step
        artifacts: list[ArtifactRef] = []
        paths = step_artifacts.get(step_name, [])
        for idx, artifact_path in enumerate(paths):
            # Extract filename for content type inference
            filename = artifact_path.split("/")[-1] if "/" in artifact_path else artifact_path
            content_type = _infer_content_type(filename)

            artifacts.append(
                ArtifactRef(
                    id=f"{run_id}-{step_name}-{idx}",
                    step_id=f"{run_id}-{step_name}",
                    ref_path=artifact_path,
                    digest="",  # Unknown from path only
                    content_type=content_type,
                    size_bytes=0,  # Unknown from path only
                    created_at=datetime.now().isoformat(),
                )
            )

        step_responses.append(
            StepResponse(
                id=f"{run_id}-{step_name}",
                run_id=run_id,
                step_name=display_name,
                status=status,
                attempts=[],
                started_at=None,
                completed_at=None,
                artifacts=artifacts if artifacts else None,
            )
        )

    return step_responses


def _determine_step_status(
    step_name: str,
    display_name: str,
    completed_steps: set[str],
    current_step: str | None,
    run_status: str | None,
    always_completed_steps: set[str],
    parent_child_groups: dict[str, list[str]],
    parallel_groups: dict[str, set[str]],
    steps_after_parallel: dict[str, str],
    all_steps: list[str],
    step_index: int,
) -> StepStatus:
    """Determine the status of a step based on various conditions."""
    if step_name in completed_steps:
        return StepStatus.COMPLETED

    if current_step and current_step == step_name:
        if run_status == RunStatus.FAILED.value:
            return StepStatus.FAILED
        return StepStatus.RUNNING

    if current_step and current_step == display_name:
        if run_status == RunStatus.FAILED.value:
            return StepStatus.FAILED
        return StepStatus.RUNNING

    # Special handling for input steps: always completed once workflow starts
    if step_name in always_completed_steps:
        return StepStatus.COMPLETED

    # Special handling for parent steps (step3): derive from children
    if step_name in parent_child_groups:
        children = parent_child_groups[step_name]
        all_children_completed = all(child in completed_steps for child in children)
        if all_children_completed:
            return StepStatus.COMPLETED
        if current_step in children:
            if run_status == RunStatus.FAILED.value:
                return StepStatus.FAILED
            return StepStatus.RUNNING
        return StepStatus.PENDING

    # Special handling for parallel steps (step3a/b/c, step7a/b)
    if step_name in parallel_groups:
        next_step = steps_after_parallel[step_name]
        next_step_idx = all_steps.index(next_step) if next_step in all_steps else -1
        if next_step_idx >= 0:
            later_completed = any(s in completed_steps for s in all_steps[next_step_idx:])
            later_running = current_step in all_steps[next_step_idx:] if current_step else False
            if later_completed or later_running:
                return StepStatus.COMPLETED
        return StepStatus.PENDING

    # Check if any later step is completed (means this one was skipped or completed)
    later_completed = any(s in completed_steps for s in all_steps[step_index + 1 :])
    if later_completed:
        return StepStatus.COMPLETED

    return StepStatus.PENDING


def _infer_content_type(filename: str) -> str:
    """Infer content type from filename extension."""
    if filename.endswith(".json"):
        return "application/json"
    if filename.endswith(".html"):
        return "text/html"
    if filename.endswith(".md"):
        return "text/markdown"
    return "application/octet-stream"


async def sync_run_with_temporal(
    run: Run,
    temporal_client: Any,
) -> bool:
    """Sync Run DB record with Temporal workflow state.

    Queries Temporal for current workflow status and updates DB if needed.
    Returns True if DB was updated.

    Args:
        run: Run ORM model to sync
        temporal_client: TemporalClient instance (passed from caller to avoid circular import)
    """
    if temporal_client is None:
        return False

    try:
        workflow_handle = temporal_client.get_workflow_handle(str(run.id))

        # Query workflow status
        workflow_status = await workflow_handle.query("get_status")
        current_step = workflow_status.get("current_step", "")
        rejected = workflow_status.get("rejected", False)
        rejection_reason = workflow_status.get("rejection_reason")

        # Check workflow execution status
        workflow_desc = await workflow_handle.describe()
        workflow_execution_status = workflow_desc.status

        # Import enum for comparison
        from temporalio.client import WorkflowExecutionStatus

        db_updated = False
        now = datetime.now()

        # Update current_step if changed
        if current_step and run.current_step != current_step:
            run.current_step = current_step
            run.updated_at = now
            db_updated = True
            logger.debug(f"Synced current_step: {current_step} for run {run.id}")

        # Update status based on Temporal state
        if workflow_execution_status == WorkflowExecutionStatus.COMPLETED:
            if run.status != RunStatus.COMPLETED.value:
                run.status = RunStatus.COMPLETED.value
                run.completed_at = now
                run.updated_at = now
                db_updated = True
                logger.info(f"Run {run.id} marked as completed from Temporal sync")

        elif workflow_execution_status == WorkflowExecutionStatus.FAILED:
            if run.status != RunStatus.FAILED.value:
                run.status = RunStatus.FAILED.value
                run.updated_at = now
                db_updated = True
                logger.info(f"Run {run.id} marked as failed from Temporal sync")

        elif workflow_execution_status == WorkflowExecutionStatus.CANCELED:
            if run.status != RunStatus.CANCELLED.value:
                run.status = RunStatus.CANCELLED.value
                run.updated_at = now
                db_updated = True
                logger.info(f"Run {run.id} marked as cancelled from Temporal sync")

        elif workflow_execution_status == WorkflowExecutionStatus.RUNNING:
            db_updated = _handle_running_workflow(
                run=run,
                current_step=current_step,
                rejected=rejected,
                rejection_reason=rejection_reason,
                now=now,
            )

        return db_updated

    except Exception as e:
        # Temporal query failed - workflow may not exist or be terminated
        logger.debug(f"Failed to sync with Temporal for run {run.id}: {e}")
        return False


def _handle_running_workflow(
    run: Run,
    current_step: str,
    rejected: bool,
    rejection_reason: str | None,
    now: datetime,
) -> bool:
    """Handle status updates for a running workflow.

    Determines run status based on Temporal workflow state:
    - waiting_approval: Step3 approval pending
    - waiting_image_input: Step11 user interaction pending
    - running: Normal execution (including parallel steps)
    """
    db_updated = False

    # Step11 waiting states (require user input)
    step11_waiting_states = (
        "waiting_image_generation",
        "step11_position_review",
        "step11_image_instructions",
        "step11_image_review",
        "step11_preview",
    )

    # Note: Parallel steps (step3a/3b/3c) are handled normally as RUNNING

    # Check if waiting for approval (Step3)
    if current_step == "waiting_approval":
        if run.status != RunStatus.WAITING_APPROVAL.value:
            run.status = RunStatus.WAITING_APPROVAL.value
            run.updated_at = now
            db_updated = True
            logger.info(f"Run {run.id} marked as waiting_approval from Temporal sync")

    # Check if waiting for image input (Step11)
    elif current_step in step11_waiting_states:
        if run.status != RunStatus.WAITING_IMAGE_INPUT.value:
            run.status = RunStatus.WAITING_IMAGE_INPUT.value
            run.updated_at = now
            db_updated = True
            logger.info(f"Run {run.id} marked as waiting_image_input from Temporal sync")

    elif rejected:
        if run.status != RunStatus.FAILED.value:
            run.status = RunStatus.FAILED.value
            run.error_message = rejection_reason or "Rejected by user"
            run.updated_at = now
            db_updated = True

    # Only update to RUNNING if workflow is actively executing
    # (has a valid current_step and not in a waiting state)
    elif current_step and current_step not in ("", "pre_approval", "post_approval"):
        if run.status not in (
            RunStatus.RUNNING.value,
            RunStatus.WAITING_APPROVAL.value,
            RunStatus.WAITING_IMAGE_INPUT.value,
        ):
            run.status = RunStatus.RUNNING.value
            run.updated_at = now
            db_updated = True
            logger.debug(f"Run {run.id} marked as running (step: {current_step})")

    # If current_step is empty or phase marker, don't change status
    # (workflow may be transitioning between phases)

    return db_updated
