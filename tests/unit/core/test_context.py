"""Tests for execution context."""

from datetime import datetime

from apps.api.core.context import ExecutionContext


class TestExecutionContext:
    """Tests for ExecutionContext."""

    def test_create_context(self) -> None:
        """Test creating an execution context."""
        ctx = ExecutionContext(
            run_id="run-123",
            step_id="step_1",
            attempt=1,
            tenant_id="tenant-abc",
            started_at=datetime(2024, 1, 1, 12, 0, 0),
            timeout_seconds=300,
        )
        assert ctx.run_id == "run-123"
        assert ctx.step_id == "step_1"
        assert ctx.attempt == 1
        assert ctx.tenant_id == "tenant-abc"
        assert ctx.timeout_seconds == 300

    def test_to_dict(self) -> None:
        """Test serialization to dictionary."""
        ctx = ExecutionContext(
            run_id="run-123",
            step_id="step_1",
            attempt=1,
            tenant_id="tenant-abc",
            started_at=datetime(2024, 1, 1, 12, 0, 0),
            timeout_seconds=300,
            config={"model": "claude-3"},
        )
        data = ctx.to_dict()
        assert data["run_id"] == "run-123"
        assert data["step_id"] == "step_1"
        assert data["started_at"] == "2024-01-01T12:00:00"
        assert data["config"]["model"] == "claude-3"

    def test_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {
            "run_id": "run-123",
            "step_id": "step_1",
            "attempt": 2,
            "tenant_id": "tenant-abc",
            "started_at": "2024-01-01T12:00:00",
            "timeout_seconds": 300,
            "config": {"key": "value"},
        }
        ctx = ExecutionContext.from_dict(data)
        assert ctx.run_id == "run-123"
        assert ctx.attempt == 2
        assert ctx.config["key"] == "value"

    def test_is_first_attempt(self) -> None:
        """Test first attempt check."""
        ctx1 = ExecutionContext(
            run_id="run-123",
            step_id="step_1",
            attempt=1,
            tenant_id="tenant-abc",
            started_at=datetime.now(),
            timeout_seconds=300,
        )
        assert ctx1.is_first_attempt() is True

        ctx2 = ExecutionContext(
            run_id="run-123",
            step_id="step_1",
            attempt=2,
            tenant_id="tenant-abc",
            started_at=datetime.now(),
            timeout_seconds=300,
        )
        assert ctx2.is_first_attempt() is False

    def test_next_attempt(self) -> None:
        """Test creating context for next retry."""
        ctx1 = ExecutionContext(
            run_id="run-123",
            step_id="step_1",
            attempt=1,
            tenant_id="tenant-abc",
            started_at=datetime(2024, 1, 1, 12, 0, 0),
            timeout_seconds=300,
            config={"preserve": "this"},
        )
        ctx2 = ctx1.next_attempt()

        assert ctx2.run_id == ctx1.run_id
        assert ctx2.step_id == ctx1.step_id
        assert ctx2.attempt == 2
        assert ctx2.tenant_id == ctx1.tenant_id
        assert ctx2.timeout_seconds == ctx1.timeout_seconds
        assert ctx2.config == ctx1.config
        assert ctx2.started_at > ctx1.started_at
