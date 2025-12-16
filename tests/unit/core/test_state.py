"""Tests for GraphState."""

from datetime import datetime

from apps.api.core.errors import ErrorCategory, StepError
from apps.api.core.state import (
    GraphState,
    add_error,
    add_step_output,
    create_initial_state,
)
from apps.api.storage.schemas import ArtifactRef


class TestGraphState:
    """Tests for GraphState operations."""

    def test_create_initial_state(self) -> None:
        """Test creating initial state."""
        state = create_initial_state(
            run_id="run-123",
            tenant_id="tenant-abc",
        )
        assert state["run_id"] == "run-123"
        assert state["tenant_id"] == "tenant-abc"
        assert state["current_step"] == "init"
        assert state["status"] == "pending"
        assert state["step_outputs"] == {}
        assert state["validation_reports"] == []
        assert state["errors"] == []

    def test_create_initial_state_with_config(self) -> None:
        """Test creating initial state with config."""
        state = create_initial_state(
            run_id="run-123",
            tenant_id="tenant-abc",
            config={"model": "claude-3"},
            metadata={"user": "test"},
        )
        assert state["config"]["model"] == "claude-3"
        assert state["metadata"]["user"] == "test"

    def test_add_step_output(self) -> None:
        """Test adding step output (immutable)."""
        state = create_initial_state(run_id="run-123", tenant_id="tenant-abc")
        artifact = ArtifactRef(
            path="storage/tenant-abc/run-123/step_1/output.json",
            digest="abc123",
            content_type="application/json",
            size_bytes=1024,
            created_at=datetime.now(),
        )

        new_state = add_step_output(state, "step_1", artifact)

        # Original state unchanged
        assert "step_1" not in state.get("step_outputs", {})

        # New state has the output
        assert "step_1" in new_state["step_outputs"]
        assert new_state["step_outputs"]["step_1"].digest == "abc123"

    def test_add_error(self) -> None:
        """Test adding error (immutable)."""
        state = create_initial_state(run_id="run-123", tenant_id="tenant-abc")
        error = StepError(
            step_id="step_1",
            category=ErrorCategory.RETRYABLE,
            message="API timeout",
            occurred_at=datetime.now(),
            attempt=1,
        )

        new_state = add_error(state, error)

        # Original state unchanged
        assert len(state.get("errors", [])) == 0

        # New state has the error
        assert len(new_state["errors"]) == 1
        assert new_state["errors"][0].message == "API timeout"


class TestArtifactRef:
    """Tests for ArtifactRef path parsing."""

    def test_get_step(self) -> None:
        """Test extracting step from path."""
        ref = ArtifactRef(
            path="storage/tenant-abc/run-123/step_1/output.json",
            digest="abc123",
            content_type="application/json",
            size_bytes=1024,
            created_at=datetime.now(),
        )
        assert ref.get_step() == "step_1"

    def test_get_run_id(self) -> None:
        """Test extracting run_id from path."""
        ref = ArtifactRef(
            path="storage/tenant-abc/run-123/step_1/output.json",
            digest="abc123",
            content_type="application/json",
            size_bytes=1024,
            created_at=datetime.now(),
        )
        assert ref.get_run_id() == "run-123"

    def test_get_tenant_id(self) -> None:
        """Test extracting tenant_id from path."""
        ref = ArtifactRef(
            path="storage/tenant-abc/run-123/step_1/output.json",
            digest="abc123",
            content_type="application/json",
            size_bytes=1024,
            created_at=datetime.now(),
        )
        assert ref.get_tenant_id() == "tenant-abc"
