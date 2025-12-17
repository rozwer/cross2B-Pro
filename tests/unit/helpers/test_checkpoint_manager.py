"""Tests for CheckpointManager class."""

import json

import pytest
from unittest.mock import AsyncMock, MagicMock

from apps.worker.helpers import CheckpointManager


class TestCheckpointManager:
    """CheckpointManager tests."""

    @pytest.fixture
    def mock_store(self):
        """Mock store."""
        store = MagicMock()
        store.put = AsyncMock()
        store.get_by_path = AsyncMock(return_value=None)
        store.list_run_artifacts = AsyncMock(return_value=[])
        store.delete = AsyncMock()
        return store

    @pytest.fixture
    def manager(self, mock_store):
        """CheckpointManager instance."""
        return CheckpointManager(mock_store)

    @pytest.mark.asyncio
    async def test_save(self, manager, mock_store):
        """Save checkpoint."""
        path = await manager.save(
            tenant_id="t1",
            run_id="r1",
            step_id="step5",
            phase="queries_generated",
            data={"queries": ["q1", "q2"]},
        )

        assert "checkpoint" in path
        assert mock_store.put.called

    @pytest.mark.asyncio
    async def test_save_with_digest(self, manager, mock_store):
        """Save with input digest."""
        path = await manager.save(
            tenant_id="t1",
            run_id="r1",
            step_id="step5",
            phase="queries_generated",
            data={"queries": ["q1"]},
            input_digest="abc123",
        )

        assert "checkpoint" in path
        # Verify put was called with content containing digest
        call_args = mock_store.put.call_args
        content = call_args.kwargs.get("content") or call_args[1].get("content")
        assert b"abc123" in content

    @pytest.mark.asyncio
    async def test_load_not_found(self, manager, mock_store):
        """Checkpoint not found."""
        mock_store.get_by_path.return_value = None

        result = await manager.load(
            tenant_id="t1",
            run_id="r1",
            step_id="step5",
            phase="queries_generated",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_load_found(self, manager, mock_store):
        """Checkpoint found."""
        checkpoint = {
            "_metadata": {"phase": "queries_generated"},
            "data": {"queries": ["q1"]},
        }
        mock_store.get_by_path.return_value = json.dumps(checkpoint).encode()

        result = await manager.load(
            tenant_id="t1",
            run_id="r1",
            step_id="step5",
            phase="queries_generated",
        )

        assert result == {"queries": ["q1"]}

    @pytest.mark.asyncio
    async def test_load_digest_mismatch(self, manager, mock_store):
        """Digest mismatch returns None."""
        checkpoint = {
            "_metadata": {
                "phase": "queries_generated",
                "input_digest": "old_digest",
            },
            "data": {"queries": ["q1"]},
        }
        mock_store.get_by_path.return_value = json.dumps(checkpoint).encode()

        result = await manager.load(
            tenant_id="t1",
            run_id="r1",
            step_id="step5",
            phase="queries_generated",
            input_digest="new_digest",
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_load_digest_match(self, manager, mock_store):
        """Digest match returns data."""
        checkpoint = {
            "_metadata": {
                "phase": "queries_generated",
                "input_digest": "same_digest",
            },
            "data": {"queries": ["q1"]},
        }
        mock_store.get_by_path.return_value = json.dumps(checkpoint).encode()

        result = await manager.load(
            tenant_id="t1",
            run_id="r1",
            step_id="step5",
            phase="queries_generated",
            input_digest="same_digest",
        )

        assert result == {"queries": ["q1"]}

    @pytest.mark.asyncio
    async def test_load_no_digest_required(self, manager, mock_store):
        """No digest required, returns data regardless of stored digest."""
        checkpoint = {
            "_metadata": {
                "phase": "queries_generated",
                "input_digest": "some_digest",
            },
            "data": {"queries": ["q1"]},
        }
        mock_store.get_by_path.return_value = json.dumps(checkpoint).encode()

        result = await manager.load(
            tenant_id="t1",
            run_id="r1",
            step_id="step5",
            phase="queries_generated",
            # No input_digest specified
        )

        assert result == {"queries": ["q1"]}

    @pytest.mark.asyncio
    async def test_exists_true(self, manager, mock_store):
        """Checkpoint exists."""
        mock_store.get_by_path.return_value = b'{"data": {}}'

        result = await manager.exists(
            tenant_id="t1",
            run_id="r1",
            step_id="step5",
            phase="queries_generated",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, manager, mock_store):
        """Checkpoint does not exist."""
        mock_store.get_by_path.return_value = None

        result = await manager.exists(
            tenant_id="t1",
            run_id="r1",
            step_id="step5",
            phase="queries_generated",
        )

        assert result is False

    def test_build_path(self, manager):
        """Path construction."""
        path = manager.build_path("t1", "r1", "step5", "queries_generated")

        assert path == "t1/r1/step5/checkpoint/queries_generated.json"

    def test_compute_digest(self):
        """Digest computation."""
        digest1 = CheckpointManager.compute_digest({"key": "value"})
        digest2 = CheckpointManager.compute_digest({"key": "value"})
        digest3 = CheckpointManager.compute_digest({"key": "different"})

        assert digest1 == digest2
        assert digest1 != digest3

    def test_compute_digest_deterministic(self):
        """Digest is deterministic regardless of dict order."""
        digest1 = CheckpointManager.compute_digest({"a": 1, "b": 2})
        digest2 = CheckpointManager.compute_digest({"b": 2, "a": 1})

        assert digest1 == digest2

    @pytest.mark.asyncio
    async def test_load_invalid_json(self, manager, mock_store):
        """Invalid JSON returns None."""
        mock_store.get_by_path.return_value = b"not valid json"

        result = await manager.load(
            tenant_id="t1",
            run_id="r1",
            step_id="step5",
            phase="queries_generated",
        )

        assert result is None
