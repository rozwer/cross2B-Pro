"""Structured logging for workflow observability.

Provides context-aware logging with automatic tenant/run/step tagging.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime
from typing import Any

# Context variables for automatic tagging
_tenant_id: ContextVar[str | None] = ContextVar("tenant_id", default=None)
_run_id: ContextVar[str | None] = ContextVar("run_id", default=None)
_step_id: ContextVar[str | None] = ContextVar("step_id", default=None)


def set_context(
    tenant_id: str | None = None,
    run_id: str | None = None,
    step_id: str | None = None,
) -> None:
    """Set logging context variables."""
    if tenant_id is not None:
        _tenant_id.set(tenant_id)
    if run_id is not None:
        _run_id.set(run_id)
    if step_id is not None:
        _step_id.set(step_id)


def clear_context() -> None:
    """Clear all logging context variables."""
    _tenant_id.set(None)
    _run_id.set(None)
    _step_id.set(None)


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add context from contextvars
        if tenant_id := _tenant_id.get():
            log_data["tenant_id"] = tenant_id
        if run_id := _run_id.get():
            log_data["run_id"] = run_id
        if step_id := _step_id.get():
            log_data["step_id"] = step_id

        # Add extra fields
        if hasattr(record, "extra_data"):
            log_data["data"] = record.extra_data

        # Add exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class StructuredLogger:
    """Logger with structured output and context awareness."""

    def __init__(self, name: str, level: int = logging.INFO):
        """Initialize structured logger.

        Args:
            name: Logger name
            level: Logging level
        """
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)

        # Add handler if not already configured
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(StructuredFormatter())
            self._logger.addHandler(handler)

    def _log(
        self,
        level: int,
        msg: str,
        *args: Any,
        extra_data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Log with optional extra data."""
        extra = kwargs.pop("extra", {})
        if extra_data:
            extra["extra_data"] = extra_data
        self._logger.log(level, msg, *args, extra=extra, **kwargs)

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log info message."""
        self._log(logging.INFO, msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message."""
        self._log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log error message."""
        self._log(logging.ERROR, msg, *args, **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log exception with traceback."""
        self._log(logging.ERROR, msg, *args, exc_info=True, **kwargs)

    def step_started(
        self,
        step_id: str,
        attempt: int = 1,
        **extra: Any,
    ) -> None:
        """Log step started event."""
        self.info(
            f"Step {step_id} started (attempt {attempt})",
            extra_data={"step_id": step_id, "attempt": attempt, **extra},
        )

    def step_completed(
        self,
        step_id: str,
        duration_ms: int | None = None,
        **extra: Any,
    ) -> None:
        """Log step completed event."""
        data = {"step_id": step_id, **extra}
        if duration_ms:
            data["duration_ms"] = duration_ms
        self.info(f"Step {step_id} completed", extra_data=data)

    def step_failed(
        self,
        step_id: str,
        error: str,
        category: str,
        **extra: Any,
    ) -> None:
        """Log step failed event."""
        self.error(
            f"Step {step_id} failed: {error}",
            extra_data={
                "step_id": step_id,
                "error": error,
                "category": category,
                **extra,
            },
        )

    def llm_request(
        self,
        provider: str,
        model: str,
        tokens_in: int | None = None,
        **extra: Any,
    ) -> None:
        """Log LLM request."""
        self.info(
            f"LLM request to {provider}/{model}",
            extra_data={
                "provider": provider,
                "model": model,
                "tokens_in": tokens_in,
                **extra,
            },
        )

    def llm_response(
        self,
        provider: str,
        model: str,
        tokens_out: int | None = None,
        latency_ms: int | None = None,
        **extra: Any,
    ) -> None:
        """Log LLM response."""
        self.info(
            f"LLM response from {provider}/{model}",
            extra_data={
                "provider": provider,
                "model": model,
                "tokens_out": tokens_out,
                "latency_ms": latency_ms,
                **extra,
            },
        )


# Global logger cache
_loggers: dict[str, StructuredLogger] = {}


def get_logger(name: str) -> StructuredLogger:
    """Get or create a structured logger.

    Args:
        name: Logger name

    Returns:
        StructuredLogger instance
    """
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name)
    return _loggers[name]
