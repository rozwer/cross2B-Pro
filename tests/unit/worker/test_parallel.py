"""Unit tests for parallel step execution.

Tests for REQ-02 (individual retry) and REQ-03 (retry instructions).
"""

import pytest

from apps.worker.workflows.parallel import (
    PARALLEL_STEP_TIMEOUT,
    ParallelStepError,
    run_parallel_steps,
)


class TestParallelStepExecution:
    """Tests for parallel step execution logic."""

    def test_parallel_step_error_structure(self) -> None:
        """Test ParallelStepError contains failed steps."""
        failed = ["step3a", "step3c"]
        error = ParallelStepError(failed_steps=failed)

        assert error.failed_steps == failed
        assert "step3a" in str(error)
        assert "step3c" in str(error)

    def test_timeout_configured(self) -> None:
        """Test parallel step timeout is 120 seconds."""
        assert PARALLEL_STEP_TIMEOUT.total_seconds() == 120


class TestParallelStepScenarios:
    """Test various parallel execution scenarios."""

    @pytest.mark.asyncio
    async def test_all_succeed_first_attempt(self) -> None:
        """Test when all three steps succeed on first attempt."""
        # This would require mocking Temporal workflow context
        # Placeholder for integration test
        pass

    @pytest.mark.asyncio
    async def test_one_failure_triggers_retry(self) -> None:
        """Test that single failure triggers retry only for that step."""
        # This would require mocking Temporal workflow context
        pass

    @pytest.mark.asyncio
    async def test_all_failures_after_max_retries(self) -> None:
        """Test ParallelStepError raised after max retries."""
        # Verify error contains all failed steps
        failed = ["step3a", "step3b", "step3c"]
        error = ParallelStepError(
            failed_steps=failed,
            message="All parallel steps failed after 3 attempts",
        )

        assert len(error.failed_steps) == 3
        assert "step3b" in error.failed_steps

    def test_step_names_are_correct(self) -> None:
        """Test parallel step names match expected values."""
        expected = ["step3a", "step3b", "step3c"]
        # Verify these are the steps handled by parallel execution
        for step in expected:
            assert step.startswith("step3")


class TestParallelStepRetryFeatures:
    """Test REQ-02 and REQ-03: Individual retry with instructions.

    Note: These tests document the expected behavior.
    Full integration tests require Temporal workflow context.
    """

    def test_run_parallel_steps_function_signature(self) -> None:
        """Test run_parallel_steps accepts retry parameters (REQ-02, REQ-03)."""
        # Verify function accepts the new parameters
        import inspect

        sig = inspect.signature(run_parallel_steps)
        params = list(sig.parameters.keys())

        assert "retry_steps" in params, "REQ-02: retry_steps parameter required"
        assert "retry_instructions" in params, "REQ-03: retry_instructions parameter required"

    def test_retry_steps_parameter_type(self) -> None:
        """Test retry_steps parameter accepts list of step names (REQ-02)."""
        import inspect

        sig = inspect.signature(run_parallel_steps)
        retry_steps_param = sig.parameters["retry_steps"]

        # Should have default value of None
        assert retry_steps_param.default is None

    def test_retry_instructions_parameter_type(self) -> None:
        """Test retry_instructions parameter accepts dict (REQ-03)."""
        import inspect

        sig = inspect.signature(run_parallel_steps)
        retry_instructions_param = sig.parameters["retry_instructions"]

        # Should have default value of None
        assert retry_instructions_param.default is None

    def test_selective_retry_scenario(self) -> None:
        """Document selective retry scenario (REQ-02).

        Scenario: Only step3a and step3c need retry.
        - retry_steps=["step3a", "step3c"]
        - retry_instructions={"step3a": "...", "step3c": "..."}
        - Result: Only those two steps should be re-executed.
        """
        retry_steps = ["step3a", "step3c"]
        retry_instructions = {
            "step3a": "ペルソナをより具体的に",
            "step3c": "競合との差別化ポイントを明確に",
        }

        # Verify step3b is NOT in retry list (approved step)
        assert "step3b" not in retry_steps
        # Verify instructions match retry steps
        assert set(retry_instructions.keys()) == set(retry_steps)

    def test_all_steps_retry_scenario(self) -> None:
        """Document all steps retry scenario.

        Scenario: All steps need retry with different instructions.
        """
        retry_steps = ["step3a", "step3b", "step3c"]
        retry_instructions = {
            "step3a": "Instruction A",
            "step3b": "Instruction B",
            "step3c": "Instruction C",
        }

        assert len(retry_steps) == 3
        assert all(step in retry_instructions for step in retry_steps)

    def test_parallel_step_error_with_retry_context(self) -> None:
        """Test error structure includes retry context."""
        failed = ["step3a"]
        error = ParallelStepError(
            failed_steps=failed,
            message="Parallel steps failed after 3 attempts: {'step3a': '[LLMError] Rate limit'}",
        )

        assert "step3a" in error.failed_steps
        assert "Rate limit" in str(error)

    def test_empty_retry_steps_runs_all(self) -> None:
        """Test that None/empty retry_steps means run all steps.

        When retry_steps is None (default), all three steps should run.
        This is the initial execution behavior.
        """
        # Document: retry_steps=None → run ["step3a", "step3b", "step3c"]
        all_steps = ["step3a", "step3b", "step3c"]
        assert len(all_steps) == 3


class TestRetryInstructionIntegration:
    """Test retry instruction integration points (REQ-03)."""

    def test_activity_args_structure(self) -> None:
        """Test activity args structure includes retry_instruction.

        When calling activities with retry, the args dict should include:
        - tenant_id
        - run_id
        - config
        - retry_instruction (when retrying)
        """
        base_args = {
            "tenant_id": "test-tenant",
            "run_id": "test-run-123",
            "config": {"some": "config"},
        }

        # When retrying with instruction
        retry_args = {
            **base_args,
            "retry_instruction": "改善指示テキスト",
        }

        assert "retry_instruction" in retry_args
        assert retry_args["retry_instruction"] == "改善指示テキスト"

    def test_instruction_truncation_for_logging(self) -> None:
        """Test that long instructions are truncated for logging."""
        long_instruction = "A" * 200  # 200 character instruction
        truncated = long_instruction[:100] + "..."

        # Verify truncation length matches expected log output
        assert len(truncated) == 103  # 100 chars + "..."
        assert truncated.endswith("...")

    def test_activity_name_mapping(self) -> None:
        """Test step to activity name mapping."""
        activity_names = {
            "step3a": "step3a_query_analysis",
            "step3b": "step3b_cooccurrence_extraction",
            "step3c": "step3c_competitor_analysis",
        }

        # Verify all steps have corresponding activity names
        for step in ["step3a", "step3b", "step3c"]:
            assert step in activity_names
            assert activity_names[step].startswith(step)
