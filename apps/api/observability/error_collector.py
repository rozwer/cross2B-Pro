"""Error log collection service for run-scoped error tracking.

Collects all errors within a run session for:
- Debugging and tracing
- LLM-based failure diagnosis
- Recovery recommendations
"""

import traceback
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.errors import ErrorCategory
from apps.api.db.models import ErrorLog


class ErrorLogEntry(BaseModel):
    """Structured error log entry for collection."""

    run_id: str = Field(..., description="Run identifier")
    step_id: str | None = Field(default=None, description="Step identifier")
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

        error_log = ErrorLog(
            run_id=run_id,
            step_id=step_id,
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
        step_id: str | None = None,
        context: dict[str, Any] | None = None,
        attempt: int = 1,
    ) -> ErrorLog:
        """Log an exception with automatic stack trace extraction.

        Args:
            run_id: Run identifier
            exception: The exception to log
            error_category: Classification for retry decisions
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
            error_category=error_category,
            error_type=type(exception).__name__,
            error_message=str(exception),
            stack_trace=stack_trace,
            context=context,
            attempt=attempt,
        )

    async def get_errors_for_run(
        self,
        run_id: str,
        step_id: str | None = None,
        limit: int | None = None,
    ) -> list[ErrorLog]:
        """Get all error logs for a run.

        Args:
            run_id: Run identifier
            step_id: Filter by step (optional)
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

        if limit:
            stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_error_summary(self, run_id: str) -> dict[str, Any]:
        """Get a summary of errors for a run.

        Args:
            run_id: Run identifier

        Returns:
            Dictionary with error counts by category, step, and type
        """
        errors = await self.get_errors_for_run(run_id)

        summary: dict[str, Any] = {
            "total_errors": len(errors),
            "by_category": {},
            "by_step": {},
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

            # Count by type
            etype = error.error_type
            summary["by_type"][etype] = summary["by_type"].get(etype, 0) + 1

            # Timeline
            summary["timeline"].append(
                {
                    "step": error.step_id,
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
