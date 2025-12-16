"""Tests for event emission."""

from datetime import datetime

from apps.api.observability.events import Event, EventEmitter, EventType


class TestEventType:
    """Tests for EventType enum."""

    def test_step_events(self) -> None:
        """Test step lifecycle event values."""
        assert EventType.STEP_STARTED.value == "step.started"
        assert EventType.STEP_SUCCEEDED.value == "step.succeeded"
        assert EventType.STEP_FAILED.value == "step.failed"
        assert EventType.STEP_RETRYING.value == "step.retrying"

    def test_run_events(self) -> None:
        """Test run lifecycle event values."""
        assert EventType.RUN_CREATED.value == "run.created"
        assert EventType.RUN_COMPLETED.value == "run.completed"
        assert EventType.RUN_FAILED.value == "run.failed"


class TestEvent:
    """Tests for Event model."""

    def test_create_event(self) -> None:
        """Test creating an event."""
        event = Event(
            event_type=EventType.STEP_STARTED,
            run_id="run-123",
            step_id="step_1",
            tenant_id="tenant-abc",
            payload={"attempt": 1},
        )
        assert event.event_type == EventType.STEP_STARTED
        assert event.run_id == "run-123"
        assert event.step_id == "step_1"
        assert event.tenant_id == "tenant-abc"
        assert event.payload["attempt"] == 1
        assert event.timestamp is not None

    def test_to_audit_dict_with_step(self) -> None:
        """Test conversion to audit log format with step."""
        event = Event(
            event_type=EventType.STEP_SUCCEEDED,
            run_id="run-123",
            step_id="step_1",
            tenant_id="tenant-abc",
            payload={"duration_ms": 1500},
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
        )
        audit = event.to_audit_dict()
        assert audit["action"] == "step.succeeded"
        assert audit["resource_type"] == "step"
        assert audit["resource_id"] == "step_1"
        assert audit["details"]["run_id"] == "run-123"

    def test_to_audit_dict_without_step(self) -> None:
        """Test conversion to audit log format without step."""
        event = Event(
            event_type=EventType.RUN_CREATED,
            run_id="run-123",
            tenant_id="tenant-abc",
            payload={},
        )
        audit = event.to_audit_dict()
        assert audit["resource_type"] == "run"
        assert audit["resource_id"] == "run-123"


class TestEventEmitter:
    """Tests for EventEmitter."""

    def test_emit_step_started(self) -> None:
        """Test creating step started event."""
        emitter = EventEmitter()
        event = emitter.emit_step_started(
            run_id="run-123",
            step_id="step_1",
            tenant_id="tenant-abc",
            attempt=2,
        )
        assert event.event_type == EventType.STEP_STARTED
        assert event.payload["attempt"] == 2

    def test_emit_step_succeeded(self) -> None:
        """Test creating step succeeded event."""
        emitter = EventEmitter()
        event = emitter.emit_step_succeeded(
            run_id="run-123",
            step_id="step_1",
            tenant_id="tenant-abc",
            duration_ms=1500,
        )
        assert event.event_type == EventType.STEP_SUCCEEDED
        assert event.payload["duration_ms"] == 1500

    def test_emit_step_failed(self) -> None:
        """Test creating step failed event."""
        emitter = EventEmitter()
        event = emitter.emit_step_failed(
            run_id="run-123",
            step_id="step_1",
            tenant_id="tenant-abc",
            error="API timeout",
            category="retryable",
        )
        assert event.event_type == EventType.STEP_FAILED
        assert event.payload["error"] == "API timeout"
        assert event.payload["category"] == "retryable"

    def test_emit_step_retrying(self) -> None:
        """Test creating step retrying event."""
        emitter = EventEmitter()
        event = emitter.emit_step_retrying(
            run_id="run-123",
            step_id="step_1",
            tenant_id="tenant-abc",
            attempt=2,
            reason="Rate limit exceeded",
        )
        assert event.event_type == EventType.STEP_RETRYING
        assert event.payload["attempt"] == 2
        assert event.payload["reason"] == "Rate limit exceeded"

    def test_buffer_events_without_session(self) -> None:
        """Test events are buffered when no session available."""
        emitter = EventEmitter()
        event = Event(
            event_type=EventType.STEP_STARTED,
            run_id="run-123",
            step_id="step_1",
            tenant_id="tenant-abc",
        )

        # Emit without session - should buffer
        import asyncio

        asyncio.get_event_loop().run_until_complete(emitter.emit(event))
        assert len(emitter._buffer) == 1
