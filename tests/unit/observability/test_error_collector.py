"""Tests for ErrorCollector service."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from apps.api.core.errors import ErrorCategory
from apps.api.observability.error_collector import (
    ErrorCollector,
    ErrorLogEntry,
    GlobalErrorCollector,
    LogSource,
    get_global_collector,
)


class TestLogSource:
    """Tests for LogSource enum."""

    def test_all_sources_defined(self):
        """Test all log sources are defined."""
        assert LogSource.LLM.value == "llm"
        assert LogSource.TOOL.value == "tool"
        assert LogSource.VALIDATION.value == "validation"
        assert LogSource.STORAGE.value == "storage"
        assert LogSource.ACTIVITY.value == "activity"
        assert LogSource.API.value == "api"


class TestErrorLogEntry:
    """Tests for ErrorLogEntry model."""

    def test_create_error_log_entry(self):
        """Test creating a basic error log entry."""
        entry = ErrorLogEntry(
            run_id="run-123",
            step_id="step1",
            error_category=ErrorCategory.RETRYABLE,
            error_type="LLMTimeoutError",
            error_message="Request timed out",
        )

        assert entry.run_id == "run-123"
        assert entry.step_id == "step1"
        assert entry.source == LogSource.ACTIVITY  # Default value
        assert entry.error_category == ErrorCategory.RETRYABLE
        assert entry.error_type == "LLMTimeoutError"
        assert entry.attempt == 1

    def test_error_log_entry_with_source(self):
        """Test error log entry with explicit source."""
        entry = ErrorLogEntry(
            run_id="run-123",
            source=LogSource.LLM,
            error_category=ErrorCategory.RETRYABLE,
            error_type="LLMTimeoutError",
            error_message="Request timed out",
        )

        assert entry.source == LogSource.LLM

    def test_error_log_entry_with_context(self):
        """Test error log entry with additional context."""
        entry = ErrorLogEntry(
            run_id="run-123",
            error_category=ErrorCategory.NON_RETRYABLE,
            error_type="LLMAuthenticationError",
            error_message="Invalid API key",
            context={"provider": "anthropic", "model": "claude-sonnet-4"},
            attempt=2,
        )

        assert entry.context == {"provider": "anthropic", "model": "claude-sonnet-4"}
        assert entry.attempt == 2


class TestErrorCollector:
    """Tests for ErrorCollector service."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def collector(self, mock_session):
        """Create ErrorCollector with mock session."""
        return ErrorCollector(mock_session)

    @pytest.mark.asyncio
    async def test_log_error(self, collector, mock_session):
        """Test logging an error."""
        error_log = await collector.log_error(
            run_id="run-123",
            step_id="step1",
            error_category=ErrorCategory.RETRYABLE,
            error_type="LLMTimeoutError",
            error_message="Request timed out",
            context={"timeout_ms": 30000},
            attempt=1,
        )

        # Verify session.add was called
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

        # Verify the error log object
        added_log = mock_session.add.call_args[0][0]
        assert added_log.run_id == "run-123"
        assert added_log.step_id == "step1"
        assert added_log.error_category == "retryable"
        assert added_log.error_type == "LLMTimeoutError"

    @pytest.mark.asyncio
    async def test_log_exception(self, collector, mock_session):
        """Test logging an exception with automatic stack trace."""
        try:
            raise ValueError("Test error message")
        except ValueError as e:
            error_log = await collector.log_exception(
                run_id="run-123",
                exception=e,
                error_category=ErrorCategory.NON_RETRYABLE,
                step_id="step2",
            )

        mock_session.add.assert_called_once()
        added_log = mock_session.add.call_args[0][0]
        assert added_log.error_type == "ValueError"
        assert added_log.error_message == "Test error message"
        assert added_log.stack_trace is not None
        assert "ValueError" in added_log.stack_trace

    @pytest.mark.asyncio
    async def test_get_errors_for_run(self, collector, mock_session):
        """Test retrieving errors for a run."""
        # Setup mock return
        mock_error = MagicMock()
        mock_error.id = 1
        mock_error.run_id = "run-123"
        mock_error.step_id = "step1"
        mock_error.error_category = "retryable"
        mock_error.error_type = "LLMTimeoutError"
        mock_error.error_message = "Timeout"
        mock_error.created_at = datetime.now()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_error]
        mock_session.execute.return_value = mock_result

        errors = await collector.get_errors_for_run("run-123")

        assert len(errors) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_error_summary(self, collector, mock_session):
        """Test error summary generation."""
        # Setup mock errors
        mock_error1 = MagicMock()
        mock_error1.error_category = "retryable"
        mock_error1.step_id = "step1"
        mock_error1.source = "llm"
        mock_error1.error_type = "LLMTimeoutError"
        mock_error1.error_message = "Timeout"
        mock_error1.attempt = 1
        mock_error1.created_at = datetime.now()

        mock_error2 = MagicMock()
        mock_error2.error_category = "non_retryable"
        mock_error2.step_id = "step2"
        mock_error2.source = "tool"
        mock_error2.error_type = "LLMAuthError"
        mock_error2.error_message = "Auth failed"
        mock_error2.attempt = 1
        mock_error2.created_at = datetime.now()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_error1, mock_error2]
        mock_session.execute.return_value = mock_result

        summary = await collector.get_error_summary("run-123")

        assert summary["total_errors"] == 2
        assert summary["by_category"]["retryable"] == 1
        assert summary["by_category"]["non_retryable"] == 1
        assert summary["by_step"]["step1"] == 1
        assert summary["by_step"]["step2"] == 1
        assert summary["by_source"]["llm"] == 1
        assert summary["by_source"]["tool"] == 1
        assert len(summary["timeline"]) == 2

    @pytest.mark.asyncio
    async def test_build_diagnostic_context(self, collector, mock_session):
        """Test building diagnostic context for LLM analysis."""
        # Setup mock error
        mock_error = MagicMock()
        mock_error.step_id = "step1"
        mock_error.source = "llm"
        mock_error.error_category = "retryable"
        mock_error.error_type = "LLMTimeoutError"
        mock_error.error_message = "Timeout"
        mock_error.context = {"timeout_ms": 30000}
        mock_error.attempt = 2
        mock_error.created_at = datetime.now()
        mock_error.stack_trace = "Traceback..."

        # Mock run info
        mock_run_row = MagicMock()
        mock_run_row.status = "failed"
        mock_run_row.current_step = "step1"
        mock_run_row.input_data = {"keyword": "test"}
        mock_run_row.config = {"llm_provider": "gemini"}
        mock_run_row.final_error = "Timeout after 3 retries"

        # Setup execute to return different results
        error_result = MagicMock()
        error_result.scalars.return_value.all.return_value = [mock_error]

        run_result = MagicMock()
        run_result.fetchone.return_value = mock_run_row

        steps_result = MagicMock()
        mock_step = MagicMock()
        mock_step._mapping = {
            "step": "step1",
            "status": "failed",
            "llm_model": "gemini-pro",
            "error_type": "RETRYABLE",
            "error_message": "Timeout",
            "retry_count": 3,
            "started_at": datetime.now(),
            "completed_at": None,
        }
        steps_result.__iter__ = lambda x: iter([mock_step])

        # Configure execute to return different results for different queries
        mock_session.execute.side_effect = [
            error_result,  # get_errors_for_run
            error_result,  # get_error_summary (calls get_errors_for_run)
            run_result,    # run info query
            steps_result,  # steps query
        ]

        context = await collector.build_diagnostic_context("run-123")

        assert context["run_id"] == "run-123"
        assert context["run_status"] == "failed"
        assert context["error_summary"]["total_errors"] == 1
        assert len(context["error_logs"]) == 1

    @pytest.mark.asyncio
    async def test_log_llm_error(self, collector, mock_session):
        """Test logging an LLM-specific error."""
        exc = TimeoutError("LLM request timed out")
        await collector.log_llm_error(
            run_id="run-123",
            exception=exc,
            error_category=ErrorCategory.RETRYABLE,
            provider="anthropic",
            model="claude-sonnet-4",
            step_id="step1",
            attempt=2,
            extra_context={"timeout_ms": 30000},
        )

        mock_session.add.assert_called_once()
        added_log = mock_session.add.call_args[0][0]
        assert added_log.source == "llm"
        assert added_log.context["provider"] == "anthropic"
        assert added_log.context["model"] == "claude-sonnet-4"
        assert added_log.context["timeout_ms"] == 30000

    @pytest.mark.asyncio
    async def test_log_tool_error(self, collector, mock_session):
        """Test logging a tool-specific error."""
        exc = RuntimeError("Failed to fetch URL")
        await collector.log_tool_error(
            run_id="run-123",
            exception=exc,
            error_category=ErrorCategory.RETRYABLE,
            tool_id="fetch",
            step_id="step3",
            extra_context={"url": "https://example.com"},
        )

        mock_session.add.assert_called_once()
        added_log = mock_session.add.call_args[0][0]
        assert added_log.source == "tool"
        assert added_log.context["tool_id"] == "fetch"
        assert added_log.context["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_log_validation_error(self, collector, mock_session):
        """Test logging a validation error."""
        await collector.log_validation_error(
            run_id="run-123",
            error_message="JSON schema validation failed",
            validation_type="json_schema",
            step_id="step5",
            issues=[{"path": "$.title", "error": "missing required field"}],
        )

        mock_session.add.assert_called_once()
        added_log = mock_session.add.call_args[0][0]
        assert added_log.source == "validation"
        assert added_log.error_category == "validation_fail"
        assert added_log.context["validation_type"] == "json_schema"
        assert len(added_log.context["issues"]) == 1

    @pytest.mark.asyncio
    async def test_log_storage_error(self, collector, mock_session):
        """Test logging a storage error."""
        exc = IOError("MinIO connection failed")
        await collector.log_storage_error(
            run_id="run-123",
            exception=exc,
            error_category=ErrorCategory.RETRYABLE,
            operation="put",
            path="tenant-1/run-123/step1/output.json",
            step_id="step1",
        )

        mock_session.add.assert_called_once()
        added_log = mock_session.add.call_args[0][0]
        assert added_log.source == "storage"
        assert added_log.context["operation"] == "put"
        assert added_log.context["path"] == "tenant-1/run-123/step1/output.json"

    @pytest.mark.asyncio
    async def test_get_errors_with_source_filter(self, collector, mock_session):
        """Test filtering errors by source."""
        mock_error = MagicMock()
        mock_error.source = "llm"
        mock_error.error_type = "LLMTimeoutError"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_error]
        mock_session.execute.return_value = mock_result

        errors = await collector.get_errors_for_run("run-123", source=LogSource.LLM)

        assert len(errors) == 1
        mock_session.execute.assert_called_once()


class TestGlobalErrorCollector:
    """Tests for GlobalErrorCollector."""

    @pytest.fixture
    def global_collector(self):
        """Create a new GlobalErrorCollector."""
        return GlobalErrorCollector()

    @pytest.mark.asyncio
    async def test_log_error_queues_entry(self, global_collector):
        """Test that log_error queues an entry."""
        await global_collector.log_error(
            run_id="run-123",
            error_category=ErrorCategory.RETRYABLE,
            error_type="TestError",
            error_message="Test message",
            source=LogSource.LLM,
        )

        assert global_collector.pending_count() == 1

    @pytest.mark.asyncio
    async def test_log_multiple_errors(self, global_collector):
        """Test queuing multiple errors."""
        for i in range(3):
            await global_collector.log_error(
                run_id="run-123",
                error_category=ErrorCategory.RETRYABLE,
                error_type="TestError",
                error_message=f"Test message {i}",
            )

        assert global_collector.pending_count() == 3

    @pytest.mark.asyncio
    async def test_log_exception_queues_with_stack_trace(self, global_collector):
        """Test that log_exception includes stack trace."""
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            await global_collector.log_exception(
                run_id="run-123",
                exception=e,
                error_category=ErrorCategory.NON_RETRYABLE,
                source=LogSource.TOOL,
            )

        assert global_collector.pending_count() == 1

    def test_get_global_collector_singleton(self):
        """Test that get_global_collector returns the same instance."""
        collector1 = get_global_collector()
        collector2 = get_global_collector()
        assert collector1 is collector2
