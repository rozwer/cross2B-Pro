"""Unit tests for Step 7A schema extensions (blog.System Ver8.3).

Tests cover:
- SectionWordCount model validation
- FourPillarsImplementation and sub-models
- CTAImplementation model
- WordCountTracking model
- SplitGeneration model
- Step7aOutput extensions and backward compatibility
"""

import pytest

from apps.worker.activities.schemas.step7a import (
    BehavioralEconomicsImplementation,
    CTAImplementation,
    CTAPosition,
    DraftQuality,
    DraftQualityMetrics,
    DraftSection,
    FourPillarsImplementation,
    GenerationStats,
    KGIImplementation,
    LLMOImplementation,
    NeuroscienceImplementation,
    SectionWordCount,
    SplitGeneration,
    Step7aOutput,
    WordCountTracking,
)


class TestSectionWordCount:
    """Tests for SectionWordCount model."""

    def test_default_values(self) -> None:
        """Test default values are set correctly."""
        section = SectionWordCount()
        assert section.section_title == ""
        assert section.target == 0
        assert section.actual == 0
        assert section.variance == 0
        assert section.is_within_tolerance is True

    def test_with_values(self) -> None:
        """Test with explicit values."""
        section = SectionWordCount(
            section_title="はじめに",
            target=500,
            actual=480,
            variance=-20,
            is_within_tolerance=True,
        )
        assert section.section_title == "はじめに"
        assert section.target == 500
        assert section.actual == 480
        assert section.variance == -20
        assert section.is_within_tolerance is True

    def test_negative_variance_allowed(self) -> None:
        """Test that negative variance is allowed."""
        section = SectionWordCount(
            section_title="Test",
            target=500,
            actual=300,
            variance=-200,
            is_within_tolerance=False,
        )
        assert section.variance == -200

    def test_word_counts_must_be_non_negative(self) -> None:
        """Test that target and actual must be non-negative."""
        with pytest.raises(ValueError):
            SectionWordCount(target=-1)
        with pytest.raises(ValueError):
            SectionWordCount(actual=-1)


class TestNeuroscienceImplementation:
    """Tests for NeuroscienceImplementation model."""

    def test_default_values(self) -> None:
        """Test default values."""
        impl = NeuroscienceImplementation()
        assert impl.applied is False
        assert impl.details == ""

    def test_with_values(self) -> None:
        """Test with explicit values."""
        impl = NeuroscienceImplementation(
            applied=True,
            details="Used fear trigger and curiosity gap",
        )
        assert impl.applied is True
        assert "fear trigger" in impl.details


class TestBehavioralEconomicsImplementation:
    """Tests for BehavioralEconomicsImplementation model."""

    def test_default_values(self) -> None:
        """Test default values."""
        impl = BehavioralEconomicsImplementation()
        assert impl.principles_used == []

    def test_with_principles(self) -> None:
        """Test with principles list."""
        impl = BehavioralEconomicsImplementation(principles_used=["損失回避", "社会的証明", "権威"])
        assert len(impl.principles_used) == 3
        assert "損失回避" in impl.principles_used


class TestLLMOImplementation:
    """Tests for LLMOImplementation model."""

    def test_default_values(self) -> None:
        """Test default values."""
        impl = LLMOImplementation()
        assert impl.token_count == 0
        assert impl.is_independent is False

    def test_with_values(self) -> None:
        """Test with explicit values."""
        impl = LLMOImplementation(token_count=450, is_independent=True)
        assert impl.token_count == 450
        assert impl.is_independent is True

    def test_token_count_must_be_non_negative(self) -> None:
        """Test that token_count must be non-negative."""
        with pytest.raises(ValueError):
            LLMOImplementation(token_count=-1)


class TestKGIImplementation:
    """Tests for KGIImplementation model."""

    def test_default_values(self) -> None:
        """Test default values."""
        impl = KGIImplementation()
        assert impl.cta_present is False
        assert impl.cta_type is None

    def test_with_cta(self) -> None:
        """Test with CTA present."""
        impl = KGIImplementation(cta_present=True, cta_type="inquiry")
        assert impl.cta_present is True
        assert impl.cta_type == "inquiry"


class TestFourPillarsImplementation:
    """Tests for FourPillarsImplementation model."""

    def test_default_values(self) -> None:
        """Test default values create nested defaults."""
        impl = FourPillarsImplementation()
        assert impl.section_title == ""
        assert isinstance(impl.neuroscience, NeuroscienceImplementation)
        assert isinstance(impl.behavioral_economics, BehavioralEconomicsImplementation)
        assert isinstance(impl.llmo, LLMOImplementation)
        assert isinstance(impl.kgi, KGIImplementation)

    def test_with_full_implementation(self) -> None:
        """Test with all four pillars implemented."""
        impl = FourPillarsImplementation(
            section_title="SEOとは",
            neuroscience=NeuroscienceImplementation(applied=True, details="恐怖トリガー"),
            behavioral_economics=BehavioralEconomicsImplementation(principles_used=["損失回避"]),
            llmo=LLMOImplementation(token_count=500, is_independent=True),
            kgi=KGIImplementation(cta_present=True, cta_type="purchase"),
        )
        assert impl.section_title == "SEOとは"
        assert impl.neuroscience.applied is True
        assert len(impl.behavioral_economics.principles_used) == 1
        assert impl.llmo.is_independent is True
        assert impl.kgi.cta_type == "purchase"

    def test_partial_implementation(self) -> None:
        """Test with partial implementation."""
        impl = FourPillarsImplementation(
            section_title="まとめ",
            neuroscience=NeuroscienceImplementation(applied=False),
            kgi=KGIImplementation(cta_present=True, cta_type="signup"),
        )
        assert impl.neuroscience.applied is False
        assert impl.kgi.cta_present is True


class TestCTAPosition:
    """Tests for CTAPosition model."""

    def test_default_values(self) -> None:
        """Test default values."""
        pos = CTAPosition()
        assert pos.position == 0
        assert pos.implemented is False

    def test_with_values(self) -> None:
        """Test with explicit values."""
        pos = CTAPosition(position=3, implemented=True)
        assert pos.position == 3
        assert pos.implemented is True

    def test_position_must_be_non_negative(self) -> None:
        """Test that position must be non-negative."""
        with pytest.raises(ValueError):
            CTAPosition(position=-1)


class TestCTAImplementation:
    """Tests for CTAImplementation model."""

    def test_default_values(self) -> None:
        """Test default values create nested defaults."""
        impl = CTAImplementation()
        assert isinstance(impl.early, CTAPosition)
        assert isinstance(impl.mid, CTAPosition)
        assert isinstance(impl.final, CTAPosition)

    def test_with_all_positions(self) -> None:
        """Test with all CTA positions implemented."""
        impl = CTAImplementation(
            early=CTAPosition(position=1, implemented=True),
            mid=CTAPosition(position=4, implemented=True),
            final=CTAPosition(position=7, implemented=True),
        )
        assert impl.early.position == 1
        assert impl.mid.position == 4
        assert impl.final.position == 7
        assert all([impl.early.implemented, impl.mid.implemented, impl.final.implemented])

    def test_partial_cta(self) -> None:
        """Test with only some CTAs implemented."""
        impl = CTAImplementation(
            early=CTAPosition(position=1, implemented=True),
            mid=CTAPosition(position=4, implemented=False),
            final=CTAPosition(position=7, implemented=True),
        )
        assert impl.early.implemented is True
        assert impl.mid.implemented is False
        assert impl.final.implemented is True


class TestWordCountTracking:
    """Tests for WordCountTracking model."""

    def test_default_values(self) -> None:
        """Test default values."""
        tracking = WordCountTracking()
        assert tracking.target == 0
        assert tracking.current == 0
        assert tracking.remaining == 0
        assert tracking.progress_percent == 0.0

    def test_with_progress(self) -> None:
        """Test with progress values."""
        tracking = WordCountTracking(
            target=5000,
            current=2500,
            remaining=2500,
            progress_percent=50.0,
        )
        assert tracking.target == 5000
        assert tracking.current == 2500
        assert tracking.progress_percent == 50.0

    def test_progress_percent_bounds(self) -> None:
        """Test that progress_percent is bounded 0-100."""
        with pytest.raises(ValueError):
            WordCountTracking(progress_percent=-1)
        with pytest.raises(ValueError):
            WordCountTracking(progress_percent=101)

    def test_values_must_be_non_negative(self) -> None:
        """Test that values must be non-negative."""
        with pytest.raises(ValueError):
            WordCountTracking(target=-1)
        with pytest.raises(ValueError):
            WordCountTracking(current=-1)
        with pytest.raises(ValueError):
            WordCountTracking(remaining=-1)


class TestSplitGeneration:
    """Tests for SplitGeneration model."""

    def test_default_values(self) -> None:
        """Test default values (no split)."""
        split = SplitGeneration()
        assert split.total_parts == 1
        assert split.current_part == 1
        assert split.completed_sections == []

    def test_with_split(self) -> None:
        """Test with split generation in progress."""
        split = SplitGeneration(
            total_parts=3,
            current_part=2,
            completed_sections=["はじめに", "基本知識"],
        )
        assert split.total_parts == 3
        assert split.current_part == 2
        assert len(split.completed_sections) == 2

    def test_parts_bounds(self) -> None:
        """Test that parts are bounded 1-5."""
        with pytest.raises(ValueError):
            SplitGeneration(total_parts=0)
        with pytest.raises(ValueError):
            SplitGeneration(total_parts=6)
        with pytest.raises(ValueError):
            SplitGeneration(current_part=0)
        with pytest.raises(ValueError):
            SplitGeneration(current_part=6)


class TestStep7aOutputExtensions:
    """Tests for Step7aOutput with blog.System Ver8.3 extensions."""

    def test_backward_compatibility(self) -> None:
        """Test that existing fields still work."""
        output = Step7aOutput(keyword="SEO対策")
        assert output.keyword == "SEO対策"
        assert output.step == "step7a"
        assert output.draft == ""
        assert output.sections == []
        assert output.section_count == 0
        assert isinstance(output.quality_metrics, DraftQualityMetrics)
        assert isinstance(output.quality, DraftQuality)
        assert isinstance(output.stats, GenerationStats)

    def test_new_fields_have_defaults(self) -> None:
        """Test that new fields have proper defaults."""
        output = Step7aOutput(keyword="SEO対策")
        assert output.section_word_counts == []
        assert output.four_pillars_implementation == []
        assert isinstance(output.cta_implementation, CTAImplementation)
        assert isinstance(output.word_count_tracking, WordCountTracking)
        assert isinstance(output.split_generation, SplitGeneration)

    def test_full_output_with_extensions(self) -> None:
        """Test creating full output with all extensions."""
        output = Step7aOutput(
            keyword="SEO対策",
            draft="# SEOとは\n\nSEOとは...",
            section_count=5,
            section_word_counts=[
                SectionWordCount(
                    section_title="はじめに",
                    target=500,
                    actual=480,
                    variance=-20,
                    is_within_tolerance=True,
                ),
                SectionWordCount(
                    section_title="SEOとは",
                    target=600,
                    actual=650,
                    variance=50,
                    is_within_tolerance=True,
                ),
            ],
            four_pillars_implementation=[
                FourPillarsImplementation(
                    section_title="はじめに",
                    neuroscience=NeuroscienceImplementation(applied=True, details="好奇心"),
                    behavioral_economics=BehavioralEconomicsImplementation(principles_used=["社会的証明"]),
                    llmo=LLMOImplementation(token_count=480, is_independent=True),
                    kgi=KGIImplementation(cta_present=False),
                ),
            ],
            cta_implementation=CTAImplementation(
                early=CTAPosition(position=1, implemented=True),
                mid=CTAPosition(position=3, implemented=True),
                final=CTAPosition(position=5, implemented=True),
            ),
            word_count_tracking=WordCountTracking(
                target=5000,
                current=5000,
                remaining=0,
                progress_percent=100.0,
            ),
            split_generation=SplitGeneration(
                total_parts=1,
                current_part=1,
                completed_sections=["はじめに", "SEOとは", "具体的な方法", "注意点", "まとめ"],
            ),
        )
        assert len(output.section_word_counts) == 2
        assert len(output.four_pillars_implementation) == 1
        assert output.cta_implementation.early.implemented is True
        assert output.word_count_tracking.progress_percent == 100.0
        assert len(output.split_generation.completed_sections) == 5

    def test_serialization(self) -> None:
        """Test that output can be serialized to dict."""
        output = Step7aOutput(
            keyword="テスト",
            section_word_counts=[SectionWordCount(section_title="Test", target=100, actual=100)],
        )
        data = output.model_dump()
        assert isinstance(data, dict)
        assert "section_word_counts" in data
        assert data["section_word_counts"][0]["section_title"] == "Test"
        assert "four_pillars_implementation" in data
        assert "cta_implementation" in data
        assert "word_count_tracking" in data
        assert "split_generation" in data


class TestDraftSection:
    """Tests for existing DraftSection model (ensuring no regression)."""

    def test_default_values(self) -> None:
        """Test default values."""
        section = DraftSection()
        assert section.level == 2
        assert section.title == ""
        assert section.content == ""
        assert section.word_count == 0
        assert section.has_subheadings is False

    def test_with_values(self) -> None:
        """Test with explicit values."""
        section = DraftSection(
            level=3,
            title="サブセクション",
            content="内容...",
            word_count=100,
            has_subheadings=True,
        )
        assert section.level == 3
        assert section.title == "サブセクション"

    def test_level_bounds(self) -> None:
        """Test that level is bounded 1-4."""
        with pytest.raises(ValueError):
            DraftSection(level=0)
        with pytest.raises(ValueError):
            DraftSection(level=5)
