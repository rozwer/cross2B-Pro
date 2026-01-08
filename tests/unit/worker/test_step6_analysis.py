"""Unit tests for Step6 blog.System integration features."""

from unittest.mock import MagicMock, patch

import pytest

from apps.worker.activities.schemas.step6 import (
    CitationFormat,
    DataAnchorPlacement,
    FourPillarsVerification,
    Step6Output,
)
from apps.worker.activities.step6 import Step6EnhancedOutline


class TestDataAnchorPlacement:
    """Tests for DataAnchorPlacement schema."""

    def test_valid_placement(self):
        """Test valid data anchor placement creation."""
        placement = DataAnchorPlacement(
            section_title="はじめに",
            anchor_type="intro_impact",
            data_point="80%",
            source_citation="[S1]",
        )
        assert placement.section_title == "はじめに"
        assert placement.anchor_type == "intro_impact"
        assert placement.data_point == "80%"
        assert placement.source_citation == "[S1]"

    def test_default_source_citation(self):
        """Test default source citation is empty."""
        placement = DataAnchorPlacement(
            section_title="Test",
            anchor_type="section_evidence",
            data_point="100人",
        )
        assert placement.source_citation == ""


class TestFourPillarsVerification:
    """Tests for FourPillarsVerification schema."""

    def test_valid_verification(self):
        """Test valid four pillars verification creation."""
        verification = FourPillarsVerification(
            sections_verified=5,
            issues_found=["neuroscience_weak"],
            auto_corrections=[],
            pillar_scores={
                "neuroscience": 0.33,
                "behavioral_economics": 0.5,
                "llmo": 0.8,
                "kgi": 0.67,
            },
        )
        assert verification.sections_verified == 5
        assert len(verification.issues_found) == 1
        assert verification.pillar_scores["llmo"] == 0.8

    def test_default_values(self):
        """Test default values."""
        verification = FourPillarsVerification()
        assert verification.sections_verified == 0
        assert verification.issues_found == []
        assert verification.auto_corrections == []
        assert verification.pillar_scores == {}


class TestCitationFormat:
    """Tests for CitationFormat schema."""

    def test_valid_format(self):
        """Test valid citation format creation."""
        fmt = CitationFormat(
            style="inline",
            examples=["[S1]: https://example.com/..."],
        )
        assert fmt.style == "inline"
        assert len(fmt.examples) == 1

    def test_default_values(self):
        """Test default values."""
        fmt = CitationFormat()
        assert fmt.style == "inline"
        assert fmt.examples == []


class TestStep6OutputWithBlogSystem:
    """Tests for Step6Output with blog.System fields."""

    def test_output_with_blog_system_fields(self):
        """Test Step6Output with all blog.System fields."""
        output = Step6Output(
            keyword="テストキーワード",
            data_anchor_placements=[
                DataAnchorPlacement(
                    section_title="はじめに",
                    anchor_type="intro_impact",
                    data_point="80%",
                )
            ],
            four_pillars_verification=FourPillarsVerification(
                sections_verified=3,
                pillar_scores={"neuroscience": 0.5},
            ),
            citation_format=CitationFormat(style="inline"),
        )
        assert len(output.data_anchor_placements) == 1
        assert output.four_pillars_verification is not None
        assert output.four_pillars_verification.sections_verified == 3
        assert output.citation_format is not None

    def test_output_without_blog_system_fields(self):
        """Test Step6Output without blog.System fields (backward compatibility)."""
        output = Step6Output(keyword="テストキーワード")
        assert output.data_anchor_placements == []
        assert output.four_pillars_verification is None
        assert output.citation_format is None


class TestExtractDataAnchorPlacements:
    """Tests for _extract_data_anchor_placements method."""

    @pytest.fixture
    def activity(self):
        """Create Step6EnhancedOutline instance with mocked dependencies."""
        with patch("apps.worker.activities.step6.CheckpointManager"):
            with patch("apps.worker.activities.step6.InputValidator"):
                return Step6EnhancedOutline()

    def test_extract_source_citations(self, activity):
        """Test extraction of [S1] style citations."""
        outline = """## はじめに
この記事では重要なデータ[S1]を紹介します。

## 詳細
データによると80%[S2]の人が該当します。

## まとめ
結論として[S3]が重要です。
"""
        result = activity._extract_data_anchor_placements(outline, [])

        assert len(result) > 0
        assert any(p.data_point == "[S1]" for p in result)
        assert any(p.anchor_type == "intro_impact" for p in result)
        assert any(p.anchor_type == "summary" for p in result)

    def test_extract_numeric_data_points(self, activity):
        """Test extraction of numeric data points."""
        outline = """## 導入
100万人以上のユーザーがいます。

## 詳細
80%が満足と回答しています。
"""
        result = activity._extract_data_anchor_placements(outline, [])

        # Should find numeric patterns
        data_points = [p.data_point for p in result]
        assert any("万" in dp for dp in data_points) or any("%" in dp for dp in data_points)

    def test_empty_outline(self, activity):
        """Test with empty outline."""
        result = activity._extract_data_anchor_placements("", [])
        assert result == []


class TestVerifyFourPillars:
    """Tests for _verify_four_pillars method."""

    @pytest.fixture
    def activity(self):
        """Create Step6EnhancedOutline instance with mocked dependencies."""
        with patch("apps.worker.activities.step6.CheckpointManager"):
            with patch("apps.worker.activities.step6.InputValidator"):
                return Step6EnhancedOutline()

    def test_all_pillars_present(self, activity):
        """Test outline with all four pillars present."""
        outline = """## はじめに
不安を感じていませんか？多くの人が選んでいます。

## 詳細
簡単な方法で専門家もおすすめしています。

## 次のステップ
詳しくは無料相談へ。

## まとめ
今だけ限定で安心のサポート付き。
"""
        md_metrics = MagicMock(h2_count=4, h3_count=2)
        result = activity._verify_four_pillars(outline, md_metrics)

        assert result.sections_verified == 4
        assert result.pillar_scores.get("neuroscience", 0) > 0
        assert result.pillar_scores.get("behavioral_economics", 0) > 0
        assert result.pillar_scores.get("kgi", 0) > 0

    def test_missing_pillars(self, activity):
        """Test outline with missing pillars."""
        outline = """## セクション1
普通のテキストです。

## セクション2
特に何もありません。
"""
        md_metrics = MagicMock(h2_count=2, h3_count=0)
        result = activity._verify_four_pillars(outline, md_metrics)

        # Should have issues
        assert len(result.issues_found) > 0

    def test_pillar_scores_range(self, activity):
        """Test pillar scores are within valid range."""
        outline = """## テスト
安心してください。損はありません。詳しくはこちら。
"""
        md_metrics = MagicMock(h2_count=1, h3_count=0)
        result = activity._verify_four_pillars(outline, md_metrics)

        for score in result.pillar_scores.values():
            assert 0.0 <= score <= 1.0


class TestBuildCitationFormat:
    """Tests for _build_citation_format method."""

    @pytest.fixture
    def activity(self):
        """Create Step6EnhancedOutline instance with mocked dependencies."""
        with patch("apps.worker.activities.step6.CheckpointManager"):
            with patch("apps.worker.activities.step6.InputValidator"):
                return Step6EnhancedOutline()

    def test_build_with_sources(self, activity):
        """Test citation format with sources."""
        source_citations = {
            "https://example.com/article1": ["[S1]"],
            "https://example.com/article2": ["[S2]"],
        }
        result = activity._build_citation_format(source_citations)

        assert result.style == "inline"
        assert len(result.examples) <= 3

    def test_build_with_empty_sources(self, activity):
        """Test citation format with no sources."""
        result = activity._build_citation_format({})

        assert result.style == "inline"
        assert result.examples == []
