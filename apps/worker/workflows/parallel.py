"""Parallel step execution helper for step3 (3A/3B/3C).

Implements retry logic for parallel steps:
- All three steps run concurrently
- Failed steps are retried (max 3 attempts per step)
- All three must succeed before proceeding to approval
- NO fallback to different models/tools
"""

import asyncio
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

# Import logger for workflow-safe logging
workflow_logger = workflow.logger


class ParallelStepError(Exception):
    """Error when parallel steps fail after retries."""

    def __init__(self, failed_steps: list[str], message: str = ""):
        self.failed_steps = failed_steps
        super().__init__(message or f"Parallel steps failed: {failed_steps}")


# Individual step retry policy
STEP_RETRY_POLICY = RetryPolicy(
    maximum_attempts=3,
    initial_interval=timedelta(seconds=2),
    maximum_interval=timedelta(seconds=30),
    backoff_coefficient=2.0,
)

# Timeout per parallel step
PARALLEL_STEP_TIMEOUT = timedelta(seconds=120)


async def run_parallel_steps(
    tenant_id: str,
    run_id: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Execute step 3A/3B/3C in parallel with retry logic.

    Implementation:
    1. Launch all three steps concurrently
    2. Collect results, track failures
    3. Retry only failed steps (up to MAX_RETRIES total rounds)
    4. All three must succeed for the function to return

    Args:
        tenant_id: Tenant identifier
        run_id: Run identifier
        config: Workflow configuration

    Returns:
        dict with results from all three steps

    Raises:
        ParallelStepError: If any step fails after max retries
    """
    max_retry_rounds = 3  # Total retry rounds for the parallel group
    parallel_steps = ["step3a", "step3b", "step3c"]
    activity_names = {
        "step3a": "step3a_query_analysis",
        "step3b": "step3b_cooccurrence_extraction",
        "step3c": "step3c_competitor_analysis",
    }

    activity_args = {
        "tenant_id": tenant_id,
        "run_id": run_id,
        "config": config,
    }

    completed: dict[str, Any] = {}
    last_errors: dict[str, str] = {}

    for attempt in range(1, max_retry_rounds + 1):
        # Determine which steps still need to run
        pending = [s for s in parallel_steps if s not in completed]
        if not pending:
            break

        workflow_logger.info(f"Parallel steps attempt {attempt}/{max_retry_rounds}: running {pending}")

        # Launch pending steps concurrently
        tasks = []
        for step in pending:
            activity_name = activity_names[step]
            task = workflow.execute_activity(
                activity_name,
                activity_args,
                start_to_close_timeout=PARALLEL_STEP_TIMEOUT,
                retry_policy=STEP_RETRY_POLICY,
            )
            tasks.append((step, task))

        # Wait for all tasks, collecting results and exceptions
        results = await asyncio.gather(
            *[t[1] for t in tasks],
            return_exceptions=True,
        )

        # Process results
        for (step, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                # Extract error message with type and traceback info
                if isinstance(result, ActivityError):
                    error_msg = str(result.cause) if result.cause else str(result)
                    error_type = type(result.cause).__name__ if result.cause else "ActivityError"
                else:
                    error_msg = str(result)
                    error_type = type(result).__name__
                # Store both message and type for better diagnostics
                last_errors[step] = f"[{error_type}] {error_msg}"
                workflow_logger.warning(f"{step} failed (attempt {attempt}): [{error_type}] {error_msg}")
            else:
                completed[step] = result
                workflow_logger.info(f"{step} succeeded on attempt {attempt}")

    # Check if all steps completed
    if len(completed) < len(parallel_steps):
        failed = [s for s in parallel_steps if s not in completed]
        error_details = {s: last_errors.get(s, "unknown error") for s in failed}
        raise ParallelStepError(
            failed_steps=failed,
            message=f"Parallel steps failed after {max_retry_rounds} attempts: {error_details}",
        )

    workflow_logger.info("All parallel steps completed successfully")
    return completed
