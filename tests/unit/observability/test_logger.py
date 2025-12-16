"""Tests for structured logging."""

import json

from apps.api.observability.logger import (
    StructuredLogger,
    clear_context,
    get_logger,
    set_context,
)


class TestStructuredLogger:
    """Tests for StructuredLogger."""

    def test_get_logger_caches(self) -> None:
        """Test that get_logger returns same instance."""
        logger1 = get_logger("test")
        logger2 = get_logger("test")
        assert logger1 is logger2

    def test_get_logger_different_names(self) -> None:
        """Test that different names get different loggers."""
        logger1 = get_logger("test1")
        logger2 = get_logger("test2")
        assert logger1 is not logger2


class TestLoggingContext:
    """Tests for logging context management."""

    def test_set_and_clear_context(self) -> None:
        """Test setting and clearing context."""
        set_context(tenant_id="tenant-abc", run_id="run-123", step_id="step_1")

        # Clear should reset all
        clear_context()

        # After clear, context should be None
        from apps.api.observability.logger import _run_id, _step_id, _tenant_id

        assert _tenant_id.get() is None
        assert _run_id.get() is None
        assert _step_id.get() is None

    def test_partial_context_update(self) -> None:
        """Test that partial updates preserve other values."""
        clear_context()
        set_context(tenant_id="tenant-abc")

        from apps.api.observability.logger import _run_id, _tenant_id

        assert _tenant_id.get() == "tenant-abc"
        assert _run_id.get() is None

        set_context(run_id="run-123")
        assert _tenant_id.get() == "tenant-abc"
        assert _run_id.get() == "run-123"
