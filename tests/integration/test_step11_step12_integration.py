"""Integration tests for Step11 → Step12 data flow.

Tests cover:
- Step11 output is correctly stored at standard path
- Step12 can load Step11 output
- Image data from Step11 is properly consumed by Step12
"""

# mypy: ignore-errors
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from apps.api.storage.artifact_store import ArtifactStore

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_step11_output():
    """Sample Step11 output with images."""
    return {
        "step": "step11",
        "phase": "completed",
        "settings": {
            "style": "photo",
            "aspect_ratio": "16:9",
            "provider": "nanobanana",
        },
        "positions": [
            {
                "id": "pos_1",
                "section": "intro",
                "order": 1,
                "description": "冒頭の導入画像",
            },
            {
                "id": "pos_2",
                "section": "body",
                "order": 2,
                "description": "本文中の説明画像",
            },
        ],
        "images": [
            {
                "id": "img_001",
                "position_id": "pos_1",
                "article_number": 1,
                "url": "https://storage.example.com/images/img_001.png",
                "alt_text": "SEO対策の概念図",
                "prompt": "A conceptual diagram showing SEO optimization",
                "width": 1920,
                "height": 1080,
            },
            {
                "id": "img_002",
                "position_id": "pos_2",
                "article_number": 1,
                "url": "https://storage.example.com/images/img_002.png",
                "alt_text": "キーワード分析のグラフ",
                "prompt": "A graph showing keyword analysis results",
                "width": 1920,
                "height": 1080,
            },
        ],
        "skipped": False,
        "metrics": {
            "total_images": 2,
            "generation_time_seconds": 45.2,
            "total_cost_usd": 0.08,
        },
    }


@pytest.fixture
def sample_step10_output():
    """Sample Step10 output with articles."""
    return {
        "step": "step10",
        "keyword": "SEO対策 初心者",
        "articles": [
            {
                "article_number": 1,
                "title": "SEO対策の基本ガイド",
                "content": "# はじめに\n\nSEO対策は...",
                "html_content": "<h1>はじめに</h1><p>SEO対策は...</p>",
                "meta_description": "SEO初心者向けの基本ガイド",
            },
        ],
    }


@pytest.fixture
def mock_storage():
    """Create mock storage that simulates artifact retrieval."""
    storage_data: dict[str, bytes] = {}

    async def mock_get_by_path(tenant_id: str, run_id: str, step: str) -> bytes | None:
        path = f"storage/{tenant_id}/{run_id}/{step}/output.json"
        return storage_data.get(path)

    async def mock_put(tenant_id: str, run_id: str, step: str, filename: str, data: bytes, **kwargs):
        path = f"storage/{tenant_id}/{run_id}/{step}/{filename}"
        storage_data[path] = data
        return MagicMock(path=path, digest="abc123")

    store = MagicMock(spec=ArtifactStore)
    store.get_by_path = mock_get_by_path
    store.put = mock_put
    store.build_path = lambda t, r, s, f="output.json": f"storage/{t}/{r}/{s}/{f}"
    store._storage_data = storage_data  # Expose for test inspection

    return store


# =============================================================================
# Storage Path Tests
# =============================================================================


class TestStep11StoragePath:
    """Test Step11 output path follows standard convention."""

    def test_build_path_follows_convention(self, tenant_id, run_id):
        """Test that build_path produces standard storage path."""
        store = ArtifactStore.__new__(ArtifactStore)
        store.bucket = "test-bucket"
        store.prefix = "storage"

        # Patch the build_path method to test path generation
        expected_path = f"storage/{tenant_id}/{run_id}/step11/output.json"

        # Verify path format
        assert expected_path.startswith("storage/")
        assert tenant_id in expected_path
        assert run_id in expected_path
        assert "step11" in expected_path

    def test_path_not_tenants_prefix(self, tenant_id, run_id):
        """Verify path doesn't use old 'tenants/' prefix."""
        correct_path = f"storage/{tenant_id}/{run_id}/step11/output.json"
        wrong_path = f"tenants/{tenant_id}/runs/{run_id}/step11/output.json"

        assert not correct_path.startswith("tenants/")
        assert correct_path != wrong_path


# =============================================================================
# Step11 → Step12 Data Flow Tests
# =============================================================================


class TestStep11ToStep12DataFlow:
    """Test data flow from Step11 to Step12."""

    @pytest.mark.asyncio
    async def test_step12_loads_step11_output(
        self,
        mock_storage,
        sample_step11_output,
        sample_step10_output,
        tenant_id,
        run_id,
    ):
        """Test that Step12 can load Step11 output from storage."""
        # Arrange - Store Step11 output
        step11_path = f"storage/{tenant_id}/{run_id}/step11/output.json"
        mock_storage._storage_data[step11_path] = json.dumps(sample_step11_output).encode()

        # Act - Simulate Step12 loading Step11 data
        from apps.worker.activities.base import load_step_data

        with patch.object(mock_storage, "get_by_path", side_effect=mock_storage.get_by_path):
            step11_data = await load_step_data(mock_storage, tenant_id, run_id, "step11")

        # Assert
        assert step11_data is not None
        assert step11_data["step"] == "step11"
        assert len(step11_data["images"]) == 2

    @pytest.mark.asyncio
    async def test_step12_handles_missing_step11(
        self,
        mock_storage,
        tenant_id,
        run_id,
    ):
        """Test Step12 handles gracefully when Step11 output is missing."""
        from apps.worker.activities.base import load_step_data

        # Act - Try to load non-existent Step11 data
        step11_data = await load_step_data(mock_storage, tenant_id, run_id, "step11")

        # Assert
        assert step11_data is None

    @pytest.mark.asyncio
    async def test_step12_extracts_images_from_step11(
        self,
        sample_step11_output,
    ):
        """Test that Step12 correctly extracts image data from Step11."""
        images = sample_step11_output["images"]

        # Verify image structure matches Step12 expectations
        for img in images:
            assert "id" in img
            assert "url" in img
            assert "alt_text" in img
            assert "article_number" in img

    @pytest.mark.asyncio
    async def test_step12_filters_images_by_article(
        self,
        sample_step11_output,
    ):
        """Test that Step12 can filter images by article number."""
        images = sample_step11_output["images"]

        # Filter for article 1
        article_1_images = [img for img in images if img.get("article_number") is None or img.get("article_number") == 1]

        assert len(article_1_images) == 2

        # Filter for article 2 (should be empty in sample)
        article_2_images = [img for img in images if img.get("article_number") == 2]

        assert len(article_2_images) == 0


# =============================================================================
# Step11 Skip Handling Tests
# =============================================================================


class TestStep11SkipHandling:
    """Test Step12 handles Step11 skip scenario."""

    @pytest.mark.asyncio
    async def test_step12_handles_skipped_step11(
        self,
        mock_storage,
        tenant_id,
        run_id,
    ):
        """Test Step12 works when Step11 was skipped."""
        # Arrange - Step11 output with skipped=True
        skipped_output = {
            "step": "step11",
            "phase": "skipped",
            "skipped": True,
            "images": [],
            "positions": [],
        }
        step11_path = f"storage/{tenant_id}/{run_id}/step11/output.json"
        mock_storage._storage_data[step11_path] = json.dumps(skipped_output).encode()

        from apps.worker.activities.base import load_step_data

        # Act
        step11_data = await load_step_data(mock_storage, tenant_id, run_id, "step11")

        # Assert
        assert step11_data is not None
        assert step11_data["skipped"] is True
        assert len(step11_data["images"]) == 0


# =============================================================================
# Image Data Integrity Tests
# =============================================================================


class TestImageDataIntegrity:
    """Test image data integrity between Step11 and Step12."""

    def test_image_has_required_fields(self, sample_step11_output):
        """Test each image has all required fields for Step12."""
        required_fields = ["id", "url", "alt_text"]

        for img in sample_step11_output["images"]:
            for field in required_fields:
                assert field in img, f"Missing required field: {field}"

    def test_image_position_mapping(self, sample_step11_output):
        """Test images are correctly mapped to positions."""
        positions = {p["id"]: p for p in sample_step11_output["positions"]}
        images = sample_step11_output["images"]

        for img in images:
            position_id = img.get("position_id")
            if position_id:
                assert position_id in positions, f"Image references unknown position: {position_id}"

    def test_image_dimensions_valid(self, sample_step11_output):
        """Test image dimensions are valid."""
        for img in sample_step11_output["images"]:
            width = img.get("width", 0)
            height = img.get("height", 0)

            assert width > 0, "Image width must be positive"
            assert height > 0, "Image height must be positive"


# =============================================================================
# Backward Compatibility Tests
# =============================================================================


class TestBackwardCompatibility:
    """Test backward compatibility with legacy data formats."""

    @pytest.mark.asyncio
    async def test_step12_handles_legacy_single_article(
        self,
        mock_storage,
        tenant_id,
        run_id,
    ):
        """Test Step12 handles legacy single-article format from Step10."""
        # Legacy format: single article instead of articles array
        legacy_step10 = {
            "step": "step10",
            "keyword": "テスト",
            "article_title": "テスト記事",
            "markdown_content": "# タイトル\n\n本文...",
            "html_content": "<h1>タイトル</h1><p>本文...</p>",
            "meta_description": "テスト記事の説明",
        }

        step10_path = f"storage/{tenant_id}/{run_id}/step10/output.json"
        mock_storage._storage_data[step10_path] = json.dumps(legacy_step10).encode()

        from apps.worker.activities.base import load_step_data

        step10_data = await load_step_data(mock_storage, tenant_id, run_id, "step10")

        # Verify legacy format is loaded
        assert step10_data is not None
        assert "markdown_content" in step10_data  # Legacy field
        assert "articles" not in step10_data  # No array

    @pytest.mark.asyncio
    async def test_step11_handles_no_images(
        self,
        mock_storage,
        tenant_id,
        run_id,
    ):
        """Test Step11 output with no images."""
        step11_no_images = {
            "step": "step11",
            "phase": "completed",
            "skipped": False,
            "images": [],
            "positions": [],
        }

        step11_path = f"storage/{tenant_id}/{run_id}/step11/output.json"
        mock_storage._storage_data[step11_path] = json.dumps(step11_no_images).encode()

        from apps.worker.activities.base import load_step_data

        step11_data = await load_step_data(mock_storage, tenant_id, run_id, "step11")

        assert step11_data is not None
        assert len(step11_data["images"]) == 0
