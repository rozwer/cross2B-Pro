"""Main Temporal Workflow for SEO article generation.

ArticleWorkflow orchestrates the entire article generation process:
- Pre-approval phase: step0 → step1 → step2 → step3 (parallel)
- Approval wait: Pauses for human approval via Temporal signal
- Post-approval phase: step4 → step5 → ... → step10

IMPORTANT:
- No fallback to different models/tools
- All artifacts stored via ArtifactStore (path/digest only in workflow)
- All state changes emit events for observability
"""

from datetime import timedelta
from typing import Any, cast

from temporalio import workflow
from temporalio.common import RetryPolicy

from .parallel import run_parallel_steps

# Activity timeouts as defined in workflow.md
STEP_TIMEOUTS: dict[str, int] = {
    "step0": 60,
    "step1": 300,
    "step2": 60,
    "step3a": 120,
    "step3b": 120,
    "step3c": 120,
    "step4": 180,
    "step5": 300,
    "step6": 180,
    "step6_5": 180,
    "step7a": 600,
    "step7b": 300,
    "step8": 300,
    "step9": 300,
    "step10": 120,
}

# Default retry policy: max 3 attempts with same conditions
DEFAULT_RETRY_POLICY = RetryPolicy(
    maximum_attempts=3,
    initial_interval=timedelta(seconds=1),
    maximum_interval=timedelta(seconds=30),
    backoff_coefficient=2.0,
)


@workflow.defn
class ArticleWorkflow:
    """Temporal Workflow for SEO article generation.

    This workflow implements the full article generation pipeline with:
    - Pre-approval phase (step0-3)
    - Human approval checkpoint
    - Post-approval phase (step4-10)

    Signals:
        approve(): Mark the run as approved, continue to post-approval
        reject(reason): Reject the run with a reason

    State is persisted via Temporal, artifacts via MinIO (ArtifactStore).
    """

    def __init__(self) -> None:
        """Initialize workflow state."""
        self.approved: bool = False
        self.rejected: bool = False
        self.rejection_reason: str | None = None
        self.current_step: str = "init"

    @workflow.signal
    async def approve(self) -> None:
        """Signal handler for approval."""
        self.approved = True

    @workflow.signal
    async def reject(self, reason: str) -> None:
        """Signal handler for rejection."""
        self.rejected = True
        self.rejection_reason = reason

    @workflow.query
    def get_status(self) -> dict[str, Any]:
        """Query handler for workflow status."""
        return {
            "current_step": self.current_step,
            "approved": self.approved,
            "rejected": self.rejected,
            "rejection_reason": self.rejection_reason,
        }

    @workflow.run
    async def run(
        self,
        tenant_id: str,
        run_id: str,
        config: dict[str, Any],
        resume_from: str | None = None,
    ) -> dict[str, Any]:
        """Execute the article generation workflow.

        Args:
            tenant_id: Tenant identifier for isolation
            run_id: Unique run identifier
            config: Configuration including pack_id, model settings, etc.
            resume_from: Optional step to resume from (for failed run recovery)

        Returns:
            dict with status and result details

        Raises:
            WorkflowFailedError: If workflow cannot complete
        """
        # Validate pack_id is provided (no auto-execution)
        pack_id = config.get("pack_id")
        if not pack_id:
            return {
                "status": "failed",
                "error": "pack_id required. Auto-execution without pack_id is forbidden.",
            }

        # Build activity args (passed to all activities)
        activity_args = {
            "tenant_id": tenant_id,
            "run_id": run_id,
            "config": config,
        }

        # ========== PRE-APPROVAL PHASE ==========
        self.current_step = "pre_approval"

        # Step 0: Keyword Selection
        if self._should_run("step0", resume_from):
            self.current_step = "step0"
            await self._execute_activity(
                "step0_keyword_selection",
                activity_args,
                "step0",
            )

        # Step 1: Competitor Article Fetch
        if self._should_run("step1", resume_from):
            self.current_step = "step1"
            await self._execute_activity(
                "step1_competitor_fetch",
                activity_args,
                "step1",
            )

        # Step 2: CSV Validation
        if self._should_run("step2", resume_from):
            self.current_step = "step2"
            await self._execute_activity(
                "step2_csv_validation",
                activity_args,
                "step2",
            )

        # Step 3: Parallel Analysis (3A/3B/3C)
        if self._should_run("step3", resume_from):
            self.current_step = "step3_parallel"
            await run_parallel_steps(tenant_id, run_id, config)

        # ========== APPROVAL WAIT ==========
        self.current_step = "waiting_approval"

        # Wait for approval or rejection signal
        await workflow.wait_condition(
            lambda: self.approved or self.rejected
        )

        if self.rejected:
            return {
                "status": "rejected",
                "reason": self.rejection_reason,
                "step": "waiting_approval",
            }

        # ========== POST-APPROVAL PHASE ==========
        self.current_step = "post_approval"

        # Step 4: Strategic Outline
        if self._should_run("step4", resume_from):
            self.current_step = "step4"
            await self._execute_activity(
                "step4_strategic_outline",
                activity_args,
                "step4",
            )

        # Step 5: Primary Source Collection
        if self._should_run("step5", resume_from):
            self.current_step = "step5"
            await self._execute_activity(
                "step5_primary_collection",
                activity_args,
                "step5",
            )

        # Step 6: Enhanced Outline
        if self._should_run("step6", resume_from):
            self.current_step = "step6"
            await self._execute_activity(
                "step6_enhanced_outline",
                activity_args,
                "step6",
            )

        # Step 6.5: Integration Package
        if self._should_run("step6_5", resume_from):
            self.current_step = "step6_5"
            await self._execute_activity(
                "step6_5_integration_package",
                activity_args,
                "step6_5",
            )

        # Step 7A: Draft Generation
        if self._should_run("step7a", resume_from):
            self.current_step = "step7a"
            await self._execute_activity(
                "step7a_draft_generation",
                activity_args,
                "step7a",
            )

        # Step 7B: Brush Up
        if self._should_run("step7b", resume_from):
            self.current_step = "step7b"
            await self._execute_activity(
                "step7b_brush_up",
                activity_args,
                "step7b",
            )

        # Step 8: Fact Check
        if self._should_run("step8", resume_from):
            self.current_step = "step8"
            await self._execute_activity(
                "step8_fact_check",
                activity_args,
                "step8",
            )

        # Step 9: Final Rewrite
        if self._should_run("step9", resume_from):
            self.current_step = "step9"
            await self._execute_activity(
                "step9_final_rewrite",
                activity_args,
                "step9",
            )

        # Step 10: Final Output
        if self._should_run("step10", resume_from):
            self.current_step = "step10"
            await self._execute_activity(
                "step10_final_output",
                activity_args,
                "step10",
            )

        # ========== COMPLETED ==========
        self.current_step = "completed"
        return {
            "status": "completed",
            "run_id": run_id,
            "tenant_id": tenant_id,
        }

    def _should_run(self, step: str, resume_from: str | None) -> bool:
        """Determine if a step should run based on resume point.

        Args:
            step: Step identifier to check
            resume_from: Step to resume from (None = run all)

        Returns:
            True if the step should be executed
        """
        if resume_from is None:
            return True

        # Step order for comparison
        step_order = [
            "step0",
            "step1",
            "step2",
            "step3",  # Represents 3a/3b/3c as a group
            "step4",
            "step5",
            "step6",
            "step6_5",
            "step7a",
            "step7b",
            "step8",
            "step9",
            "step10",
        ]

        try:
            current_idx = step_order.index(step)
            resume_idx = step_order.index(resume_from)
            return current_idx >= resume_idx
        except ValueError:
            # Unknown step, run it
            return True

    async def _execute_activity(
        self,
        activity_name: str,
        args: dict[str, Any],
        step_id: str,
    ) -> dict[str, Any]:
        """Execute an activity with appropriate timeout and retry policy.

        Args:
            activity_name: Name of the activity to execute
            args: Arguments to pass to the activity
            step_id: Step identifier for timeout lookup

        Returns:
            Activity result
        """
        timeout = STEP_TIMEOUTS.get(step_id, 120)

        result = await workflow.execute_activity(
            activity_name,
            args,
            start_to_close_timeout=timedelta(seconds=timeout),
            retry_policy=DEFAULT_RETRY_POLICY,
        )
        return cast(dict[str, Any], result)
