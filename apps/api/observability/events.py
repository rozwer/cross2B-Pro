"""Event emission for workflow observability.

Events are persisted to DB for tracking and debugging.
All workflow state changes should emit events.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class EventType(str, Enum):
    """Types of workflow events."""

    # Step lifecycle
    STEP_STARTED = "step.started"
    STEP_SUCCEEDED = "step.succeeded"
    STEP_FAILED = "step.failed"
    STEP_RETRYING = "step.retrying"

    # Run lifecycle
    RUN_CREATED = "run.created"
    RUN_STARTED = "run.started"
    RUN_PAUSED = "run.paused"
    RUN_RESUMED = "run.resumed"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"

    # Repair actions
    REPAIR_APPLIED = "repair.applied"
    REPAIR_FAILED = "repair.failed"

    # Validation
    VALIDATION_PASSED = "validation.passed"
    VALIDATION_FAILED = "validation.failed"

    # LLM operations
    LLM_REQUEST_SENT = "llm.request_sent"
    LLM_RESPONSE_RECEIVED = "llm.response_received"
    LLM_ERROR = "llm.error"


class Event(BaseModel):
    """Structured event for workflow observability."""

    event_type: EventType = Field(..., description="Type of the event")
    run_id: str = Field(..., description="Run identifier")
    step_id: str | None = Field(default=None, description="Step identifier (if applicable)")
    tenant_id: str = Field(..., description="Tenant identifier")
    payload: dict[str, Any] = Field(default_factory=dict, description="Event-specific data")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the event occurred",
    )

    def to_audit_dict(self) -> dict[str, Any]:
        """Convert to audit log format."""
        return {
            "action": self.event_type.value,
            "resource_type": "run" if self.step_id is None else "step",
            "resource_id": self.step_id or self.run_id,
            "details": {
                "run_id": self.run_id,
                "tenant_id": self.tenant_id,
                "payload": self.payload,
                "timestamp": self.timestamp.isoformat(),
            },
        }


class EventEmitter:
    """Emits events to persistent storage.

    Events are stored in the audit_logs table for traceability.
    """

    def __init__(self, session_factory: Any | None = None) -> None:
        """Initialize event emitter.

        Args:
            session_factory: Async session factory for DB access
        """
        self._session_factory = session_factory
        self._buffer: list[Event] = []

    async def emit(
        self,
        event: Event,
        session: AsyncSession | None = None,
    ) -> None:
        """Emit an event to persistent storage.

        Args:
            event: Event to emit
            session: Optional existing session (uses session_factory if not provided)
        """
        if session:
            await self._persist_event(event, session)
        elif self._session_factory:
            async with self._session_factory() as sess:
                await self._persist_event(event, sess)
                await sess.commit()
        else:
            # Buffer event if no session available
            self._buffer.append(event)

    async def _persist_event(self, event: Event, session: AsyncSession) -> None:
        """Persist event to audit_logs table."""
        audit_data = event.to_audit_dict()
        await session.execute(
            text(
                """
                INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details)
                VALUES (:user_id, :action, :resource_type, :resource_id, :details)
            """
            ),
            {
                "user_id": "system",  # System-generated events
                "action": audit_data["action"],
                "resource_type": audit_data["resource_type"],
                "resource_id": audit_data["resource_id"],
                "details": audit_data["details"],
            },
        )

    async def flush_buffer(self, session: AsyncSession) -> int:
        """Flush buffered events to storage.

        Args:
            session: Database session

        Returns:
            Number of events flushed
        """
        count = len(self._buffer)
        for event in self._buffer:
            await self._persist_event(event, session)
        self._buffer.clear()
        return count

    def emit_step_started(
        self,
        run_id: str,
        step_id: str,
        tenant_id: str,
        attempt: int = 1,
        **payload: Any,
    ) -> Event:
        """Create a STEP_STARTED event."""
        return Event(
            event_type=EventType.STEP_STARTED,
            run_id=run_id,
            step_id=step_id,
            tenant_id=tenant_id,
            payload={"attempt": attempt, **payload},
        )

    def emit_step_succeeded(
        self,
        run_id: str,
        step_id: str,
        tenant_id: str,
        duration_ms: int | None = None,
        **payload: Any,
    ) -> Event:
        """Create a STEP_SUCCEEDED event."""
        return Event(
            event_type=EventType.STEP_SUCCEEDED,
            run_id=run_id,
            step_id=step_id,
            tenant_id=tenant_id,
            payload={"duration_ms": duration_ms, **payload} if duration_ms else payload,
        )

    def emit_step_failed(
        self,
        run_id: str,
        step_id: str,
        tenant_id: str,
        error: str,
        category: str,
        **payload: Any,
    ) -> Event:
        """Create a STEP_FAILED event."""
        return Event(
            event_type=EventType.STEP_FAILED,
            run_id=run_id,
            step_id=step_id,
            tenant_id=tenant_id,
            payload={"error": error, "category": category, **payload},
        )

    def emit_step_retrying(
        self,
        run_id: str,
        step_id: str,
        tenant_id: str,
        attempt: int,
        reason: str,
        **payload: Any,
    ) -> Event:
        """Create a STEP_RETRYING event."""
        return Event(
            event_type=EventType.STEP_RETRYING,
            run_id=run_id,
            step_id=step_id,
            tenant_id=tenant_id,
            payload={"attempt": attempt, "reason": reason, **payload},
        )
