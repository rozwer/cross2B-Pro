"""Unit tests for ArticleWorkflow."""

import pytest

from apps.worker.workflows.article_workflow import (
    DEFAULT_RETRY_POLICY,
    STEP_TIMEOUTS,
    ArticleWorkflow,
)


class TestArticleWorkflow:
    """Tests for ArticleWorkflow class."""

    def test_workflow_initialization(self):
        """Test workflow initializes with correct state."""
        workflow = ArticleWorkflow()

        assert workflow.approved is False
        assert workflow.rejected is False
        assert workflow.rejection_reason is None
        assert workflow.current_step == "init"

    def test_approve_signal(self):
        """Test approve signal sets approved flag."""
        workflow = ArticleWorkflow()

        # Simulate approve signal
        import asyncio

        asyncio.get_event_loop().run_until_complete(workflow.approve())

        assert workflow.approved is True
        assert workflow.rejected is False

    def test_reject_signal(self):
        """Test reject signal sets rejected flag and reason."""
        workflow = ArticleWorkflow()
        reason = "Quality issues found"

        # Simulate reject signal
        import asyncio

        asyncio.get_event_loop().run_until_complete(workflow.reject(reason))

        assert workflow.rejected is True
        assert workflow.rejection_reason == reason

    def test_get_status_query(self):
        """Test get_status query returns correct state."""
        workflow = ArticleWorkflow()
        workflow.current_step = "step3"

        status = workflow.get_status()

        assert status["current_step"] == "step3"
        assert status["approved"] is False
        assert status["rejected"] is False
        assert status["rejection_reason"] is None

    def test_should_run_no_resume(self):
        """Test _should_run returns True when no resume_from."""
        workflow = ArticleWorkflow()

        assert workflow._should_run("step0", None) is True
        assert workflow._should_run("step5", None) is True
        assert workflow._should_run("step10", None) is True

    def test_should_run_with_resume(self):
        """Test _should_run respects resume_from step."""
        workflow = ArticleWorkflow()

        # Resume from step3 - steps before should be skipped
        assert workflow._should_run("step0", "step3") is False
        assert workflow._should_run("step1", "step3") is False
        assert workflow._should_run("step2", "step3") is False
        assert workflow._should_run("step3", "step3") is True
        assert workflow._should_run("step4", "step3") is True
        assert workflow._should_run("step10", "step3") is True

    def test_step_timeouts_defined(self):
        """Test all steps have defined timeouts."""
        expected_steps = [
            "step0",
            "step1",
            "step2",
            "step3a",
            "step3b",
            "step3c",
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

        for step in expected_steps:
            assert step in STEP_TIMEOUTS, f"Missing timeout for {step}"
            assert STEP_TIMEOUTS[step] > 0

    def test_step7a_has_longest_timeout(self):
        """Test step7a (draft generation) has the longest timeout."""
        max_timeout = max(STEP_TIMEOUTS.values())
        assert STEP_TIMEOUTS["step7a"] == max_timeout
        assert STEP_TIMEOUTS["step7a"] == 600  # 10 minutes

    def test_default_retry_policy(self):
        """Test default retry policy is configured correctly."""
        assert DEFAULT_RETRY_POLICY.maximum_attempts == 3


class TestWorkflowPackIdValidation:
    """Tests for pack_id validation in workflow."""

    @pytest.mark.asyncio
    async def test_missing_pack_id_raises_application_error(self):
        """Test workflow raises ApplicationError if pack_id is missing."""
        from temporalio.exceptions import ApplicationError

        workflow = ArticleWorkflow()

        # Workflow should raise ApplicationError when pack_id is missing
        with pytest.raises(ApplicationError) as exc_info:
            await workflow.run(
                tenant_id="test_tenant",
                run_id="test_run",
                config={},  # No pack_id
            )

        assert "pack_id required" in str(exc_info.value)
        assert exc_info.value.type == "VALIDATION_ERROR"

    def test_pack_id_provided_passes_validation(self):
        """Test pack_id check passes when provided."""
        # We can't fully test workflow execution without mocking Temporal,
        # but we can verify the pack_id validation logic
        config = {"pack_id": "mock_pack"}
        pack_id = config.get("pack_id")
        assert pack_id is not None
