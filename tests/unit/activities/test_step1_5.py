"""Unit tests for Step 1.5: Related Keyword Competitor Extraction."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.core.errors import ErrorCategory
from apps.worker.activities.base import ActivityError
from apps.worker.activities.step1_5 import (
    Step1_5RelatedKeywordExtraction,
    step1_5_related_keyword_extraction,
)

# Path for patching load_step_data (imported inside execute method)
LOAD_STEP_DATA_PATH = "apps.worker.activities.base.load_step_data"


class TestStep1_5RelatedKeywordExtraction:
    """Tests for Step1_5RelatedKeywordExtraction activity."""

    def test_step_id(self) -> None:
        """Test step_id property returns correct value."""
        activity = Step1_5RelatedKeywordExtraction()
        assert activity.step_id == "step1_5"

    @pytest.mark.asyncio
    async def test_execute_skip_when_no_related_keywords(self) -> None:
        """Test execution skips when related_keywords is empty."""
        activity = Step1_5RelatedKeywordExtraction()

        # Mock dependencies
        mock_ctx = MagicMock()
        mock_ctx.config = {"related_keywords": []}
        mock_ctx.tenant_id = "test_tenant"
        mock_ctx.run_id = "test_run"

        mock_state = MagicMock()

        with patch("apps.worker.activities.base.load_step_data") as mock_load:
            # Return empty step1 data, then empty step0 data
            mock_load.side_effect = [{}, {}]

            result = await activity.execute(mock_ctx, mock_state)

        assert result["step"] == "step1_5"
        assert result["skipped"] is True
        assert result["skip_reason"] == "no_related_keywords"
        assert result["related_keywords_analyzed"] == 0
        assert result["related_competitor_data"] == []

    @pytest.mark.asyncio
    async def test_execute_skip_when_related_keywords_missing(self) -> None:
        """Test execution skips when related_keywords key is missing."""
        activity = Step1_5RelatedKeywordExtraction()

        mock_ctx = MagicMock()
        mock_ctx.config = {}  # No related_keywords key
        mock_ctx.tenant_id = "test_tenant"
        mock_ctx.run_id = "test_run"

        mock_state = MagicMock()

        with patch("apps.worker.activities.base.load_step_data") as mock_load:
            # Return empty step1 data, then empty step0 data
            mock_load.side_effect = [{}, {}]

            result = await activity.execute(mock_ctx, mock_state)

        assert result["skipped"] is True
        assert result["skip_reason"] == "no_related_keywords"

    @pytest.mark.asyncio
    async def test_execute_with_related_keywords(self) -> None:
        """Test execution processes related keywords."""
        activity = Step1_5RelatedKeywordExtraction()

        # Mock checkpoint (no existing data)
        activity.checkpoint = MagicMock()
        activity.checkpoint.load = AsyncMock(return_value=None)
        activity.checkpoint.save = AsyncMock()

        # Mock context
        mock_ctx = MagicMock()
        mock_ctx.config = {"related_keywords": ["keyword1", "keyword2"]}
        mock_ctx.tenant_id = "test_tenant"
        mock_ctx.run_id = "test_run"

        mock_state = MagicMock()

        # Mock tools
        mock_serp_result = MagicMock()
        mock_serp_result.success = True
        mock_serp_result.data = {
            "results": [
                {"url": "https://example.com/1"},
                {"url": "https://example.com/2"},
            ]
        }

        mock_page_result = MagicMock()
        mock_page_result.success = True
        mock_page_result.data = {
            "title": "Test Page",
            "body_text": "Test content " * 50,  # Valid content length
            "headings": ["H2 Example"],
        }

        mock_serp_tool = MagicMock()
        mock_serp_tool.execute = AsyncMock(return_value=mock_serp_result)

        mock_page_tool = MagicMock()
        mock_page_tool.execute = AsyncMock(return_value=mock_page_result)

        with patch("apps.worker.activities.step1_5.ToolRegistry") as mock_registry:
            mock_registry_instance = MagicMock()
            mock_registry_instance.get = MagicMock(side_effect=lambda name: mock_serp_tool if name == "serp_fetch" else mock_page_tool)
            mock_registry.return_value = mock_registry_instance

            with patch("apps.worker.activities.step1_5.activity"):
                with patch("apps.worker.activities.base.load_step_data") as mock_load:
                    # Return empty step1 data, then empty step0 data
                    mock_load.side_effect = [{}, {}]

                    result = await activity.execute(mock_ctx, mock_state)

        assert result["step"] == "step1_5"
        assert result["skipped"] is False
        assert result["related_keywords_analyzed"] == 2
        assert len(result["related_competitor_data"]) == 2

    @pytest.mark.asyncio
    async def test_execute_limits_keywords(self) -> None:
        """Test execution limits to MAX_RELATED_KEYWORDS."""
        activity = Step1_5RelatedKeywordExtraction()

        # Create more keywords than the limit
        many_keywords = [f"keyword{i}" for i in range(10)]

        activity.checkpoint = MagicMock()
        activity.checkpoint.load = AsyncMock(return_value=None)
        activity.checkpoint.save = AsyncMock()

        mock_ctx = MagicMock()
        mock_ctx.config = {"related_keywords": many_keywords}
        mock_ctx.tenant_id = "test_tenant"
        mock_ctx.run_id = "test_run"

        mock_state = MagicMock()

        mock_serp_result = MagicMock()
        mock_serp_result.success = True
        mock_serp_result.data = {"results": []}

        mock_serp_tool = MagicMock()
        mock_serp_tool.execute = AsyncMock(return_value=mock_serp_result)

        with patch("apps.worker.activities.step1_5.ToolRegistry") as mock_registry:
            mock_registry_instance = MagicMock()
            mock_registry_instance.get = MagicMock(return_value=mock_serp_tool)
            mock_registry.return_value = mock_registry_instance

            with patch("apps.worker.activities.step1_5.activity"):
                with patch("apps.worker.activities.base.load_step_data") as mock_load:
                    # Return empty step1 data, then empty step0 data
                    mock_load.side_effect = [{}, {}]

                    result = await activity.execute(mock_ctx, mock_state)

        # Should only process MAX_RELATED_KEYWORDS (5)
        assert result["related_keywords_analyzed"] <= activity.MAX_RELATED_KEYWORDS

    @pytest.mark.asyncio
    async def test_execute_tool_not_found_raises_error(self) -> None:
        """Test execution raises error when required tool not found."""
        activity = Step1_5RelatedKeywordExtraction()

        activity.checkpoint = MagicMock()
        activity.checkpoint.load = AsyncMock(return_value=None)

        mock_ctx = MagicMock()
        mock_ctx.config = {"related_keywords": ["keyword1"]}
        mock_ctx.tenant_id = "test_tenant"
        mock_ctx.run_id = "test_run"

        mock_state = MagicMock()

        with patch("apps.worker.activities.step1_5.ToolRegistry") as mock_registry:
            mock_registry_instance = MagicMock()
            mock_registry_instance.get = MagicMock(side_effect=Exception("Tool not found"))
            mock_registry.return_value = mock_registry_instance

            with patch("apps.worker.activities.base.load_step_data") as mock_load:
                # Return empty step1 data, then empty step0 data
                mock_load.side_effect = [{}, {}]

                with pytest.raises(ActivityError) as exc_info:
                    await activity.execute(mock_ctx, mock_state)

                assert exc_info.value.category == ErrorCategory.NON_RETRYABLE
                assert "Required tool not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_checkpoint_resume(self) -> None:
        """Test execution resumes from checkpoint."""
        activity = Step1_5RelatedKeywordExtraction()

        # Mock checkpoint with existing data
        checkpoint_data = {
            "processed_keywords": ["keyword1"],
            "competitor_data": [
                {
                    "keyword": "keyword1",
                    "search_results_count": 5,
                    "competitors": [],
                    "fetch_success_count": 0,
                    "fetch_failed_count": 0,
                }
            ],
        }
        activity.checkpoint = MagicMock()
        activity.checkpoint.load = AsyncMock(return_value=checkpoint_data)
        activity.checkpoint.save = AsyncMock()

        mock_ctx = MagicMock()
        mock_ctx.config = {"related_keywords": ["keyword1", "keyword2"]}
        mock_ctx.tenant_id = "test_tenant"
        mock_ctx.run_id = "test_run"

        mock_state = MagicMock()

        mock_serp_result = MagicMock()
        mock_serp_result.success = True
        mock_serp_result.data = {"results": []}

        mock_serp_tool = MagicMock()
        mock_serp_tool.execute = AsyncMock(return_value=mock_serp_result)

        with patch("apps.worker.activities.step1_5.ToolRegistry") as mock_registry:
            mock_registry_instance = MagicMock()
            mock_registry_instance.get = MagicMock(return_value=mock_serp_tool)
            mock_registry.return_value = mock_registry_instance

            with patch("apps.worker.activities.step1_5.activity"):
                with patch("apps.worker.activities.base.load_step_data") as mock_load:
                    # Return empty step1 data, then empty step0 data
                    mock_load.side_effect = [{}, {}]

                    result = await activity.execute(mock_ctx, mock_state)

        # Should include data from checkpoint + newly processed
        assert result["related_keywords_analyzed"] == 2
        # SERP should only be called for keyword2 (keyword1 was in checkpoint)
        assert mock_serp_tool.execute.call_count == 1


class TestStep1_5Step1Deduplication:
    """Tests for step1 URL deduplication."""

    @pytest.mark.asyncio
    async def test_excludes_step1_duplicate_urls(self) -> None:
        """Test execution excludes URLs already fetched in step1."""
        activity = Step1_5RelatedKeywordExtraction()

        # Mock checkpoint (no existing data)
        activity.checkpoint = MagicMock()
        activity.checkpoint.load = AsyncMock(return_value=None)
        activity.checkpoint.save = AsyncMock()

        # Mock context
        mock_ctx = MagicMock()
        mock_ctx.config = {"related_keywords": ["keyword1"]}
        mock_ctx.tenant_id = "test_tenant"
        mock_ctx.run_id = "test_run"

        mock_state = MagicMock()

        # Mock step1 data with some URLs
        step1_data = {
            "competitors": [
                {"url": "https://example.com/1"},
                {"url": "https://example.com/2"},
            ]
        }

        # Mock SERP result returning URLs including duplicates from step1
        mock_serp_result = MagicMock()
        mock_serp_result.success = True
        mock_serp_result.data = {
            "results": [
                {"url": "https://example.com/1"},  # Duplicate from step1
                {"url": "https://example.com/3"},  # New URL
                {"url": "https://example.com/4"},  # New URL
            ]
        }

        mock_page_result = MagicMock()
        mock_page_result.success = True
        mock_page_result.data = {
            "title": "Test Page",
            "body_text": "Test content " * 50,
            "headings": [],
        }

        mock_serp_tool = MagicMock()
        mock_serp_tool.execute = AsyncMock(return_value=mock_serp_result)

        mock_page_tool = MagicMock()
        mock_page_tool.execute = AsyncMock(return_value=mock_page_result)

        with patch("apps.worker.activities.step1_5.ToolRegistry") as mock_registry:
            mock_registry_instance = MagicMock()
            mock_registry_instance.get = MagicMock(side_effect=lambda name: mock_serp_tool if name == "serp_fetch" else mock_page_tool)
            mock_registry.return_value = mock_registry_instance

            with patch("apps.worker.activities.step1_5.activity"):
                with patch("apps.worker.activities.base.load_step_data") as mock_load:
                    # Return step1 data, then step0 data (empty)
                    mock_load.side_effect = [step1_data, {}]

                    result = await activity.execute(mock_ctx, mock_state)

        # Should have processed 1 keyword
        assert result["related_keywords_analyzed"] == 1

        # page_tool should only be called for non-duplicate URLs (2 calls: /3 and /4)
        assert mock_page_tool.execute.call_count == 2

        # Check that skipped_duplicate_count is tracked
        kw_data = result["related_competitor_data"][0]
        assert kw_data["skipped_duplicate_count"] == 1  # /1 was skipped

    @pytest.mark.asyncio
    async def test_works_when_step1_empty(self) -> None:
        """Test execution works normally when step1 has no competitors."""
        activity = Step1_5RelatedKeywordExtraction()

        activity.checkpoint = MagicMock()
        activity.checkpoint.load = AsyncMock(return_value=None)
        activity.checkpoint.save = AsyncMock()

        mock_ctx = MagicMock()
        mock_ctx.config = {"related_keywords": ["keyword1"]}
        mock_ctx.tenant_id = "test_tenant"
        mock_ctx.run_id = "test_run"

        mock_state = MagicMock()

        # Mock SERP result
        mock_serp_result = MagicMock()
        mock_serp_result.success = True
        mock_serp_result.data = {
            "results": [
                {"url": "https://example.com/1"},
            ]
        }

        mock_page_result = MagicMock()
        mock_page_result.success = True
        mock_page_result.data = {
            "title": "Test Page",
            "body_text": "Test content " * 50,
            "headings": [],
        }

        mock_serp_tool = MagicMock()
        mock_serp_tool.execute = AsyncMock(return_value=mock_serp_result)

        mock_page_tool = MagicMock()
        mock_page_tool.execute = AsyncMock(return_value=mock_page_result)

        with patch("apps.worker.activities.step1_5.ToolRegistry") as mock_registry:
            mock_registry_instance = MagicMock()
            mock_registry_instance.get = MagicMock(side_effect=lambda name: mock_serp_tool if name == "serp_fetch" else mock_page_tool)
            mock_registry.return_value = mock_registry_instance

            with patch("apps.worker.activities.step1_5.activity"):
                with patch("apps.worker.activities.base.load_step_data") as mock_load:
                    # Return empty step1 data, then empty step0 data
                    mock_load.side_effect = [{"competitors": []}, {}]

                    result = await activity.execute(mock_ctx, mock_state)

        # Should process normally
        assert result["skipped"] is False
        assert result["related_keywords_analyzed"] == 1

        # No duplicates to skip
        kw_data = result["related_competitor_data"][0]
        assert kw_data["skipped_duplicate_count"] == 0

    @pytest.mark.asyncio
    async def test_works_when_step1_not_found(self) -> None:
        """Test execution works normally when step1 data is not found."""
        activity = Step1_5RelatedKeywordExtraction()

        activity.checkpoint = MagicMock()
        activity.checkpoint.load = AsyncMock(return_value=None)
        activity.checkpoint.save = AsyncMock()

        mock_ctx = MagicMock()
        mock_ctx.config = {"related_keywords": ["keyword1"]}
        mock_ctx.tenant_id = "test_tenant"
        mock_ctx.run_id = "test_run"

        mock_state = MagicMock()

        mock_serp_result = MagicMock()
        mock_serp_result.success = True
        mock_serp_result.data = {
            "results": [
                {"url": "https://example.com/1"},
            ]
        }

        mock_page_result = MagicMock()
        mock_page_result.success = True
        mock_page_result.data = {
            "title": "Test Page",
            "body_text": "Test content " * 50,
            "headings": [],
        }

        mock_serp_tool = MagicMock()
        mock_serp_tool.execute = AsyncMock(return_value=mock_serp_result)

        mock_page_tool = MagicMock()
        mock_page_tool.execute = AsyncMock(return_value=mock_page_result)

        with patch("apps.worker.activities.step1_5.ToolRegistry") as mock_registry:
            mock_registry_instance = MagicMock()
            mock_registry_instance.get = MagicMock(side_effect=lambda name: mock_serp_tool if name == "serp_fetch" else mock_page_tool)
            mock_registry.return_value = mock_registry_instance

            with patch("apps.worker.activities.step1_5.activity"):
                with patch("apps.worker.activities.base.load_step_data") as mock_load:
                    # Return None for step1 (not found), then empty step0 data
                    mock_load.side_effect = [None, {}]

                    result = await activity.execute(mock_ctx, mock_state)

        # Should process normally without errors
        assert result["skipped"] is False
        assert result["related_keywords_analyzed"] == 1


class TestStep1_5ContentValidation:
    """Tests for content validation logic."""

    def test_is_valid_content_empty(self) -> None:
        """Test empty content is invalid."""
        activity = Step1_5RelatedKeywordExtraction()
        assert activity._is_valid_content("") is False

    def test_is_valid_content_too_short(self) -> None:
        """Test content shorter than 100 chars is invalid."""
        activity = Step1_5RelatedKeywordExtraction()
        assert activity._is_valid_content("Short content") is False

    def test_is_valid_content_error_page(self) -> None:
        """Test error page detection."""
        activity = Step1_5RelatedKeywordExtraction()

        # Short error page should be invalid
        error_content = "404 Page Not Found"
        assert activity._is_valid_content(error_content) is False

        # Long page with 404 in content should be valid
        long_content = "This is article about HTTP error codes like 404. " * 50
        assert activity._is_valid_content(long_content) is True

    def test_is_valid_content_success(self) -> None:
        """Test valid content passes validation."""
        activity = Step1_5RelatedKeywordExtraction()

        valid_content = "This is valid article content. " * 20
        assert activity._is_valid_content(valid_content) is True


class TestStep1_5PageDataExtraction:
    """Tests for page data extraction."""

    def test_extract_page_data_basic(self) -> None:
        """Test basic page data extraction."""
        activity = Step1_5RelatedKeywordExtraction()

        fetch_data = {
            "title": "Test Title",
            "body_text": "Test content for the page.",
            "headings": ["H2 Title 1", "H2 Title 2"],
        }

        result = activity._extract_page_data(fetch_data, "https://example.com")

        assert result["url"] == "https://example.com"
        assert result["title"] == "Test Title"
        assert "Test content" in result["content_summary"]
        assert result["headings"] == ["H2 Title 1", "H2 Title 2"]
        assert "fetched_at" in result

    def test_extract_page_data_truncates_long_content(self) -> None:
        """Test long content is truncated."""
        activity = Step1_5RelatedKeywordExtraction()

        long_content = "A" * 20000  # Longer than MAX_CONTENT_CHARS
        fetch_data = {
            "title": "Test",
            "body_text": long_content,
            "headings": [],
        }

        result = activity._extract_page_data(fetch_data, "https://example.com")

        # Content should be truncated
        assert len(result["content_summary"]) <= 2000  # Summary limit

    def test_extract_page_data_fallback_to_h2(self) -> None:
        """Test headings fallback to h2 field."""
        activity = Step1_5RelatedKeywordExtraction()

        fetch_data = {
            "title": "Test",
            "body_text": "Content",
            "h2": ["Fallback H2 1", "Fallback H2 2"],
        }

        result = activity._extract_page_data(fetch_data, "https://example.com")

        assert result["headings"] == ["Fallback H2 1", "Fallback H2 2"]


class TestStep1_5TemporalActivity:
    """Tests for Temporal activity wrapper."""

    @pytest.mark.asyncio
    async def test_temporal_activity_wrapper(self) -> None:
        """Test Temporal activity wrapper calls correct method."""
        with patch("apps.worker.activities.step1_5.Step1_5RelatedKeywordExtraction") as mock_class:
            mock_instance = MagicMock()
            mock_instance.run = AsyncMock(return_value={"step": "step1_5"})
            mock_class.return_value = mock_instance

            args = {
                "tenant_id": "test_tenant",
                "run_id": "test_run",
                "config": {"related_keywords": []},
            }

            result = await step1_5_related_keyword_extraction(args)

            mock_instance.run.assert_called_once_with(
                tenant_id="test_tenant",
                run_id="test_run",
                config={"related_keywords": []},
            )
            assert result == {"step": "step1_5"}


class TestStep1_5Schema:
    """Tests for Step 1.5 output schema."""

    def test_schema_import(self) -> None:
        """Test schema can be imported."""
        from apps.worker.activities.schemas.step1_5 import (
            FetchMetadata,
            RelatedCompetitorArticle,
            RelatedKeywordData,
            Step1_5Output,
        )

        # Verify classes exist
        assert Step1_5Output is not None
        assert RelatedKeywordData is not None
        assert RelatedCompetitorArticle is not None
        assert FetchMetadata is not None

    def test_step1_5_output_model(self) -> None:
        """Test Step1_5Output model validation."""
        from apps.worker.activities.schemas.step1_5 import Step1_5Output

        output = Step1_5Output(
            related_keywords_analyzed=2,
            related_competitor_data=[],
            skipped=False,
        )

        assert output.step == "step1_5"
        assert output.related_keywords_analyzed == 2
        assert output.skipped is False

    def test_step1_5_output_skip(self) -> None:
        """Test Step1_5Output model for skipped case."""
        from apps.worker.activities.schemas.step1_5 import Step1_5Output

        output = Step1_5Output(
            related_keywords_analyzed=0,
            related_competitor_data=[],
            skipped=True,
            skip_reason="no_related_keywords",
        )

        assert output.skipped is True
        assert output.skip_reason == "no_related_keywords"
