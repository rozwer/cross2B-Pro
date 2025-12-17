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
        # IMPORTANT: Do NOT accumulate step data in config to avoid gRPC size limits
        # Each activity should load required data from storage via load_step_data()
        activity_args = {
            "tenant_id": tenant_id,
            "run_id": run_id,
            "config": config,
        }

        # ========== PRE-APPROVAL PHASE ==========
        self.current_step = "pre_approval"

        # Track artifact refs only (not full data)
        artifact_refs: dict[str, dict[str, Any]] = {}

        # Step 0: Keyword Selection
        if self._should_run("step0", resume_from):
            self.current_step = "step0"
            step0_result = await self._execute_activity(
                "step0_keyword_selection",
                activity_args,
                "step0",
            )
            artifact_refs["step0"] = step0_result.get("artifact_ref", {})

        # Step 1: Competitor Article Fetch
        if self._should_run("step1", resume_from):
            self.current_step = "step1"
            step1_result = await self._execute_activity(
                "step1_competitor_fetch",
                activity_args,
                "step1",
            )
            artifact_refs["step1"] = step1_result.get("artifact_ref", {})

        # Step 2: CSV Validation
        if self._should_run("step2", resume_from):
            self.current_step = "step2"
            step2_result = await self._execute_activity(
                "step2_csv_validation",
                activity_args,
                "step2",
            )
            artifact_refs["step2"] = step2_result.get("artifact_ref", {})

        # Step 3: Parallel Analysis (3A/3B/3C)
        if self._should_run("step3", resume_from):
            self.current_step = "step3_parallel"
            step3_results = await run_parallel_steps(tenant_id, run_id, config)
            # Store artifact refs only
            for step_key in ["step3a", "step3b", "step3c"]:
                if step_key in step3_results:
                    artifact_refs[step_key] = step3_results[step_key].get("artifact_ref", {})

        # ========== APPROVAL WAIT ==========
        # Skip approval wait if resuming from post-approval step
        post_approval_steps = ["step4", "step5", "step6", "step6_5", "step7a", "step7b", "step8", "step9", "step10"]
        skip_approval = resume_from is not None and resume_from in post_approval_steps

        if not skip_approval:
            self.current_step = "waiting_approval"

            # Wait for approval or rejection signal
            await workflow.wait_condition(
                lambda: self.approved or self.rejected
            )

            if self.rejected:
                # Sync rejected status to API DB
                await self._sync_run_status(
                    tenant_id,
                    run_id,
                    "failed",
                    "waiting_approval",
                    error_code="REJECTED",
                    error_message=self.rejection_reason or "Rejected by reviewer",
                )
                return {
                    "status": "rejected",
                    "reason": self.rejection_reason,
                    "step": "waiting_approval",
                }
        else:
            # When resuming from post-approval, mark as approved
            self.approved = True

        # ========== POST-APPROVAL PHASE ==========
        self.current_step = "post_approval"

        # Step 4: Strategic Outline
        if self._should_run("step4", resume_from):
            self.current_step = "step4"
            step4_result = await self._execute_activity(
                "step4_strategic_outline",
                activity_args,
                "step4",
            )
            artifact_refs["step4"] = step4_result.get("artifact_ref", {})

        # Step 5: Primary Source Collection
        if self._should_run("step5", resume_from):
            self.current_step = "step5"
            step5_result = await self._execute_activity(
                "step5_primary_collection",
                activity_args,
                "step5",
            )
            artifact_refs["step5"] = step5_result.get("artifact_ref", {})

        # Step 6: Enhanced Outline
        if self._should_run("step6", resume_from):
            self.current_step = "step6"
            step6_result = await self._execute_activity(
                "step6_enhanced_outline",
                activity_args,
                "step6",
            )
            artifact_refs["step6"] = step6_result.get("artifact_ref", {})

        # Step 6.5: Integration Package
        if self._should_run("step6_5", resume_from):
            self.current_step = "step6_5"
            step6_5_result = await self._execute_activity(
                "step6_5_integration_package",
                activity_args,
                "step6_5",
            )
            artifact_refs["step6_5"] = step6_5_result.get("artifact_ref", {})

        # Step 7A: Draft Generation
        if self._should_run("step7a", resume_from):
            self.current_step = "step7a"
            step7a_result = await self._execute_activity(
                "step7a_draft_generation",
                activity_args,
                "step7a",
            )
            artifact_refs["step7a"] = step7a_result.get("artifact_ref", {})

        # Step 7B: Brush Up
        if self._should_run("step7b", resume_from):
            self.current_step = "step7b"
            step7b_result = await self._execute_activity(
                "step7b_brush_up",
                activity_args,
                "step7b",
            )
            artifact_refs["step7b"] = step7b_result.get("artifact_ref", {})

        # Step 8: Fact Check
        if self._should_run("step8", resume_from):
            self.current_step = "step8"
            step8_result = await self._execute_activity(
                "step8_fact_check",
                activity_args,
                "step8",
            )
            artifact_refs["step8"] = step8_result.get("artifact_ref", {})

        # Step 9: Final Rewrite
        if self._should_run("step9", resume_from):
            self.current_step = "step9"
            step9_result = await self._execute_activity(
                "step9_final_rewrite",
                activity_args,
                "step9",
            )
            artifact_refs["step9"] = step9_result.get("artifact_ref", {})

        # Step 10: Final Output
        if self._should_run("step10", resume_from):
            self.current_step = "step10"
            step10_result = await self._execute_activity(
                "step10_final_output",
                activity_args,
                "step10",
            )
            artifact_refs["step10"] = step10_result.get("artifact_ref", {})

        # ========== COMPLETED ==========
        self.current_step = "completed"

        # Sync final status to API DB
        await self._sync_run_status(tenant_id, run_id, "completed", "completed")

        return {
            "status": "completed",
            "run_id": run_id,
            "tenant_id": tenant_id,
            "artifact_refs": artifact_refs,
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

    async def _sync_run_status(
        self,
        tenant_id: str,
        run_id: str,
        status: str,
        current_step: str,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Sync workflow status to API database.

        This is called at terminal states (completed, rejected) to ensure
        the API database reflects the final workflow state.

        Args:
            tenant_id: Tenant identifier
            run_id: Run identifier
            status: Final status (completed, failed)
            current_step: Final step reached
            error_code: Optional error code if failed
            error_message: Optional error message if failed
        """
        sync_args = {
            "tenant_id": tenant_id,
            "run_id": run_id,
            "status": status,
            "current_step": current_step,
        }
        if error_code:
            sync_args["error_code"] = error_code
        if error_message:
            sync_args["error_message"] = error_message

        # Use a short timeout - status sync is best-effort
        await workflow.execute_activity(
            "sync_run_status",
            sync_args,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )
