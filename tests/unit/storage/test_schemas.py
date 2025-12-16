"""Tests for storage schemas."""

from datetime import datetime

import pytest

from apps.api.storage.schemas import ArtifactMetrics, ArtifactRef


class TestArtifactRef:
    """Tests for ArtifactRef model."""

    def test_create_artifact_ref(self) -> None:
        """Test creating an artifact reference."""
        ref = ArtifactRef(
            path="storage/tenant-abc/run-123/step_1/output.json",
            digest="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            content_type="application/json",
            size_bytes=2048,
            created_at=datetime(2024, 1, 1, 12, 0, 0),
        )
        assert ref.path == "storage/tenant-abc/run-123/step_1/output.json"
        assert len(ref.digest) == 64  # SHA256 hex
        assert ref.content_type == "application/json"
        assert ref.size_bytes == 2048

    def test_default_content_type(self) -> None:
        """Test default content type is application/json."""
        ref = ArtifactRef(
            path="storage/tenant-abc/run-123/step_1/output.json",
            digest="abc123",
            size_bytes=1024,
            created_at=datetime.now(),
        )
        assert ref.content_type == "application/json"

    def test_size_must_be_non_negative(self) -> None:
        """Test that size_bytes must be >= 0."""
        with pytest.raises(ValueError):
            ArtifactRef(
                path="storage/tenant-abc/run-123/step_1/output.json",
                digest="abc123",
                size_bytes=-1,
                created_at=datetime.now(),
            )

    def test_path_parsing(self) -> None:
        """Test path component extraction."""
        ref = ArtifactRef(
            path="storage/tenant-xyz/run-456/step_2/data.json",
            digest="def456",
            size_bytes=512,
            created_at=datetime.now(),
        )
        assert ref.get_tenant_id() == "tenant-xyz"
        assert ref.get_run_id() == "run-456"
        assert ref.get_step() == "step_2"

    def test_invalid_path_raises_error(self) -> None:
        """Test that invalid paths raise ValueError."""
        ref = ArtifactRef(
            path="invalid/path",
            digest="abc123",
            size_bytes=100,
            created_at=datetime.now(),
        )
        with pytest.raises(ValueError, match="Invalid artifact path"):
            ref.get_step()


class TestArtifactMetrics:
    """Tests for ArtifactMetrics model."""

    def test_create_metrics(self) -> None:
        """Test creating artifact metrics."""
        metrics = ArtifactMetrics(
            token_usage={"input": 100, "output": 500},
            char_count=2000,
            processing_time_ms=1500,
        )
        assert metrics.token_usage == {"input": 100, "output": 500}
        assert metrics.char_count == 2000
        assert metrics.processing_time_ms == 1500

    def test_optional_fields(self) -> None:
        """Test that all fields are optional."""
        metrics = ArtifactMetrics()
        assert metrics.token_usage is None
        assert metrics.char_count is None
        assert metrics.processing_time_ms is None
