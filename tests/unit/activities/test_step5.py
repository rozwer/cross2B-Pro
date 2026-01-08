"""Tests for step5 primary collection activity.

Tests cover:
- Basic source collection
- 3-phase classification
- Knowledge gap discovery
- Section-source mapping
- Freshness score calculation
"""

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from apps.worker.activities.schemas.step5 import (
    CollectionStats,
    KnowledgeGap,
    PhaseSpecificData,
    PrimarySource,
    Step5Output,
)
from apps.worker.activities.step5 import Step5PrimaryCollection


def create_step5_activity() -> Step5PrimaryCollection:
    """Helper to create Step5PrimaryCollection with mocked dependencies."""
    with patch("apps.worker.activities.step5.BaseActivity.__init__", return_value=None):
        with patch("apps.worker.activities.step5.InputValidator"):
            with patch("apps.worker.activities.step5.OutputParser"):
                with patch("apps.worker.activities.step5.CheckpointManager"):
                    step = Step5PrimaryCollection.__new__(Step5PrimaryCollection)
                    step.store = MagicMock()
                    step.input_validator = MagicMock()
                    step.parser = MagicMock()
                    step.checkpoint = MagicMock()
                    return step


class TestStep5PrimaryCollection:
    """Test basic Step5 functionality."""

    @pytest.fixture
    def activity(self) -> Step5PrimaryCollection:
        """Create Step5PrimaryCollection instance."""
        return create_step5_activity()

    def test_step_id(self, activity: Step5PrimaryCollection) -> None:
        """Test step_id property."""
        assert activity.step_id == "step5"


class TestPhaseClassification:
    """Test 3-phase source classification."""

    @pytest.fixture
    def activity(self) -> Step5PrimaryCollection:
        """Create Step5PrimaryCollection instance."""
        return create_step5_activity()

    def test_classify_phase1_anxiety(self, activity: Step5PrimaryCollection) -> None:
        """Test phase1 (anxiety) classification."""
        source = {
            "title": "企業のリスク管理",
            "excerpt": "この問題が深刻化すると損失は避けられない",
        }
        result = activity._classify_phase(source)
        assert result == "phase1_anxiety"

    def test_classify_phase2_understanding(self, activity: Step5PrimaryCollection) -> None:
        """Test phase2 (understanding) classification."""
        source = {
            "title": "効果的な対策方法",
            "excerpt": "この手順で改善できます。ステップバイステップで解説",
        }
        result = activity._classify_phase(source)
        assert result == "phase2_understanding"

    def test_classify_phase3_action(self, activity: Step5PrimaryCollection) -> None:
        """Test phase3 (action) classification."""
        source = {
            "title": "成功事例から学ぶ",
            "excerpt": "導入実績100社以上。ROI200%達成の成果",
        }
        result = activity._classify_phase(source)
        assert result == "phase3_action"

    def test_classify_default_to_phase2(self, activity: Step5PrimaryCollection) -> None:
        """Test default classification is phase2."""
        source = {
            "title": "一般的な記事",
            "excerpt": "特に特徴のない内容です",
        }
        result = activity._classify_phase(source)
        assert result == "phase2_understanding"

    def test_classify_empty_source(self, activity: Step5PrimaryCollection) -> None:
        """Test classification with empty source."""
        source: dict[str, Any] = {}
        result = activity._classify_phase(source)
        assert result == "phase2_understanding"


class TestFreshnessScore:
    """Test freshness score calculation."""

    @pytest.fixture
    def activity(self) -> Step5PrimaryCollection:
        """Create Step5PrimaryCollection instance."""
        return create_step5_activity()

    def test_freshness_current_year(self, activity: Step5PrimaryCollection) -> None:
        """Test freshness score for current year publication."""
        current_year = str(datetime.now().year)
        result = activity._calculate_freshness_score(current_year)
        assert result == 1.0

    def test_freshness_one_year_old(self, activity: Step5PrimaryCollection) -> None:
        """Test freshness score for 1-year-old publication."""
        last_year = str(datetime.now().year - 1)
        result = activity._calculate_freshness_score(last_year)
        assert result == 0.9

    def test_freshness_two_years_old(self, activity: Step5PrimaryCollection) -> None:
        """Test freshness score for 2-year-old publication."""
        two_years = str(datetime.now().year - 2)
        result = activity._calculate_freshness_score(two_years)
        assert result == 0.7

    def test_freshness_three_years_old(self, activity: Step5PrimaryCollection) -> None:
        """Test freshness score for 3-year-old publication."""
        three_years = str(datetime.now().year - 3)
        result = activity._calculate_freshness_score(three_years)
        assert result == 0.5

    def test_freshness_very_old(self, activity: Step5PrimaryCollection) -> None:
        """Test freshness score for very old publication."""
        old_year = str(datetime.now().year - 10)
        result = activity._calculate_freshness_score(old_year)
        assert result == 0.1  # Minimum value

    def test_freshness_iso_format(self, activity: Step5PrimaryCollection) -> None:
        """Test freshness score with ISO format date."""
        current_year = datetime.now().year
        iso_date = f"{current_year}-06-15"
        result = activity._calculate_freshness_score(iso_date)
        assert result == 1.0

    def test_freshness_none_date(self, activity: Step5PrimaryCollection) -> None:
        """Test freshness score with None date."""
        result = activity._calculate_freshness_score(None)
        assert result == 0.5  # Default

    def test_freshness_invalid_date(self, activity: Step5PrimaryCollection) -> None:
        """Test freshness score with invalid date."""
        result = activity._calculate_freshness_score("not-a-date")
        assert result == 0.5  # Default


class TestKnowledgeGapDiscovery:
    """Test knowledge gap discovery from step3c data."""

    @pytest.fixture
    def activity(self) -> Step5PrimaryCollection:
        """Create Step5PrimaryCollection instance."""
        return create_step5_activity()

    def test_find_knowledge_gaps_with_step3c(self, activity: Step5PrimaryCollection) -> None:
        """Test knowledge gap discovery with step3c data."""
        step3c_data = {
            "differentiation_angles": [
                {
                    "keyword": "AI活用",
                    "description": "AI活用の具体的手法",
                    "coverage": "0/10記事",
                    "recommended_section": "H2-5",
                },
                {
                    "keyword": "コスト削減",
                    "description": "コスト削減の実践例",
                    "coverage": "2/10記事",
                },
            ]
        }
        sources = [
            PrimarySource(
                url="https://example.com/ai",
                title="AI活用ガイド",
                excerpt="AI活用の具体的な手法について解説します",
            ),
        ]

        result = activity._find_knowledge_gaps(step3c_data, sources)

        assert len(result) == 2
        assert result[0].gap_id == "KG001"
        assert result[0].gap_description == "AI活用の具体的手法"
        assert result[0].competitor_coverage == "0/10記事"
        assert result[0].primary_source_url == "https://example.com/ai"
        assert result[0].differentiation_value == "high"  # 0/10 → high
        assert result[0].implementation_section == "H2-5"

        assert result[1].gap_id == "KG002"
        assert result[1].differentiation_value == "medium"  # 2/10 → medium

    def test_find_knowledge_gaps_no_step3c(self, activity: Step5PrimaryCollection) -> None:
        """Test knowledge gap discovery without step3c data."""
        sources = [
            PrimarySource(url="https://example.com", title="Test", excerpt="test"),
        ]

        result = activity._find_knowledge_gaps(None, sources)

        assert len(result) == 0

    def test_find_knowledge_gaps_empty_angles(self, activity: Step5PrimaryCollection) -> None:
        """Test knowledge gap discovery with empty angles."""
        step3c_data = {"differentiation_angles": []}
        sources: list[PrimarySource] = []

        result = activity._find_knowledge_gaps(step3c_data, sources)

        assert len(result) == 0

    def test_find_knowledge_gaps_max_10(self, activity: Step5PrimaryCollection) -> None:
        """Test knowledge gap discovery limits to 10 gaps."""
        step3c_data = {"differentiation_angles": [{"keyword": f"topic{i}", "description": f"desc{i}"} for i in range(15)]}
        sources: list[PrimarySource] = []

        result = activity._find_knowledge_gaps(step3c_data, sources)

        assert len(result) == 10


class TestSectionSourceMapping:
    """Test section-source mapping."""

    @pytest.fixture
    def activity(self) -> Step5PrimaryCollection:
        """Create Step5PrimaryCollection instance."""
        return create_step5_activity()

    def test_map_sources_to_sections(self, activity: Step5PrimaryCollection) -> None:
        """Test mapping sources to sections."""
        sources = [
            PrimarySource(
                url="https://example.com/1",
                title="Problem",
                phase_alignment="phase1_anxiety",
            ),
            PrimarySource(
                url="https://example.com/2",
                title="Solution",
                phase_alignment="phase2_understanding",
            ),
            PrimarySource(
                url="https://example.com/3",
                title="Success",
                phase_alignment="phase3_action",
            ),
        ]
        sections = [
            {"id": "introduction", "title": "はじめに"},
            {"id": "H2-5", "title": "解決方法"},
            {"id": "H2-12", "title": "導入事例"},
        ]

        result = activity._map_sources_to_sections(sources, sections)

        assert len(result) == 3

        # Introduction gets phase1 sources
        intro = result[0]
        assert intro.section_id == "introduction"
        assert "https://example.com/1" in intro.assigned_sources
        assert intro.enhancement_notes == "phase1_anxiety向けデータ配置"

        # H2-5 gets phase2 sources
        h2_5 = result[1]
        assert h2_5.section_id == "H2-5"
        assert "https://example.com/2" in h2_5.assigned_sources
        assert h2_5.enhancement_notes == "phase2_understanding向けデータ配置"

        # H2-12 gets phase3 sources
        h2_12 = result[2]
        assert h2_12.section_id == "H2-12"
        assert "https://example.com/3" in h2_12.assigned_sources
        assert h2_12.enhancement_notes == "phase3_action向けデータ配置"

    def test_map_sources_empty_sections(self, activity: Step5PrimaryCollection) -> None:
        """Test mapping with no sections."""
        sources = [
            PrimarySource(url="https://example.com", title="Test"),
        ]
        sections: list[dict[str, Any]] = []

        result = activity._map_sources_to_sections(sources, sections)

        assert len(result) == 0

    def test_map_sources_max_3_per_section(self, activity: Step5PrimaryCollection) -> None:
        """Test mapping limits to 3 sources per section."""
        sources = [
            PrimarySource(
                url=f"https://example.com/{i}",
                title=f"Source {i}",
                phase_alignment="phase2_understanding",
            )
            for i in range(5)
        ]
        sections = [{"id": "H2-5", "title": "Main"}]

        result = activity._map_sources_to_sections(sources, sections)

        assert len(result) == 1
        assert len(result[0].assigned_sources) == 3  # Max 3


class TestPhaseSpecificData:
    """Test phase-specific data building."""

    @pytest.fixture
    def activity(self) -> Step5PrimaryCollection:
        """Create Step5PrimaryCollection instance."""
        return create_step5_activity()

    def test_build_phase_specific_data(self, activity: Step5PrimaryCollection) -> None:
        """Test building phase-specific data."""
        sources = [
            PrimarySource(
                url="https://example.com/1",
                title="Risk",
                excerpt="リスクについての説明",
                phase_alignment="phase1_anxiety",
            ),
            PrimarySource(
                url="https://example.com/2",
                title="Solution",
                excerpt="解決策の説明",
                phase_alignment="phase2_understanding",
            ),
            PrimarySource(
                url="https://example.com/3",
                title="Method",
                excerpt="方法の説明",
                phase_alignment="phase2_understanding",
            ),
            PrimarySource(
                url="https://example.com/4",
                title="Success",
                excerpt="成功事例",
                phase_alignment="phase3_action",
            ),
        ]

        result = activity._build_phase_specific_data(sources)

        assert result.phase1_anxiety.total_count == 1
        assert len(result.phase1_anxiety.source_urls) == 1
        assert "https://example.com/1" in result.phase1_anxiety.source_urls

        assert result.phase2_understanding.total_count == 2
        assert len(result.phase2_understanding.source_urls) == 2

        assert result.phase3_action.total_count == 1
        assert len(result.phase3_action.source_urls) == 1

    def test_build_phase_specific_data_empty(self, activity: Step5PrimaryCollection) -> None:
        """Test building phase-specific data with no sources."""
        sources: list[PrimarySource] = []

        result = activity._build_phase_specific_data(sources)

        assert result.phase1_anxiety.total_count == 0
        assert result.phase2_understanding.total_count == 0
        assert result.phase3_action.total_count == 0


class TestSchemas:
    """Test schema validation."""

    def test_primary_source_defaults(self) -> None:
        """Test PrimarySource default values."""
        source = PrimarySource(url="https://example.com", title="Test")

        assert source.source_type == "other"
        assert source.excerpt == ""
        assert source.credibility_score == 0.5
        assert source.verified is False
        assert source.phase_alignment == "phase2_understanding"
        assert source.freshness_score == 0.5
        assert source.data_points == []
        assert source.publication_date is None

    def test_collection_stats_defaults(self) -> None:
        """Test CollectionStats default values."""
        stats = CollectionStats()

        assert stats.total_collected == 0
        assert stats.total_verified == 0
        assert stats.failed_queries == 0
        assert stats.phase1_count == 0
        assert stats.phase2_count == 0
        assert stats.phase3_count == 0

    def test_knowledge_gap_model(self) -> None:
        """Test KnowledgeGap model."""
        gap = KnowledgeGap(
            gap_id="KG001",
            gap_description="AI活用の手法",
            competitor_coverage="0/10記事",
            differentiation_value="high",
        )

        assert gap.gap_id == "KG001"
        assert gap.primary_source_url is None
        assert gap.implementation_section == ""

    def test_step5_output_model(self) -> None:
        """Test Step5Output model."""
        output = Step5Output(
            keyword="SEO対策",
            sources=[
                PrimarySource(url="https://example.com", title="Test"),
            ],
            collection_stats=CollectionStats(
                total_collected=1,
                phase1_count=0,
                phase2_count=1,
                phase3_count=0,
            ),
            phase_specific_data=PhaseSpecificData(),
            knowledge_gaps_filled=[
                KnowledgeGap(gap_id="KG001", gap_description="Gap 1"),
            ],
        )

        assert output.step == "step5"
        assert output.keyword == "SEO対策"
        assert len(output.sources) == 1
        assert output.collection_stats.phase2_count == 1
        assert len(output.knowledge_gaps_filled) == 1
