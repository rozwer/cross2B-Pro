"""Main Temporal Workflow for SEO article generation.

ArticleWorkflow orchestrates the entire article generation process:
- Pre-approval phase: step0 → step1 → step1_5 → step2 → step3 (parallel)
- Approval wait: Pauses for human approval via Temporal signal
- Post-approval phase: step3_5 → step4 → ... → step12

IMPORTANT:
- No fallback to different models/tools
- All artifacts stored via ArtifactStore (path/digest only in workflow)
- All state changes emit events for observability
"""

from datetime import timedelta
from typing import Any, cast

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

from .parallel import run_parallel_steps

# Activity timeouts as defined in workflow.md
STEP_TIMEOUTS: dict[str, int] = {
    "step0": 60,
    "step1": 300,
    "step1_5": 300,
    "step2": 60,
    "step3a": 120,
    "step3b": 120,
    "step3c": 120,
    "step3_5": 180,
    "step4": 180,
    "step5": 300,
    "step6": 180,
    "step6_5": 180,
    "step7a": 600,
    "step7b": 300,
    "step8": 300,
    "step9": 300,
    "step10": 120,
    "step11": 600,  # 画像生成は時間がかかる
    "step12": 300,
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
        self.config: dict[str, Any] = {}
        # Step11 (image generation) state - Legacy (backward compatibility)
        self.image_gen_decision_made: bool = False
        self.image_gen_enabled: bool = False
        self.image_gen_config: dict[str, Any] | None = None
        # Step11 Multi-phase state (new)
        self.step11_phase: str = "idle"  # idle, 11A, 11B, 11C, 11D, 11E, skipped, completed
        self.step11_settings: dict[str, Any] | None = None
        self.step11_positions: list[dict[str, Any]] | None = None
        self.step11_positions_confirmed: dict[str, Any] | None = None
        self.step11_instructions: list[dict[str, Any]] | None = None
        self.step11_generated_images: list[dict[str, Any]] | None = None
        self.step11_image_reviews: list[dict[str, Any]] | None = None
        self.step11_finalized: dict[str, Any] | None = None

    @workflow.signal
    async def approve(self) -> None:
        """Signal handler for approval."""
        self.approved = True

    @workflow.signal
    async def reject(self, reason: str) -> None:
        """Signal handler for rejection."""
        self.rejected = True
        self.rejection_reason = reason

    @workflow.signal
    async def start_image_generation(self, config: dict[str, Any]) -> None:
        """Signal handler to start image generation.

        Args:
            config: Image generation config with:
                - enabled: bool (True to generate, False to skip)
                - image_count: int (number of images to generate)
                - position_request: str (optional user request for positions)
        """
        self.image_gen_decision_made = True
        self.image_gen_enabled = config.get("enabled", True)
        self.image_gen_config = config
        # Also populate step11_settings for the multi-phase workflow
        # This ensures image_gen_config values are used in step11 execution
        if self.image_gen_enabled:
            self.step11_settings = {
                "image_count": config.get("image_count", 3),
                "position_request": config.get("position_request", ""),
            }

    @workflow.signal
    async def skip_image_generation(self) -> None:
        """Signal handler to skip image generation."""
        self.image_gen_decision_made = True
        self.image_gen_enabled = False
        self.image_gen_config = None

    # ========== Step11 Multi-phase Signals ==========

    @workflow.signal
    async def step11_start_settings(self, config: dict[str, Any]) -> None:
        """Phase 11A: User provides initial settings.

        Args:
            config: Settings with:
                - image_count: int (1-10)
                - position_request: str (optional user preference)
        """
        self.step11_phase = "11A"
        self.step11_settings = config
        # Also set legacy flags for compatibility
        self.image_gen_decision_made = True
        self.image_gen_enabled = True

    @workflow.signal
    async def step11_skip(self) -> None:
        """Skip image generation entirely."""
        self.step11_phase = "skipped"
        self.image_gen_decision_made = True
        self.image_gen_enabled = False

    @workflow.signal
    async def step11_confirm_positions(self, payload: dict[str, Any]) -> None:
        """Phase 11B: User confirms or modifies positions.

        Args:
            payload:
                - approved: bool
                - modified_positions: list[dict] | None (if user edited)
                - reanalyze: bool (request re-analysis)
                - reanalyze_request: str (additional instructions)
        """
        self.step11_positions_confirmed = payload

    @workflow.signal
    async def step11_submit_instructions(self, payload: dict[str, Any]) -> None:
        """Phase 11C: User submits per-image instructions.

        Args:
            payload:
                - instructions: list[{index: int, instruction: str}]
        """
        self.step11_instructions = payload.get("instructions", [])

    @workflow.signal
    async def step11_review_images(self, payload: dict[str, Any]) -> None:
        """Phase 11D: User reviews generated images.

        Args:
            payload:
                - reviews: list[{
                    index: int,
                    accepted: bool,
                    retry: bool,
                    retry_instruction: str
                }]
        """
        self.step11_image_reviews = payload.get("reviews", [])

    @workflow.signal
    async def step11_finalize(self, payload: dict[str, Any]) -> None:
        """Phase 11E: User confirms final preview.

        Args:
            payload:
                - confirmed: bool
                - restart_from: str | None (e.g., "11C" to go back)
        """
        self.step11_finalized = payload

    @workflow.query
    def get_status(self) -> dict[str, Any]:
        """Query handler for workflow status."""
        return {
            "current_step": self.current_step,
            "approved": self.approved,
            "rejected": self.rejected,
            "rejection_reason": self.rejection_reason,
            "image_gen_decision_made": self.image_gen_decision_made,
            "image_gen_enabled": self.image_gen_enabled,
            # Step11 multi-phase state
            "step11_phase": self.step11_phase,
            "step11_settings": self.step11_settings,
            "step11_positions_count": len(self.step11_positions or []),
            "step11_images_count": len(self.step11_generated_images or []),
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
        # Raising ApplicationError ensures Temporal marks the workflow as failed,
        # which triggers proper status updates in the API
        pack_id = config.get("pack_id")
        if not pack_id:
            raise ApplicationError(
                "pack_id required. Auto-execution without pack_id is forbidden.",
                type="VALIDATION_ERROR",
                non_retryable=True,
            )

        self.config = config

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

        # Step 1.5: Related Keyword Competitor Extraction (optional)
        if self._should_run("step1_5", resume_from):
            self.current_step = "step1_5"
            step1_5_result = await self._execute_activity(
                "step1_5_related_keyword_extraction",
                activity_args,
                "step1_5",
            )
            artifact_refs["step1_5"] = step1_5_result.get("artifact_ref", {})

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
        post_approval_steps = [
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
        skip_approval = resume_from is not None and resume_from in post_approval_steps

        if not skip_approval:
            self.current_step = "waiting_approval"

            # Wait for approval or rejection signal
            await workflow.wait_condition(lambda: self.approved or self.rejected)

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

        # Step 3.5: Human Touch Generation (first post-approval step)
        if self._should_run("step3_5", resume_from):
            self.current_step = "step3_5"
            step3_5_result = await self._execute_activity(
                "step3_5_human_touch_generation",
                activity_args,
                "step3_5",
            )
            artifact_refs["step3_5"] = step3_5_result.get("artifact_ref", {})

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

        # ========== STEP 11: MULTI-PHASE IMAGE GENERATION ==========
        if self._should_run("step11", resume_from):
            step11_result = await self._run_step11_multiphase(tenant_id, run_id, config, activity_args, resume_from)
            artifact_refs["step11"] = step11_result.get("artifact_ref", {})

        # Step 12: WordPress HTML Generation
        if self._should_run("step12", resume_from):
            self.current_step = "step12"
            step12_result = await self._execute_activity(
                "step12_wordpress_html_generation",
                activity_args,
                "step12",
            )
            artifact_refs["step12"] = step12_result.get("artifact_ref", {})

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
            return self._step_enabled(step)

        # Step order for comparison (granular, including 3a/3b/3c)
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
            "step11",
            "step12",
        ]

        # Normalize step3 to step3a for comparison (step3 group starts at 3a)
        normalized_step = step if step != "step3" else "step3a"
        normalized_resume = resume_from if resume_from != "step3" else "step3a"

        try:
            current_idx = step_order.index(normalized_step)
            resume_idx = step_order.index(normalized_resume)
            return current_idx >= resume_idx and self._step_enabled(step)
        except ValueError:
            # Unknown step, run it
            return self._step_enabled(step)

    def _step_enabled(self, step: str) -> bool:
        """Check feature flags for optional steps."""
        config = self.config or {}
        if step == "step1_5":
            return config.get("enable_step1_5", True)
        if step == "step3_5":
            return config.get("enable_step3_5", True)
        if step == "step12":
            return config.get("enable_step12", True)
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

    async def _run_step11_multiphase(
        self,
        tenant_id: str,
        run_id: str,
        config: dict[str, Any],
        activity_args: dict[str, Any],
        resume_from: str | None,
    ) -> dict[str, Any]:
        """Execute Step11 with multi-phase interactive workflow.

        Phases:
            11A: Initial settings (image count, position request)
            11B: Position review (approve/edit/reanalyze)
            11C: Image instructions (per-image user instructions)
            11D: Image review (accept/retry per image)
            11E: Final preview (confirm or restart from 11C)

        Args:
            tenant_id: Tenant identifier
            run_id: Run identifier
            config: Workflow configuration
            activity_args: Base activity arguments
            resume_from: Optional step to resume from

        Returns:
            Step11 result with artifact_ref
        """
        self.current_step = "step11"
        max_retries_per_image = 3

        # Skip waiting phases if resuming from step11
        skip_initial_wait = resume_from == "step11"

        # ========== Phase 11A: Wait for initial settings or skip ==========
        if not skip_initial_wait:
            self.step11_phase = "waiting_11A"
            self.current_step = "waiting_image_generation"
            # Use waiting_image_input (not waiting_approval) for Step11 waiting state
            await self._sync_run_status(tenant_id, run_id, "waiting_image_input", "waiting_image_generation")

            # Wait for settings signal or skip signal
            await workflow.wait_condition(lambda: self.step11_phase in ("11A", "skipped") or self.image_gen_decision_made)

            # Handle legacy skip signal
            if self.image_gen_decision_made and not self.image_gen_enabled:
                self.step11_phase = "skipped"

        # Handle skip
        if self.step11_phase == "skipped":
            self.current_step = "step11"
            skip_args = {
                **activity_args,
                "config": {**config, "step11_enabled": False},
            }
            return await self._execute_activity(
                "step11_mark_skipped",
                skip_args,
                "step11",
            )

        # ========== Phase 11B: Analyze positions and wait for confirmation ==========
        self.step11_phase = "11B_analyzing"
        self.current_step = "step11_analyzing"
        await self._sync_run_status(tenant_id, run_id, "running", "step11_analyzing")

        # Execute position analysis activity
        analyze_args = {
            **activity_args,
            "config": {
                **config,
                "step11_enabled": True,
                "step11_image_count": (self.step11_settings or {}).get("image_count", 3),
                "step11_position_request": (self.step11_settings or {}).get("position_request", ""),
            },
        }
        position_result = await self._execute_activity(
            "step11_analyze_positions",
            analyze_args,
            "step11",
        )
        self.step11_positions = position_result.get("positions", [])

        # Wait for position confirmation with reanalyze loop
        while True:
            self.step11_phase = "waiting_11B"
            self.current_step = "step11_position_review"
            self.step11_positions_confirmed = None
            await self._sync_run_status(tenant_id, run_id, "waiting_image_input", "step11_position_review")

            await workflow.wait_condition(lambda: self.step11_positions_confirmed is not None)

            # Check if reanalyze requested
            if self.step11_positions_confirmed.get("reanalyze"):
                self.step11_phase = "11B_reanalyzing"
                self.current_step = "step11_analyzing"
                await self._sync_run_status(tenant_id, run_id, "running", "step11_analyzing")

                # Reanalyze with additional request
                reanalyze_args = {
                    **activity_args,
                    "config": {
                        **config,
                        "step11_enabled": True,
                        "step11_image_count": (self.step11_settings or {}).get("image_count", 3),
                        "step11_position_request": (
                            (self.step11_settings or {}).get("position_request", "")
                            + "\n"
                            + self.step11_positions_confirmed.get("reanalyze_request", "")
                        ),
                    },
                }
                position_result = await self._execute_activity(
                    "step11_analyze_positions",
                    reanalyze_args,
                    "step11",
                )
                self.step11_positions = position_result.get("positions", [])
                continue  # Loop back to wait for confirmation

            # Apply modified positions if provided
            if self.step11_positions_confirmed.get("modified_positions"):
                self.step11_positions = self.step11_positions_confirmed["modified_positions"]

            break  # Positions confirmed, proceed to next phase

        # ========== Phase 11C: Wait for per-image instructions ==========
        # This is where we can restart from 11E
        phase_11c_start = True
        while phase_11c_start:
            phase_11c_start = False  # Only loop if restart_from == "11C"

            self.step11_phase = "waiting_11C"
            self.current_step = "step11_image_instructions"
            self.step11_instructions = None
            await self._sync_run_status(tenant_id, run_id, "waiting_image_input", "step11_image_instructions")

            await workflow.wait_condition(lambda: self.step11_instructions is not None)

            # ========== Phase 11D: Generate images and wait for review ==========
            self.step11_phase = "11D_generating"
            self.current_step = "step11_generating"
            await self._sync_run_status(tenant_id, run_id, "running", "step11_generating")

            # Execute image generation activity
            generate_args = {
                **activity_args,
                "config": {
                    **config,
                    "step11_enabled": True,
                },
                "positions": self.step11_positions,
                "instructions": self.step11_instructions,
            }
            generation_result = await self._execute_activity(
                "step11_generate_images",
                generate_args,
                "step11",
            )
            self.step11_generated_images = generation_result.get("images", [])

            # Initialize retry counts
            retry_counts = [0] * len(self.step11_generated_images)

            # Wait for image review with retry loop
            while True:
                self.step11_phase = "waiting_11D"
                self.current_step = "step11_image_review"
                self.step11_image_reviews = None
                await self._sync_run_status(tenant_id, run_id, "waiting_image_input", "step11_image_review")

                await workflow.wait_condition(lambda: self.step11_image_reviews is not None)

                # Process retries with index bounds validation
                num_positions = len(self.step11_positions)
                num_images = len(self.step11_generated_images)
                retries_needed = [
                    r
                    for r in self.step11_image_reviews
                    if r.get("retry")
                    and 0 <= r.get("index", -1) < num_positions
                    and r.get("index", -1) < len(retry_counts)
                    and retry_counts[r["index"]] < max_retries_per_image
                ]

                if not retries_needed:
                    break  # All images accepted or max retries reached

                self.step11_phase = "11D_retrying"
                self.current_step = "step11_generating"
                await self._sync_run_status(tenant_id, run_id, "running", "step11_generating")

                for retry_req in retries_needed:
                    idx = retry_req["index"]
                    # Double-check bounds before accessing arrays
                    if idx < 0 or idx >= num_positions:
                        workflow.logger.warning(f"Step11 retry: index {idx} out of bounds (positions: {num_positions})")
                        continue
                    if idx >= num_images:
                        workflow.logger.warning(f"Step11 retry: index {idx} out of bounds (images: {num_images})")
                        continue

                    retry_counts[idx] += 1

                    retry_args = {
                        **activity_args,
                        "config": {**config, "step11_enabled": True},
                        "image_index": idx,
                        "position": self.step11_positions[idx],
                        "instruction": retry_req.get("retry_instruction", ""),
                        "original_instruction": (
                            self.step11_instructions[idx].get("instruction", "") if idx < len(self.step11_instructions) else ""
                        ),
                    }
                    retry_result = await self._execute_activity(
                        "step11_retry_image",
                        retry_args,
                        "step11",
                    )
                    if retry_result.get("success"):
                        self.step11_generated_images[idx] = retry_result["image"]
                        self.step11_generated_images[idx]["retry_count"] = retry_counts[idx]

            # ========== Phase 11E: Insert images and show preview ==========
            self.step11_phase = "11E_inserting"
            self.current_step = "step11_inserting"
            await self._sync_run_status(tenant_id, run_id, "running", "step11_inserting")

            insert_args = {
                **activity_args,
                "config": {**config, "step11_enabled": True},
                "images": self.step11_generated_images,
                "positions": self.step11_positions,
            }
            insert_result = await self._execute_activity(
                "step11_insert_images",
                insert_args,
                "step11",
            )

            # Wait for final confirmation
            self.step11_phase = "waiting_11E"
            self.current_step = "step11_preview"
            self.step11_finalized = None
            await self._sync_run_status(tenant_id, run_id, "waiting_image_input", "step11_preview")

            await workflow.wait_condition(lambda: self.step11_finalized is not None)

            # Check if restart requested
            if self.step11_finalized.get("restart_from") == "11C":
                phase_11c_start = True
                continue  # Loop back to phase 11C

        # ========== Completed ==========
        self.step11_phase = "completed"
        return insert_result


@workflow.defn
class ImageAdditionWorkflow:
    """Temporal Workflow for adding images to completed runs.

    This workflow is used when a run has already completed but the user
    wants to add images afterward. It runs the same Step11 multi-phase
    logic as ArticleWorkflow but as an independent workflow.

    Signals:
        step11_confirm_positions(payload): Confirm or modify image positions
        step11_submit_instructions(payload): Submit per-image instructions
        step11_review_images(payload): Review generated images
        step11_finalize(payload): Confirm final preview
        skip(): Skip image generation
    """

    def __init__(self) -> None:
        """Initialize workflow state."""
        # Step11 multi-phase state
        self.step11_phase: str = "idle"
        self.step11_settings: dict[str, Any] | None = None
        self.step11_positions: list[dict[str, Any]] | None = None
        self.step11_positions_confirmed: dict[str, Any] | None = None
        self.step11_instructions: list[dict[str, Any]] | None = None
        self.step11_generated_images: list[dict[str, Any]] | None = None
        self.step11_image_reviews: list[dict[str, Any]] | None = None
        self.step11_finalized: dict[str, Any] | None = None
        self.skipped: bool = False
        self.current_step: str = "step11"

    # ========== Signals ==========

    @workflow.signal
    async def step11_confirm_positions(self, payload: dict[str, Any]) -> None:
        """Phase 11B: User confirms or modifies positions."""
        self.step11_positions_confirmed = payload

    @workflow.signal
    async def step11_submit_instructions(self, payload: dict[str, Any]) -> None:
        """Phase 11C: User submits per-image instructions."""
        self.step11_instructions = payload.get("instructions", [])

    @workflow.signal
    async def step11_review_images(self, payload: dict[str, Any]) -> None:
        """Phase 11D: User reviews generated images."""
        self.step11_image_reviews = payload.get("reviews", [])

    @workflow.signal
    async def step11_finalize(self, payload: dict[str, Any]) -> None:
        """Phase 11E: User confirms final preview."""
        self.step11_finalized = payload

    @workflow.signal
    async def skip(self) -> None:
        """Skip image generation."""
        self.skipped = True
        self.step11_phase = "skipped"

    @workflow.query
    def get_status(self) -> dict[str, Any]:
        """Query handler for workflow status."""
        return {
            "step11_phase": self.step11_phase,
            "step11_settings": self.step11_settings,
            "step11_positions_count": len(self.step11_positions or []),
            "step11_images_count": len(self.step11_generated_images or []),
            "current_step": self.current_step,
            "skipped": self.skipped,
        }

    @workflow.run
    async def run(
        self,
        tenant_id: str,
        run_id: str,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute image addition workflow.

        Args:
            tenant_id: Tenant identifier
            run_id: Run identifier
            config: Configuration with:
                - image_count: Number of images to generate
                - position_request: User preference for positions
                - article_markdown: The article content (from step10 output)

        Returns:
            Result dictionary with artifact_ref
        """
        self.step11_settings = {
            "image_count": config.get("image_count", 3),
            "position_request": config.get("position_request", ""),
        }

        # Helper for executing activities
        with workflow.unsafe.imports_passed_through():
            from apps.worker.activities import (
                step11_analyze_positions,
                step11_generate_images,
                step11_insert_images,
                step11_retry_image,
                sync_run_status,
            )

        async def execute_activity(
            activity_name: str,
            activity_input: dict[str, Any],
            step_name: str = "step11",
        ) -> dict[str, Any]:
            """Execute an activity with standard settings."""
            activities = {
                "step11_analyze_positions": step11_analyze_positions,
                "step11_generate_images": step11_generate_images,
                "step11_retry_image": step11_retry_image,
                "step11_insert_images": step11_insert_images,
                "sync_run_status": sync_run_status,
            }
            activity = activities.get(activity_name)
            if not activity:
                raise ValueError(f"Unknown activity: {activity_name}")

            timeout = STEP_TIMEOUTS.get(step_name, 300)
            return cast(
                dict[str, Any],
                await workflow.execute_activity(
                    activity,
                    activity_input,
                    start_to_close_timeout=timedelta(seconds=timeout),
                    retry_policy=DEFAULT_RETRY_POLICY,
                ),
            )

        async def update_status(status: str, current_step: str) -> None:
            """Update run status in database."""
            await execute_activity(
                "sync_run_status",
                {
                    "tenant_id": tenant_id,
                    "run_id": run_id,
                    "status": status,
                    "current_step": current_step,
                },
                "step11",
            )

        # ========== Phase 11B: Position Analysis ==========
        self.step11_phase = "11B_analyzing"
        self.current_step = "step11_analyzing"
        await update_status("running", "step11_analyzing")

        position_result = await execute_activity(
            "step11_analyze_positions",
            {
                "tenant_id": tenant_id,
                "run_id": run_id,
                "config": {
                    **config,
                    "step11_enabled": True,
                    "step11_image_count": self.step11_settings.get("image_count", 3),
                    "step11_position_request": self.step11_settings.get("position_request", ""),
                },
            },
        )
        self.step11_positions = position_result.get("positions", [])

        # Wait for position confirmation loop
        while True:
            self.step11_phase = "waiting_11B"
            self.current_step = "step11_position_review"
            self.step11_positions_confirmed = None
            await update_status("waiting_image_input", "step11_position_review")

            await workflow.wait_condition(lambda: self.step11_positions_confirmed is not None or self.skipped)

            if self.skipped:
                await update_status("completed", "step11")
                return {"artifact_ref": {}, "skipped": True}

            if self.step11_positions_confirmed.get("reanalyze"):
                self.step11_phase = "11B_reanalyzing"
                self.current_step = "step11_analyzing"
                await update_status("running", "step11_analyzing")

                position_result = await execute_activity(
                    "step11_analyze_positions",
                    {
                        "tenant_id": tenant_id,
                        "run_id": run_id,
                        "config": {
                            **config,
                            "step11_enabled": True,
                            "step11_image_count": self.step11_settings.get("image_count", 3),
                            "step11_position_request": (
                                self.step11_settings.get("position_request", "")
                                + " "
                                + self.step11_positions_confirmed.get("reanalyze_request", "")
                            ),
                        },
                    },
                )
                self.step11_positions = position_result.get("positions", [])
                continue

            if self.step11_positions_confirmed.get("modified_positions"):
                self.step11_positions = self.step11_positions_confirmed["modified_positions"]

            break

        # ========== Phase 11C-11E: Main loop ==========
        phase_11c_start = True
        insert_result: dict[str, Any] = {}

        while True:
            # ===== Phase 11C: Image Instructions =====
            if phase_11c_start:
                phase_11c_start = False
                self.step11_phase = "waiting_11C"
                self.current_step = "step11_image_instructions"
                self.step11_instructions = None
                await update_status("waiting_image_input", "step11_image_instructions")

                await workflow.wait_condition(lambda: self.step11_instructions is not None or self.skipped)

                if self.skipped:
                    await update_status("completed", "step11")
                    return {"artifact_ref": {}, "skipped": True}

            # ===== Phase 11D: Image Generation =====
            self.step11_phase = "11D_generating"
            self.current_step = "step11_generating"
            await update_status("running", "step11_generating")

            generation_result = await execute_activity(
                "step11_generate_images",
                {
                    "tenant_id": tenant_id,
                    "run_id": run_id,
                    "config": {**config, "step11_enabled": True},
                    "positions": self.step11_positions,
                    "instructions": self.step11_instructions,
                },
            )
            self.step11_generated_images = generation_result.get("images", [])

            # Image review loop
            retry_counts = [0] * len(self.step11_generated_images)
            max_retries = 3

            while True:
                self.step11_phase = "waiting_11D"
                self.current_step = "step11_image_review"
                self.step11_image_reviews = None
                await update_status("waiting_image_input", "step11_image_review")

                await workflow.wait_condition(lambda: self.step11_image_reviews is not None or self.skipped)

                if self.skipped:
                    await update_status("completed", "step11")
                    return {"artifact_ref": {}, "skipped": True}

                # Validate index bounds before processing retries
                num_positions = len(self.step11_positions)
                num_images = len(self.step11_generated_images)
                retries_requested = [
                    r
                    for r in self.step11_image_reviews
                    if r.get("retry")
                    and 0 <= r.get("index", -1) < num_positions
                    and r.get("index", -1) < len(retry_counts)
                    and retry_counts[r["index"]] < max_retries
                ]

                if not retries_requested:
                    break

                self.step11_phase = "11D_retrying"
                self.current_step = "step11_generating"
                await update_status("running", "step11_generating")

                for r in retries_requested:
                    idx = r["index"]
                    # Double-check bounds before accessing arrays
                    if idx < 0 or idx >= num_positions:
                        workflow.logger.warning(f"Step11 retry: index {idx} out of bounds (positions: {num_positions})")
                        continue
                    if idx >= num_images:
                        workflow.logger.warning(f"Step11 retry: index {idx} out of bounds (images: {num_images})")
                        continue

                    retry_counts[idx] += 1
                    retry_result = await execute_activity(
                        "step11_retry_image",
                        {
                            "tenant_id": tenant_id,
                            "run_id": run_id,
                            "config": {**config, "step11_enabled": True},
                            "position": self.step11_positions[idx],
                            "instruction": (
                                self.step11_instructions[idx].get("instruction", "") if idx < len(self.step11_instructions) else ""
                            ),
                            "retry_instruction": r.get("retry_instruction", ""),
                        },
                    )
                    self.step11_generated_images[idx] = retry_result["image"]
                    self.step11_generated_images[idx]["retry_count"] = retry_counts[idx]

            # ===== Phase 11E: Insert Images =====
            self.step11_phase = "11E_inserting"
            self.current_step = "step11_inserting"
            await update_status("running", "step11_inserting")

            insert_result = await execute_activity(
                "step11_insert_images",
                {
                    "tenant_id": tenant_id,
                    "run_id": run_id,
                    "config": {**config, "step11_enabled": True},
                    "images": self.step11_generated_images,
                    "positions": self.step11_positions,
                },
            )

            # Preview confirmation
            self.step11_phase = "waiting_11E"
            self.current_step = "step11_preview"
            self.step11_finalized = None
            await update_status("waiting_image_input", "step11_preview")

            await workflow.wait_condition(lambda: self.step11_finalized is not None or self.skipped)

            if self.skipped:
                await update_status("completed", "step11")
                return {"artifact_ref": {}, "skipped": True}

            if self.step11_finalized.get("restart_from") == "11C":
                phase_11c_start = True
                continue

            break

        # ========== Completed ==========
        self.step11_phase = "completed"
        await update_status("completed", "step11")
        return insert_result
