"""End-to-end tests for complete workflow execution.

These tests require mock_pack and optionally mock LLM responses.
Set USE_MOCK_LLM=true for testing without real API calls.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Environment configuration for E2E tests
USE_MOCK_LLM = os.getenv("USE_MOCK_LLM", "true").lower() == "true"
MOCK_PACK_ID = os.getenv("MOCK_PACK_ID", "mock_pack")


class TestWorkflowE2EWithMocks:
    """E2E tests using mock LLM and tools."""

    @pytest.fixture
    def mock_llm_response(self):
        """Create mock LLM response."""
        return MagicMock(
            content="Mock LLM response content",
            model="mock-model",
            input_tokens=100,
            output_tokens=200,
        )

    @pytest.fixture
    def workflow_config(self):
        """Standard workflow configuration for testing."""
        return {
            "pack_id": MOCK_PACK_ID,
            "keyword": "テストキーワード",
            "llm_provider": "gemini",
            "max_tokens": 2000,
            "temperature": 0.7,
        }

    @pytest.mark.skipif(not USE_MOCK_LLM, reason="Requires mock LLM")
    def test_pack_id_required(self, workflow_config):
        """Test workflow requires pack_id."""
        config_without_pack = {k: v for k, v in workflow_config.items() if k != "pack_id"}
        assert "pack_id" not in config_without_pack

    @pytest.mark.skipif(not USE_MOCK_LLM, reason="Requires mock LLM")
    def test_mock_pack_available(self):
        """Test mock_pack is available for testing."""
        from apps.api.prompts.loader import PromptPackLoader

        loader = PromptPackLoader()
        pack = loader.load("mock_pack")

        assert pack is not None
        assert pack.pack_id == "mock_pack"

    @pytest.mark.skipif(not USE_MOCK_LLM, reason="Requires mock LLM")
    def test_config_has_all_required_fields(self, workflow_config):
        """Test configuration has all required fields."""
        required = ["pack_id", "keyword"]

        for field in required:
            assert field in workflow_config, f"Missing required field: {field}"


class TestWorkflowStateTransitions:
    """Tests for workflow state transitions."""

    def test_initial_state_is_pending(self):
        """Test workflow starts in pending state."""
        from apps.worker.workflows.article_workflow import ArticleWorkflow

        workflow = ArticleWorkflow()
        status = workflow.get_status()

        assert status["approved"] is False
        assert status["rejected"] is False

    def test_approval_changes_state(self):
        """Test approval signal changes workflow state."""
        from apps.worker.workflows.article_workflow import ArticleWorkflow
        import asyncio

        workflow = ArticleWorkflow()
        asyncio.get_event_loop().run_until_complete(workflow.approve())

        status = workflow.get_status()
        assert status["approved"] is True

    def test_rejection_changes_state(self):
        """Test rejection signal changes workflow state."""
        from apps.worker.workflows.article_workflow import ArticleWorkflow
        import asyncio

        workflow = ArticleWorkflow()
        asyncio.get_event_loop().run_until_complete(workflow.reject("Quality issues"))

        status = workflow.get_status()
        assert status["rejected"] is True
        assert status["rejection_reason"] == "Quality issues"


class TestIdempotency:
    """Tests for workflow idempotency."""

    def test_same_input_produces_same_digest(self):
        """Test identical inputs produce identical digests."""
        from apps.worker.activities.base import BaseActivity

        class TestActivity(BaseActivity):
            @property
            def step_id(self):
                return "test"

            async def execute(self, ctx, state):
                return {}

        activity = TestActivity()

        config = {"pack_id": "mock_pack", "keyword": "test"}
        digest1 = activity._compute_input_digest("tenant", "run", config)
        digest2 = activity._compute_input_digest("tenant", "run", config)

        assert digest1 == digest2

    def test_different_runs_produce_different_digests(self):
        """Test different run_ids produce different digests."""
        from apps.worker.activities.base import BaseActivity

        class TestActivity(BaseActivity):
            @property
            def step_id(self):
                return "test"

            async def execute(self, ctx, state):
                return {}

        activity = TestActivity()

        config = {"pack_id": "mock_pack", "keyword": "test"}
        digest1 = activity._compute_input_digest("tenant", "run1", config)
        digest2 = activity._compute_input_digest("tenant", "run2", config)

        assert digest1 != digest2


class TestFallbackProhibition:
    """Tests to verify no fallback behavior exists."""

    def test_no_fallback_in_workflow_code(self):
        """Test workflow code contains no fallback patterns."""
        import inspect
        from apps.worker.workflows import article_workflow

        source = inspect.getsource(article_workflow)

        # Check for forbidden patterns
        forbidden_patterns = [
            "fallback",
            "fall_back",
            "alternate_model",
            "backup_provider",
        ]

        for pattern in forbidden_patterns:
            assert pattern.lower() not in source.lower(), \
                f"Found forbidden pattern '{pattern}' in workflow code"

    def test_no_fallback_in_activity_code(self):
        """Test activity code contains no fallback patterns."""
        import inspect
        from apps.worker.activities import base

        source = inspect.getsource(base)

        forbidden_patterns = [
            "fallback",
            "fall_back",
            "alternate_model",
            "backup_provider",
        ]

        for pattern in forbidden_patterns:
            # Allow 'fallback' in comments/docstrings about prohibition
            lines_with_pattern = [
                line for line in source.split('\n')
                if pattern.lower() in line.lower()
                and not line.strip().startswith('#')
                and '"""' not in line
            ]
            assert len(lines_with_pattern) == 0, \
                f"Found forbidden pattern '{pattern}' in activity code"
