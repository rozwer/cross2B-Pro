"""Tests for ArtifactStore."""

import hashlib
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from apps.api.storage.artifact_store import (
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    ArtifactStore,
)
from apps.api.storage.schemas import ArtifactRef


class TestArtifactStore:
    """Tests for ArtifactStore."""

    def test_compute_digest(self) -> None:
        """Test SHA256 digest computation."""
        content = b"Hello, World!"
        expected = hashlib.sha256(content).hexdigest()
        assert ArtifactStore._compute_digest(content) == expected

    def test_build_path(self) -> None:
        """Test path building convention."""
        store = ArtifactStore()
        path = store.build_path(
            tenant_id="tenant-abc",
            run_id="run-123",
            step="step_1",
            filename="output.json",
        )
        assert path == "storage/tenant-abc/run-123/step_1/output.json"

    def test_build_path_default_filename(self) -> None:
        """Test path building with default filename."""
        store = ArtifactStore()
        path = store.build_path(
            tenant_id="tenant-abc",
            run_id="run-123",
            step="step_1",
        )
        assert path.endswith("output.json")

    @pytest.mark.asyncio
    async def test_put_creates_artifact_ref(self) -> None:
        """Test put returns correct ArtifactRef."""
        store = ArtifactStore()

        # Mock MinIO client
        mock_client = MagicMock()
        mock_client.bucket_exists.return_value = True
        store._client = mock_client

        content = b'{"key": "value"}'
        path = "storage/tenant-abc/run-123/step_1/output.json"

        ref = await store.put(content, path)

        assert ref.path == path
        assert ref.digest == ArtifactStore._compute_digest(content)
        assert ref.size_bytes == len(content)
        assert ref.content_type == "application/json"
        mock_client.put_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_verifies_digest(self) -> None:
        """Test get verifies content digest."""
        store = ArtifactStore()

        content = b'{"key": "value"}'
        ref = ArtifactRef(
            path="storage/tenant-abc/run-123/step_1/output.json",
            digest=ArtifactStore._compute_digest(content),
            size_bytes=len(content),
            created_at=datetime.now(),
        )

        # Mock MinIO client to return correct content
        mock_response = MagicMock()
        mock_response.read.return_value = content
        mock_client = MagicMock()
        mock_client.get_object.return_value = mock_response
        store._client = mock_client

        result = await store.get(ref)
        assert result == content

    @pytest.mark.asyncio
    async def test_get_raises_on_digest_mismatch(self) -> None:
        """Test get raises ArtifactIntegrityError on digest mismatch."""
        store = ArtifactStore()

        ref = ArtifactRef(
            path="storage/tenant-abc/run-123/step_1/output.json",
            digest="expected_digest_that_wont_match",
            size_bytes=100,
            created_at=datetime.now(),
        )

        # Mock MinIO client to return different content
        mock_response = MagicMock()
        mock_response.read.return_value = b"different content"
        mock_client = MagicMock()
        mock_client.get_object.return_value = mock_response
        store._client = mock_client

        with pytest.raises(ArtifactIntegrityError, match="Digest mismatch"):
            await store.get(ref)

    @pytest.mark.asyncio
    async def test_get_without_verification(self) -> None:
        """Test get can skip digest verification."""
        store = ArtifactStore()

        content = b"some content"
        ref = ArtifactRef(
            path="storage/tenant-abc/run-123/step_1/output.json",
            digest="wrong_digest",
            size_bytes=len(content),
            created_at=datetime.now(),
        )

        # Mock MinIO client
        mock_response = MagicMock()
        mock_response.read.return_value = content
        mock_client = MagicMock()
        mock_client.get_object.return_value = mock_response
        store._client = mock_client

        # Should not raise with verify=False
        result = await store.get(ref, verify=False)
        assert result == content

    @pytest.mark.asyncio
    async def test_exists_checks_size(self) -> None:
        """Test exists checks size as quick verification."""
        store = ArtifactStore()

        ref = ArtifactRef(
            path="storage/tenant-abc/run-123/step_1/output.json",
            digest="abc123",
            size_bytes=1024,
            created_at=datetime.now(),
        )

        # Mock MinIO client with matching size
        mock_stat = MagicMock()
        mock_stat.size = 1024
        mock_client = MagicMock()
        mock_client.stat_object.return_value = mock_stat
        store._client = mock_client

        result = await store.exists(ref)
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_on_size_mismatch(self) -> None:
        """Test exists returns False on size mismatch."""
        store = ArtifactStore()

        ref = ArtifactRef(
            path="storage/tenant-abc/run-123/step_1/output.json",
            digest="abc123",
            size_bytes=1024,
            created_at=datetime.now(),
        )

        # Mock MinIO client with different size
        mock_stat = MagicMock()
        mock_stat.size = 2048
        mock_client = MagicMock()
        mock_client.stat_object.return_value = mock_stat
        store._client = mock_client

        result = await store.exists(ref)
        assert result is False
