"""Unit tests for Step2 word count and structure analysis."""

from unittest.mock import MagicMock, patch

import pytest

from apps.worker.activities.schemas.step2 import (
    Step2Output,
    StructureAnalysis,
    WordCountAnalysis,
)
from apps.worker.activities.step2 import Step2CSVValidation


class TestWordCountAnalysis:
    """Tests for WordCountAnalysis schema."""

    def test_valid_analysis(self):
        """Test valid word count analysis creation."""
        analysis = WordCountAnalysis(
            min=100,
            max=500,
            average=300.0,
            median=300.0,
        )
        assert analysis.min == 100
        assert analysis.max == 500
        assert analysis.average == 300.0
        assert analysis.median == 300.0

    def test_min_must_be_non_negative(self):
        """Test min must be >= 0."""
        with pytest.raises(ValueError):
            WordCountAnalysis(min=-1, max=100, average=50.0, median=50.0)

    def test_max_must_be_non_negative(self):
        """Test max must be >= 0."""
        with pytest.raises(ValueError):
            WordCountAnalysis(min=0, max=-100, average=50.0, median=50.0)


class TestStructureAnalysis:
    """Tests for StructureAnalysis schema."""

    def test_valid_analysis(self):
        """Test valid structure analysis creation."""
        analysis = StructureAnalysis(
            avg_h2_count=5.0,
            avg_h3_count=10.0,
            common_patterns=["まとめ", "FAQ"],
        )
        assert analysis.avg_h2_count == 5.0
        assert analysis.avg_h3_count == 10.0
        assert analysis.common_patterns == ["まとめ", "FAQ"]

    def test_default_values(self):
        """Test default values."""
        analysis = StructureAnalysis()
        assert analysis.avg_h2_count == 0.0
        assert analysis.avg_h3_count == 0.0
        assert analysis.common_patterns == []


class TestStep2OutputWithAnalysis:
    """Tests for Step2Output with new analysis fields."""

    def test_output_with_analysis(self):
        """Test Step2Output with word count and structure analysis."""
        output = Step2Output(
            is_valid=True,
            word_count_analysis=WordCountAnalysis(min=100, max=500, average=300.0, median=300.0),
            structure_analysis=StructureAnalysis(avg_h2_count=3.0, avg_h3_count=6.0, common_patterns=["まとめ"]),
        )
        assert output.word_count_analysis is not None
        assert output.word_count_analysis.min == 100
        assert output.structure_analysis is not None
        assert output.structure_analysis.avg_h2_count == 3.0

    def test_output_without_analysis(self):
        """Test Step2Output without analysis (backward compatibility)."""
        output = Step2Output(is_valid=True)
        assert output.word_count_analysis is None
        assert output.structure_analysis is None


class TestComputeWordCountAnalysis:
    """Tests for _compute_word_count_analysis method."""

    @pytest.fixture
    def activity(self):
        """Create Step2CSVValidation instance with mocked dependencies."""
        with patch("apps.worker.activities.step2.CheckpointManager"):
            with patch("apps.worker.activities.step2.InputValidator"):
                activity = Step2CSVValidation()
                # Mock ContentMetrics
                activity.metrics = MagicMock()
                return activity

    def test_empty_records_returns_none(self, activity):
        """Test empty records returns None."""
        result = activity._compute_word_count_analysis([])
        assert result is None

    def test_single_record(self, activity):
        """Test single record analysis."""
        activity.metrics.text_metrics.return_value = MagicMock(word_count=500)

        records = [{"content": "test content"}]
        result = activity._compute_word_count_analysis(records)

        assert result is not None
        assert result["min"] == 500
        assert result["max"] == 500
        assert result["average"] == 500.0
        assert result["median"] == 500.0

    def test_multiple_records(self, activity):
        """Test multiple records analysis."""
        # Return different word counts for each call
        activity.metrics.text_metrics.side_effect = [
            MagicMock(word_count=100),
            MagicMock(word_count=200),
            MagicMock(word_count=300),
            MagicMock(word_count=400),
            MagicMock(word_count=500),
        ]

        records = [
            {"content": "content1"},
            {"content": "content2"},
            {"content": "content3"},
            {"content": "content4"},
            {"content": "content5"},
        ]
        result = activity._compute_word_count_analysis(records)

        assert result is not None
        assert result["min"] == 100
        assert result["max"] == 500
        assert result["average"] == 300.0
        assert result["median"] == 300.0


class TestComputeStructureAnalysis:
    """Tests for _compute_structure_analysis method."""

    @pytest.fixture
    def activity(self):
        """Create Step2CSVValidation instance with mocked dependencies."""
        with patch("apps.worker.activities.step2.CheckpointManager"):
            with patch("apps.worker.activities.step2.InputValidator"):
                return Step2CSVValidation()

    def test_empty_records_returns_none(self, activity):
        """Test empty records returns None."""
        result = activity._compute_structure_analysis([])
        assert result is None

    def test_markdown_headings(self, activity):
        """Test markdown style headings."""
        records = [
            {
                "headings": [
                    "## はじめに",
                    "### 詳細1",
                    "### 詳細2",
                    "## まとめ",
                ]
            }
        ]
        result = activity._compute_structure_analysis(records)

        assert result is not None
        assert result["avg_h2_count"] == 2.0
        assert result["avg_h3_count"] == 2.0

    def test_html_headings(self, activity):
        """Test HTML style headings."""
        records = [
            {
                "headings": [
                    "<h2>Introduction</h2>",
                    "<h3>Details</h3>",
                    "<h2>Conclusion</h2>",
                ]
            }
        ]
        result = activity._compute_structure_analysis(records)

        assert result is not None
        assert result["avg_h2_count"] == 2.0
        assert result["avg_h3_count"] == 1.0

    def test_common_patterns_extraction(self, activity):
        """Test common patterns are extracted correctly."""
        records = [
            {"headings": ["## はじめに", "## まとめ"]},
            {"headings": ["## はじめに", "## まとめ"]},
            {"headings": ["## はじめに", "## FAQ"]},
        ]
        result = activity._compute_structure_analysis(records)

        assert result is not None
        # "はじめに" appears in 3/3 (100%), "まとめ" in 2/3 (67%)
        assert "はじめに" in result["common_patterns"]
        assert "まとめ" in result["common_patterns"]

    def test_no_common_patterns_when_threshold_not_met(self, activity):
        """Test no common patterns when threshold not met."""
        records = [
            {"headings": ["## A", "## B"]},
            {"headings": ["## C", "## D"]},
            {"headings": ["## E", "## F"]},
            {"headings": ["## G", "## H"]},
        ]
        result = activity._compute_structure_analysis(records)

        assert result is not None
        # No heading appears in 50%+ of records
        assert result["common_patterns"] == []


class TestExtractHeadingText:
    """Tests for _extract_heading_text method."""

    @pytest.fixture
    def activity(self):
        """Create Step2CSVValidation instance with mocked dependencies."""
        with patch("apps.worker.activities.step2.CheckpointManager"):
            with patch("apps.worker.activities.step2.InputValidator"):
                return Step2CSVValidation()

    def test_markdown_h1(self, activity):
        """Test markdown H1 extraction."""
        result = activity._extract_heading_text("# タイトル")
        assert result == "タイトル"

    def test_markdown_h2(self, activity):
        """Test markdown H2 extraction."""
        result = activity._extract_heading_text("## セクション")
        assert result == "セクション"

    def test_markdown_h3(self, activity):
        """Test markdown H3 extraction."""
        result = activity._extract_heading_text("### サブセクション")
        assert result == "サブセクション"

    def test_html_h2(self, activity):
        """Test HTML H2 extraction."""
        result = activity._extract_heading_text("<h2>Section Title</h2>")
        assert result == "Section Title"

    def test_html_h3_with_attributes(self, activity):
        """Test HTML H3 with attributes extraction."""
        result = activity._extract_heading_text('<h3 class="title">Subsection</h3>')
        assert result == "Subsection"

    def test_plain_text(self, activity):
        """Test plain text passthrough."""
        result = activity._extract_heading_text("Plain heading")
        assert result == "Plain heading"
