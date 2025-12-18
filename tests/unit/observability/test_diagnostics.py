"""Tests for DiagnosticsService."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from apps.api.observability.diagnostics import (
    DiagnosticsService,
    DiagnosticResult,
    RecommendedAction,
    DIAGNOSTIC_SYSTEM_PROMPT,
)


class TestDiagnosticResult:
    """Tests for DiagnosticResult model."""

    def test_create_diagnostic_result(self):
        """Test creating a diagnostic result."""
        result = DiagnosticResult(
            root_cause="LLM rate limit exceeded",
            recommended_actions=[
                RecommendedAction(
                    priority=1,
                    action="Wait and retry",
                    rationale="Rate limits reset after 60 seconds",
                    step_to_resume="step3",
                ),
            ],
            resume_step="step3",
            confidence=0.85,
            summary="Rate limit issue, retry recommended",
        )

        assert result.root_cause == "LLM rate limit exceeded"
        assert len(result.recommended_actions) == 1
        assert result.recommended_actions[0].priority == 1
        assert result.resume_step == "step3"
        assert result.confidence == 0.85

    def test_diagnostic_result_validation(self):
        """Test that confidence is properly validated."""
        with pytest.raises(ValueError):
            DiagnosticResult(
                root_cause="Test",
                recommended_actions=[],
                confidence=1.5,  # Invalid: > 1.0
                summary="Test",
            )


class TestRecommendedAction:
    """Tests for RecommendedAction model."""

    def test_create_recommended_action(self):
        """Test creating a recommended action."""
        action = RecommendedAction(
            priority=1,
            action="Fix authentication",
            rationale="API key is invalid",
        )

        assert action.priority == 1
        assert action.step_to_resume is None

    def test_priority_validation(self):
        """Test priority validation (1-10)."""
        with pytest.raises(ValueError):
            RecommendedAction(
                priority=0,  # Invalid: < 1
                action="Test",
                rationale="Test",
            )

        with pytest.raises(ValueError):
            RecommendedAction(
                priority=11,  # Invalid: > 10
                action="Test",
                rationale="Test",
            )


class TestDiagnosticsService:
    """Tests for DiagnosticsService."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = MagicMock()
        client.provider_name = "anthropic"
        client.default_model = "claude-sonnet-4"
        client.generate_json = AsyncMock(return_value={
            "root_cause": "Network timeout during LLM call",
            "recommended_actions": [
                {
                    "priority": 1,
                    "action": "Retry the workflow",
                    "rationale": "Network issues are often transient",
                    "step_to_resume": "step3",
                },
            ],
            "resume_step": "step3",
            "confidence": 0.75,
            "summary": "Network timeout - retry recommended",
        })
        return client

    @pytest.fixture
    def mock_error_collector(self):
        """Create a mock error collector."""
        collector = MagicMock()
        collector.get_errors_for_run = AsyncMock(return_value=[])
        collector.get_error_summary = AsyncMock(return_value={
            "total_errors": 1,
            "by_category": {"retryable": 1},
            "by_step": {"step3": 1},
            "by_source": {"llm": 1},
            "by_type": {"LLMTimeoutError": 1},
            "timeline": [],
        })
        collector.build_diagnostic_context = AsyncMock(return_value={
            "run_id": "run-123",
            "run_status": "failed",
            "current_step": "step3",
            "final_error": "Timeout",
            "input_data": {"keyword": "test"},
            "config": {},
            "error_summary": {
                "total_errors": 1,
                "by_category": {"retryable": 1},
                "by_step": {"step3": 1},
                "by_source": {"llm": 1},
                "by_type": {"LLMTimeoutError": 1},
                "timeline": [
                    {
                        "step": "step3",
                        "source": "llm",
                        "type": "LLMTimeoutError",
                        "message": "Timeout",
                        "attempt": 3,
                        "timestamp": datetime.now().isoformat(),
                    }
                ],
            },
            "error_logs": [
                {
                    "step_id": "step3",
                    "source": "llm",
                    "category": "retryable",
                    "type": "LLMTimeoutError",
                    "message": "Timeout after 30s",
                    "context": {"timeout_ms": 30000},
                    "attempt": 3,
                    "timestamp": datetime.now().isoformat(),
                    "stack_trace": None,
                }
            ],
            "step_history": [
                {"step": "step0", "status": "completed"},
                {"step": "step1", "status": "completed"},
                {"step": "step2", "status": "completed"},
                {"step": "step3", "status": "failed", "error_message": "Timeout"},
            ],
        })
        return collector

    @pytest.fixture
    def service(self, mock_session, mock_llm_client, mock_error_collector):
        """Create DiagnosticsService with mocks."""
        service = DiagnosticsService(
            session=mock_session,
            llm_provider="anthropic",
            llm_client=mock_llm_client,
        )
        service._error_collector = mock_error_collector
        return service

    @pytest.mark.asyncio
    async def test_analyze_failure(self, service, mock_session, mock_llm_client):
        """Test analyzing a failed run."""
        report = await service.analyze_failure("run-123", "tenant-1")

        # Verify LLM was called
        mock_llm_client.generate_json.assert_called_once()

        # Verify report was saved
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

        # Check report content
        saved_report = mock_session.add.call_args[0][0]
        assert saved_report.run_id == "run-123"
        assert saved_report.llm_provider == "anthropic"
        assert "Network timeout" in saved_report.root_cause_analysis

    @pytest.mark.asyncio
    async def test_analyze_failure_with_llm_error(
        self, service, mock_session, mock_llm_client, mock_error_collector
    ):
        """Test fallback when LLM analysis fails."""
        mock_llm_client.generate_json.side_effect = Exception("LLM unavailable")

        # Update mock to return non_retryable errors
        mock_error_collector.build_diagnostic_context.return_value = {
            "run_id": "run-123",
            "run_status": "failed",
            "current_step": "step2",
            "final_error": "Auth error",
            "input_data": {},
            "config": {},
            "error_summary": {
                "total_errors": 1,
                "by_category": {"non_retryable": 1},
                "by_step": {},
                "by_type": {},
                "timeline": [],
            },
            "error_logs": [],
            "step_history": [],
        }

        report = await service.analyze_failure("run-123", "tenant-1")

        # Should still save a report (fallback diagnosis)
        mock_session.add.assert_called_once()
        saved_report = mock_session.add.call_args[0][0]

        # Fallback should mention non-retryable
        assert "non-retryable" in saved_report.root_cause_analysis.lower() or \
               "Non-retryable" in saved_report.root_cause_analysis

    @pytest.mark.asyncio
    async def test_get_latest_diagnosis(self, service, mock_session):
        """Test retrieving the latest diagnosis."""
        mock_report = MagicMock()
        mock_report.id = 1
        mock_report.run_id = "run-123"
        mock_report.root_cause_analysis = "Test analysis"
        mock_report.created_at = datetime.now()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_report
        mock_session.execute.return_value = mock_result

        report = await service.get_latest_diagnosis("run-123")

        assert report is not None
        assert report.run_id == "run-123"

    def test_format_user_prompt(self, service):
        """Test prompt formatting."""
        context = {
            "run_id": "run-123",
            "run_status": "failed",
            "current_step": "step3",
            "final_error": "Timeout error",
            "input_data": {"keyword": "test"},
            "config": {"llm_provider": "gemini"},
            "error_summary": {
                "total_errors": 2,
                "by_category": {"retryable": 2},
                "by_step": {"step3": 2},
                "by_source": {"llm": 2},
                "by_type": {"LLMTimeoutError": 2},
                "timeline": [
                    {
                        "timestamp": "2024-01-01T12:00:00",
                        "step": "step3",
                        "source": "llm",
                        "type": "LLMTimeoutError",
                        "attempt": 1,
                        "message": "First timeout",
                    },
                ],
            },
            "step_history": [
                {"step": "step0", "status": "completed"},
                {"step": "step3", "status": "failed", "error_message": "Timeout"},
            ],
        }

        prompt = service._format_user_prompt(context)

        assert "run-123" in prompt
        assert "failed" in prompt
        assert "step3" in prompt
        assert "LLMTimeoutError" in prompt

    def test_create_fallback_diagnosis_non_retryable(self, service):
        """Test fallback diagnosis for non-retryable errors."""
        context = {
            "current_step": "step2",
            "error_summary": {
                "by_category": {"non_retryable": 1},
                "by_type": {"LLMAuthenticationError": 1},
            },
        }

        result = service._create_fallback_diagnosis(context)

        assert "non-retryable" in result.root_cause.lower() or \
               "Non-retryable" in result.root_cause
        assert result.confidence == 0.3
        assert len(result.recommended_actions) > 0

    def test_create_fallback_diagnosis_validation_fail(self, service):
        """Test fallback diagnosis for validation failures."""
        context = {
            "current_step": "step5",
            "error_summary": {
                "by_category": {"validation_fail": 1},
                "by_type": {"LLMValidationError": 1},
            },
        }

        result = service._create_fallback_diagnosis(context)

        assert "validation" in result.root_cause.lower()
        assert result.resume_step == "step5"

    def test_create_fallback_diagnosis_retryable(self, service):
        """Test fallback diagnosis for retryable errors."""
        context = {
            "current_step": "step3",
            "error_summary": {
                "by_category": {"retryable": 3},
                "by_type": {"LLMTimeoutError": 3},
            },
        }

        result = service._create_fallback_diagnosis(context)

        assert "retry" in result.root_cause.lower()
        assert result.resume_step == "step3"


class TestDiagnosticSystemPrompt:
    """Tests for the diagnostic system prompt."""

    def test_system_prompt_contains_workflow_steps(self):
        """Test that system prompt documents workflow steps."""
        assert "step0" in DIAGNOSTIC_SYSTEM_PROMPT
        assert "step10" in DIAGNOSTIC_SYSTEM_PROMPT

    def test_system_prompt_contains_error_categories(self):
        """Test that system prompt documents error categories."""
        assert "retryable" in DIAGNOSTIC_SYSTEM_PROMPT
        assert "non_retryable" in DIAGNOSTIC_SYSTEM_PROMPT
        assert "validation_fail" in DIAGNOSTIC_SYSTEM_PROMPT

    def test_system_prompt_has_guidelines(self):
        """Test that system prompt includes guidelines."""
        assert "root cause" in DIAGNOSTIC_SYSTEM_PROMPT.lower()
        assert "priority" in DIAGNOSTIC_SYSTEM_PROMPT.lower()
