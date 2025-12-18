"""Error log collection service for run-scoped error tracking.

Collects all errors within a run session for:
- Debugging and tracing
- LLM-based failure diagnosis
- Recovery recommendations

Supports multiple log sources:
- llm: LLM provider errors (timeout, rate limit, auth)
- tool: Tool execution errors (search, fetch, verify)
- validation: Output validation failures
- storage: MinIO/artifact storage errors
- activity: Temporal activity errors
- api: FastAPI endpoint errors
"""

import asyncio
import logging
import traceback
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.errors import ErrorCategory
from apps.api.db.models import ErrorLog

logger = logging.getLogger(__name__)


class LogSource(str, Enum):
    """Error log source classification."""

    LLM = "llm"
    TOOL = "tool"
    VALIDATION = "validation"
    STORAGE = "storage"
    ACTIVITY = "activity"
    API = "api"


class ErrorLogEntry(BaseModel):
    """Structured error log entry for collection."""

    run_id: str = Field(..., description="Run identifier")
    step_id: str | None = Field(default=None, description="Step identifier")
    source: LogSource = Field(default=LogSource.ACTIVITY, description="Error source")
    error_category: ErrorCategory = Field(..., description="Error classification")
    error_type: str = Field(..., description="Exception class name")
    error_message: str = Field(..., description="Error message")
    stack_trace: str | None = Field(default=None, description="Full stack trace")
    context: dict[str, Any] | None = Field(
        default=None, description="Additional context (LLM model, tool, params)"
    )
    attempt: int = Field(default=1, ge=1, description="Attempt number")
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorCollector:
    """Collects and persists error logs for diagnostic purposes.

    Usage:
        collector = ErrorCollector(session)

        # Log an error
        await collector.log_error(
            run_id="run-123",
            step_id="step1",
            error_category=ErrorCategory.RETRYABLE,
            error_type="LLMTimeoutError",
            error_message="Request timed out",
            context={"model": "gpt-4", "timeout_ms": 30000},
            attempt=2,
        )

        # Get all errors for a run
        errors = await collector.get_errors_for_run("run-123")
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize error collector.

        Args:
            session: Async database session
        """
        self._session = session

    async def log_error(
        self,
        run_id: str,
        error_category: ErrorCategory | str,
        error_type: str,
        error_message: str,
        source: LogSource | str = LogSource.ACTIVITY,
        step_id: str | None = None,
        stack_trace: str | None = None,
        context: dict[str, Any] | None = None,
        attempt: int = 1,
    ) -> ErrorLog:
        """Log an error to the database.

        Args:
            run_id: Run identifier
            error_category: Classification for retry decisions
            error_type: Exception class name
            error_message: Human-readable error message
            source: Error source (llm, tool, validation, storage, activity, api)
            step_id: Step identifier (optional)
            stack_trace: Full stack trace (optional)
            context: Additional context like LLM model, tool, input params
            attempt: Which attempt number failed

        Returns:
            Created ErrorLog record
        """
        category_str = (
            error_category.value
            if isinstance(error_category, ErrorCategory)
            else error_category
        )
        source_str = source.value if isinstance(source, LogSource) else source

        error_log = ErrorLog(
            run_id=run_id,
            step_id=step_id,
            source=source_str,
            error_category=category_str,
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            context=context,
            attempt=attempt,
        )

        self._session.add(error_log)
        await self._session.flush()
        return error_log

    async def log_exception(
        self,
        run_id: str,
        exception: Exception,
        error_category: ErrorCategory | str,
        source: LogSource | str = LogSource.ACTIVITY,
        step_id: str | None = None,
        context: dict[str, Any] | None = None,
        attempt: int = 1,
    ) -> ErrorLog:
        """Log an exception with automatic stack trace extraction.

        Args:
            run_id: Run identifier
            exception: The exception to log
            error_category: Classification for retry decisions
            source: Error source (llm, tool, validation, storage, activity, api)
            step_id: Step identifier (optional)
            context: Additional context
            attempt: Which attempt number failed

        Returns:
            Created ErrorLog record
        """
        stack_trace = "".join(
            traceback.format_exception(type(exception), exception, exception.__traceback__)
        )

        return await self.log_error(
            run_id=run_id,
            step_id=step_id,
            source=source,
            error_category=error_category,
            error_type=type(exception).__name__,
            error_message=str(exception),
            stack_trace=stack_trace,
            context=context,
            attempt=attempt,
        )

    # =========================================================================
    # Source-specific log methods
    # =========================================================================

    async def log_llm_error(
        self,
        run_id: str,
        exception: Exception,
        error_category: ErrorCategory | str,
        provider: str,
        model: str,
        step_id: str | None = None,
        attempt: int = 1,
        extra_context: dict[str, Any] | None = None,
    ) -> ErrorLog:
        """Log an LLM provider error.

        Args:
            run_id: Run identifier
            exception: The LLM exception
            error_category: Classification for retry decisions
            provider: LLM provider name (anthropic, openai, gemini)
            model: Model name used
            step_id: Step identifier (optional)
            attempt: Attempt number
            extra_context: Additional context

        Returns:
            Created ErrorLog record
        """
        context = {
            "provider": provider,
            "model": model,
            **(extra_context or {}),
        }
        return await self.log_exception(
            run_id=run_id,
            exception=exception,
            error_category=error_category,
            source=LogSource.LLM,
            step_id=step_id,
            context=context,
            attempt=attempt,
        )

    async def log_tool_error(
        self,
        run_id: str,
        exception: Exception,
        error_category: ErrorCategory | str,
        tool_id: str,
        step_id: str | None = None,
        attempt: int = 1,
        extra_context: dict[str, Any] | None = None,
    ) -> ErrorLog:
        """Log a tool execution error.

        Args:
            run_id: Run identifier
            exception: The tool exception
            error_category: Classification for retry decisions
            tool_id: Tool identifier (search, fetch, verify)
            step_id: Step identifier (optional)
            attempt: Attempt number
            extra_context: Additional context (URL, query, etc.)

        Returns:
            Created ErrorLog record
        """
        context = {
            "tool_id": tool_id,
            **(extra_context or {}),
        }
        return await self.log_exception(
            run_id=run_id,
            exception=exception,
            error_category=error_category,
            source=LogSource.TOOL,
            step_id=step_id,
            context=context,
            attempt=attempt,
        )

    async def log_validation_error(
        self,
        run_id: str,
        error_message: str,
        validation_type: str,
        step_id: str | None = None,
        issues: list[dict[str, Any]] | None = None,
        extra_context: dict[str, Any] | None = None,
    ) -> ErrorLog:
        """Log a validation failure.

        Args:
            run_id: Run identifier
            error_message: Validation error message
            validation_type: Type of validation (json, csv, schema)
            step_id: Step identifier (optional)
            issues: List of validation issues
            extra_context: Additional context

        Returns:
            Created ErrorLog record
        """
        context = {
            "validation_type": validation_type,
            "issues": issues or [],
            **(extra_context or {}),
        }
        return await self.log_error(
            run_id=run_id,
            error_category=ErrorCategory.VALIDATION_FAIL,
            error_type="ValidationError",
            error_message=error_message,
            source=LogSource.VALIDATION,
            step_id=step_id,
            context=context,
        )

    async def log_storage_error(
        self,
        run_id: str,
        exception: Exception,
        error_category: ErrorCategory | str,
        operation: str,
        path: str | None = None,
        step_id: str | None = None,
        extra_context: dict[str, Any] | None = None,
    ) -> ErrorLog:
        """Log a storage operation error.

        Args:
            run_id: Run identifier
            exception: The storage exception
            error_category: Classification for retry decisions
            operation: Storage operation (put, get, delete)
            path: Artifact path
            step_id: Step identifier (optional)
            extra_context: Additional context

        Returns:
            Created ErrorLog record
        """
        context = {
            "operation": operation,
            "path": path,
            **(extra_context or {}),
        }
        return await self.log_exception(
            run_id=run_id,
            exception=exception,
            error_category=error_category,
            source=LogSource.STORAGE,
            step_id=step_id,
            context=context,
        )

    async def get_errors_for_run(
        self,
        run_id: str,
        step_id: str | None = None,
        source: LogSource | str | None = None,
        limit: int | None = None,
    ) -> list[ErrorLog]:
        """Get all error logs for a run.

        Args:
            run_id: Run identifier
            step_id: Filter by step (optional)
            source: Filter by source (optional)
            limit: Maximum number of errors to return

        Returns:
            List of ErrorLog records ordered by created_at
        """
        stmt = (
            select(ErrorLog)
            .where(ErrorLog.run_id == run_id)
            .order_by(ErrorLog.created_at.asc())
        )

        if step_id:
            stmt = stmt.where(ErrorLog.step_id == step_id)

        if source:
            source_str = source.value if isinstance(source, LogSource) else source
            stmt = stmt.where(ErrorLog.source == source_str)

        if limit:
            stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_error_summary(self, run_id: str) -> dict[str, Any]:
        """Get a summary of errors for a run.

        Args:
            run_id: Run identifier

        Returns:
            Dictionary with error counts by category, step, source, and type
        """
        errors = await self.get_errors_for_run(run_id)

        summary: dict[str, Any] = {
            "total_errors": len(errors),
            "by_category": {},
            "by_step": {},
            "by_source": {},
            "by_type": {},
            "timeline": [],
        }

        for error in errors:
            # Count by category
            cat = error.error_category
            summary["by_category"][cat] = summary["by_category"].get(cat, 0) + 1

            # Count by step
            step = error.step_id or "unknown"
            summary["by_step"][step] = summary["by_step"].get(step, 0) + 1

            # Count by source
            src = error.source
            summary["by_source"][src] = summary["by_source"].get(src, 0) + 1

            # Count by type
            etype = error.error_type
            summary["by_type"][etype] = summary["by_type"].get(etype, 0) + 1

            # Timeline
            summary["timeline"].append(
                {
                    "step": error.step_id,
                    "source": error.source,
                    "type": error.error_type,
                    "message": error.error_message[:200],
                    "attempt": error.attempt,
                    "timestamp": error.created_at.isoformat(),
                }
            )

        return summary

    async def build_diagnostic_context(self, run_id: str) -> dict[str, Any]:
        """Build context for LLM diagnostic analysis.

        Compiles all error logs and related information for the
        diagnostics service to analyze.

        Args:
            run_id: Run identifier

        Returns:
            Structured context for LLM analysis
        """
        errors = await self.get_errors_for_run(run_id)
        summary = await self.get_error_summary(run_id)

        # Get run details
        run_info = await self._session.execute(
            text(
                """
                SELECT
                    r.status,
                    r.current_step,
                    r.input_data,
                    r.config,
                    r.error_message as final_error
                FROM runs r
                WHERE r.id = :run_id
                """
            ),
            {"run_id": run_id},
        )
        run_row = run_info.fetchone()

        # Get step execution history
        steps_result = await self._session.execute(
            text(
                """
                SELECT
                    step,
                    status,
                    llm_model,
                    error_type,
                    error_message,
                    retry_count,
                    started_at,
                    completed_at
                FROM steps
                WHERE run_id = :run_id
                ORDER BY started_at ASC
                """
            ),
            {"run_id": run_id},
        )
        steps = [dict(row._mapping) for row in steps_result]

        return {
            "run_id": run_id,
            "run_status": run_row.status if run_row else "unknown",
            "current_step": run_row.current_step if run_row else None,
            "final_error": run_row.final_error if run_row else None,
            "input_data": run_row.input_data if run_row else None,
            "config": run_row.config if run_row else None,
            "error_summary": summary,
            "error_logs": [
                {
                    "step_id": e.step_id,
                    "source": e.source,
                    "category": e.error_category,
                    "type": e.error_type,
                    "message": e.error_message,
                    "context": e.context,
                    "attempt": e.attempt,
                    "timestamp": e.created_at.isoformat(),
                    "stack_trace": e.stack_trace[:2000] if e.stack_trace else None,
                }
                for e in errors
            ],
            "step_history": steps,
        }


# =============================================================================
# Global Error Collector (for non-session contexts)
# =============================================================================


class GlobalErrorCollector:
    """Global error collector that works without an active session.

    Useful for logging errors in contexts where a database session
    is not available (e.g., LLM providers, tools outside of activities).

    Uses a background queue to batch-write errors to the database.
    """

    def __init__(self) -> None:
        """Initialize the global collector."""
        self._queue: list[ErrorLogEntry] = []
        self._lock = asyncio.Lock()

    async def log_error(
        self,
        run_id: str,
        error_category: ErrorCategory | str,
        error_type: str,
        error_message: str,
        source: LogSource | str = LogSource.ACTIVITY,
        step_id: str | None = None,
        stack_trace: str | None = None,
        context: dict[str, Any] | None = None,
        attempt: int = 1,
    ) -> None:
        """Queue an error for logging.

        Args:
            run_id: Run identifier
            error_category: Classification for retry decisions
            error_type: Exception class name
            error_message: Human-readable error message
            source: Error source
            step_id: Step identifier (optional)
            stack_trace: Full stack trace (optional)
            context: Additional context
            attempt: Which attempt number failed
        """
        category = (
            error_category if isinstance(error_category, ErrorCategory)
            else ErrorCategory(error_category)
        )
        src = source if isinstance(source, LogSource) else LogSource(source)

        entry = ErrorLogEntry(
            run_id=run_id,
            step_id=step_id,
            source=src,
            error_category=category,
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            context=context,
            attempt=attempt,
        )

        async with self._lock:
            self._queue.append(entry)

    async def log_exception(
        self,
        run_id: str,
        exception: Exception,
        error_category: ErrorCategory | str,
        source: LogSource | str = LogSource.ACTIVITY,
        step_id: str | None = None,
        context: dict[str, Any] | None = None,
        attempt: int = 1,
    ) -> None:
        """Queue an exception for logging."""
        stack_trace = "".join(
            traceback.format_exception(type(exception), exception, exception.__traceback__)
        )

        await self.log_error(
            run_id=run_id,
            error_category=error_category,
            error_type=type(exception).__name__,
            error_message=str(exception),
            source=source,
            step_id=step_id,
            stack_trace=stack_trace,
            context=context,
            attempt=attempt,
        )

    async def flush(self, tenant_id: str) -> int:
        """Flush queued errors to the database.

        Args:
            tenant_id: Tenant identifier for database connection

        Returns:
            Number of errors flushed
        """
        async with self._lock:
            if not self._queue:
                return 0

            entries = self._queue.copy()
            self._queue.clear()

        try:
            from apps.api.db.tenant import get_tenant_manager

            manager = get_tenant_manager()
            async with manager.get_session(tenant_id) as session:
                collector = ErrorCollector(session)
                for entry in entries:
                    await collector.log_error(
                        run_id=entry.run_id,
                        step_id=entry.step_id,
                        source=entry.source,
                        error_category=entry.error_category,
                        error_type=entry.error_type,
                        error_message=entry.error_message,
                        stack_trace=entry.stack_trace,
                        context=entry.context,
                        attempt=entry.attempt,
                    )

            return len(entries)

        except Exception as e:
            # Put entries back in queue on failure
            logger.error(f"Failed to flush error logs: {e}")
            async with self._lock:
                self._queue.extend(entries)
            return 0

    def pending_count(self) -> int:
        """Get count of pending errors."""
        return len(self._queue)


# Global instance
_global_collector: GlobalErrorCollector | None = None


def get_global_collector() -> GlobalErrorCollector:
    """Get the global error collector instance."""
    global _global_collector
    if _global_collector is None:
        _global_collector = GlobalErrorCollector()
    return _global_collector


async def collect_error(
    run_id: str,
    error_category: ErrorCategory | str,
    error_type: str,
    error_message: str,
    source: LogSource | str = LogSource.ACTIVITY,
    step_id: str | None = None,
    stack_trace: str | None = None,
    context: dict[str, Any] | None = None,
    attempt: int = 1,
) -> None:
    """Convenience function to log an error via the global collector.

    Use this when you don't have a database session available.
    Remember to call flush() periodically or at activity completion.
    """
    collector = get_global_collector()
    await collector.log_error(
        run_id=run_id,
        error_category=error_category,
        error_type=error_type,
        error_message=error_message,
        source=source,
        step_id=step_id,
        stack_trace=stack_trace,
        context=context,
        attempt=attempt,
    )


async def collect_exception(
    run_id: str,
    exception: Exception,
    error_category: ErrorCategory | str,
    source: LogSource | str = LogSource.ACTIVITY,
    step_id: str | None = None,
    context: dict[str, Any] | None = None,
    attempt: int = 1,
) -> None:
    """Convenience function to log an exception via the global collector."""
    collector = get_global_collector()
    await collector.log_exception(
        run_id=run_id,
        exception=exception,
        error_category=error_category,
        source=source,
        step_id=step_id,
        context=context,
        attempt=attempt,
    )
