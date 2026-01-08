"""Unit tests for Step4 schemas.

blog.System Ver8.3 対応:
- TitleMetadata: タイトルルール検証
- ThreePhaseStructure: 3フェーズ構成
- SectionFourPillars: セクション別4本柱実装
- CTAPlacements: 3段階CTA配置
- WordCountTracking: 文字数管理
"""

import pytest
from pydantic import ValidationError

from apps.worker.activities.schemas.step4 import (
    BehavioralEconomicsConfig,
    CTAPlacements,
    CTAPosition,
    KGIConfig,
    LLMOConfig,
    NeuroscienceConfig,
    OutlineMetrics,
    OutlineQuality,
    OutlineSection,
    PhaseSection,
    SectionFourPillars,
    Step4Output,
    ThreePhaseStructure,
    TitleMetadata,
    WordCountTracking,
)


class TestOutlineSectionSchema:
    """OutlineSection schema tests."""

    def test_outline_section_minimal(self) -> None:
        """Test OutlineSection with minimal required fields."""
        section = OutlineSection(level=2, title="テストセクション")
        assert section.level == 2
        assert section.title == "テストセクション"
        assert section.description == ""
        assert section.target_word_count == 0

    def test_outline_section_with_subsections(self) -> None:
        """Test OutlineSection with nested subsections."""
        section = OutlineSection(
            level=2,
            title="親セクション",
            subsections=[
                OutlineSection(level=3, title="子セクション1"),
                OutlineSection(level=3, title="子セクション2"),
            ],
        )
        assert len(section.subsections) == 2
        assert section.subsections[0].level == 3

    def test_outline_section_level_validation(self) -> None:
        """Test level must be between 1 and 4."""
        with pytest.raises(ValidationError):
            OutlineSection(level=0, title="Invalid")
        with pytest.raises(ValidationError):
            OutlineSection(level=5, title="Invalid")


class TestTitleMetadataSchema:
    """TitleMetadata schema tests."""

    def test_title_metadata_creation(self) -> None:
        """Test TitleMetadata creation."""
        metadata = TitleMetadata(
            char_count=32,
            contains_number=True,
            contains_keyword=True,
            no_brackets=True,
            validation_passed=True,
        )
        assert metadata.char_count == 32
        assert metadata.validation_passed is True

    def test_title_metadata_with_issues(self) -> None:
        """Test TitleMetadata with validation issues."""
        metadata = TitleMetadata(
            char_count=50,
            contains_number=False,
            contains_keyword=False,
            no_brackets=False,
            validation_passed=False,
            issues=["文字数超過", "数字なし", "キーワードなし", "括弧あり"],
        )
        assert len(metadata.issues) == 4
        assert metadata.validation_passed is False

    def test_title_metadata_defaults(self) -> None:
        """Test TitleMetadata default values."""
        metadata = TitleMetadata()
        assert metadata.char_count == 0
        assert metadata.contains_number is False
        assert metadata.no_brackets is True
        assert metadata.issues == []


class TestNeuroscienceConfigSchema:
    """NeuroscienceConfig schema tests."""

    def test_neuroscience_config_creation(self) -> None:
        """Test NeuroscienceConfig creation."""
        config = NeuroscienceConfig(
            cognitive_load="low",
            phase="1",
            attention_hooks=["驚き", "疑問"],
        )
        assert config.cognitive_load == "low"
        assert config.phase == "1"
        assert len(config.attention_hooks) == 2

    def test_neuroscience_config_defaults(self) -> None:
        """Test NeuroscienceConfig default values."""
        config = NeuroscienceConfig()
        assert config.cognitive_load == "medium"
        assert config.phase == "2"
        assert config.attention_hooks == []


class TestBehavioralEconomicsConfigSchema:
    """BehavioralEconomicsConfig schema tests."""

    def test_behavioral_economics_config_creation(self) -> None:
        """Test BehavioralEconomicsConfig creation."""
        config = BehavioralEconomicsConfig(
            principles_applied=["損失回避", "社会的証明", "希少性"],
            bias_triggers=["フレーミング効果"],
        )
        assert len(config.principles_applied) == 3
        assert "損失回避" in config.principles_applied

    def test_behavioral_economics_config_defaults(self) -> None:
        """Test BehavioralEconomicsConfig default values."""
        config = BehavioralEconomicsConfig()
        assert config.principles_applied == []
        assert config.bias_triggers == []


class TestLLMOConfigSchema:
    """LLMOConfig schema tests."""

    def test_llmo_config_creation(self) -> None:
        """Test LLMOConfig creation."""
        config = LLMOConfig(
            token_target=500,
            question_heading=True,
            structured_data=True,
        )
        assert config.token_target == 500
        assert config.question_heading is True

    def test_llmo_config_token_target_validation(self) -> None:
        """Test token_target must be between 100 and 1000."""
        with pytest.raises(ValidationError):
            LLMOConfig(token_target=50)
        with pytest.raises(ValidationError):
            LLMOConfig(token_target=1500)

    def test_llmo_config_defaults(self) -> None:
        """Test LLMOConfig default values."""
        config = LLMOConfig()
        assert config.token_target == 500
        assert config.question_heading is False


class TestKGIConfigSchema:
    """KGIConfig schema tests."""

    def test_kgi_config_creation(self) -> None:
        """Test KGIConfig creation."""
        config = KGIConfig(
            cta_placement="early",
            conversion_goal="資料請求",
        )
        assert config.cta_placement == "early"
        assert config.conversion_goal == "資料請求"

    def test_kgi_config_defaults(self) -> None:
        """Test KGIConfig default values."""
        config = KGIConfig()
        assert config.cta_placement == "none"
        assert config.conversion_goal == ""


class TestSectionFourPillarsSchema:
    """SectionFourPillars schema tests."""

    def test_section_four_pillars_creation(self) -> None:
        """Test SectionFourPillars creation."""
        pillars = SectionFourPillars(
            section_title="SEOとは何か？",
            neuroscience=NeuroscienceConfig(cognitive_load="low", phase="1"),
            behavioral_economics=BehavioralEconomicsConfig(principles_applied=["損失回避"]),
            llmo=LLMOConfig(token_target=500, question_heading=True),
            kgi=KGIConfig(cta_placement="early"),
        )
        assert pillars.section_title == "SEOとは何か？"
        assert pillars.neuroscience.cognitive_load == "low"
        assert pillars.llmo.question_heading is True

    def test_section_four_pillars_defaults(self) -> None:
        """Test SectionFourPillars with default nested configs."""
        pillars = SectionFourPillars(section_title="テストセクション")
        assert pillars.neuroscience.cognitive_load == "medium"
        assert pillars.behavioral_economics.principles_applied == []
        assert pillars.llmo.token_target == 500
        assert pillars.kgi.cta_placement == "none"


class TestPhaseSectionSchema:
    """PhaseSection schema tests."""

    def test_phase_section_creation(self) -> None:
        """Test PhaseSection creation."""
        phase = PhaseSection(
            word_count_ratio=0.12,
            target_word_count=600,
            sections=["導入", "課題提起"],
        )
        assert phase.word_count_ratio == 0.12
        assert phase.target_word_count == 600
        assert len(phase.sections) == 2

    def test_phase_section_ratio_validation(self) -> None:
        """Test word_count_ratio must be between 0 and 1."""
        with pytest.raises(ValidationError):
            PhaseSection(word_count_ratio=-0.1)
        with pytest.raises(ValidationError):
            PhaseSection(word_count_ratio=1.5)

    def test_phase_section_defaults(self) -> None:
        """Test PhaseSection default values."""
        phase = PhaseSection()
        assert phase.word_count_ratio == 0.0
        assert phase.target_word_count == 0
        assert phase.sections == []


class TestThreePhaseStructureSchema:
    """ThreePhaseStructure schema tests."""

    def test_three_phase_structure_creation(self) -> None:
        """Test ThreePhaseStructure creation."""
        structure = ThreePhaseStructure(
            phase1=PhaseSection(word_count_ratio=0.12, sections=["導入"]),
            phase2=PhaseSection(word_count_ratio=0.70, sections=["本論1", "本論2"]),
            phase3=PhaseSection(word_count_ratio=0.18, sections=["まとめ"]),
            is_balanced=True,
        )
        assert structure.phase1.word_count_ratio == 0.12
        assert structure.phase2.word_count_ratio == 0.70
        assert structure.is_balanced is True

    def test_three_phase_structure_with_issues(self) -> None:
        """Test ThreePhaseStructure with balance issues."""
        structure = ThreePhaseStructure(
            is_balanced=False,
            balance_issues=["Phase1比率が範囲外", "Phase2比率が範囲外"],
        )
        assert structure.is_balanced is False
        assert len(structure.balance_issues) == 2

    def test_three_phase_structure_defaults(self) -> None:
        """Test ThreePhaseStructure default values."""
        structure = ThreePhaseStructure()
        assert structure.phase1.word_count_ratio == 0.0
        assert structure.is_balanced is False


class TestCTAPositionSchema:
    """CTAPosition schema tests."""

    def test_cta_position_creation(self) -> None:
        """Test CTAPosition creation."""
        position = CTAPosition(
            position=650,
            section="導入セクション",
            cta_type="資料請求",
        )
        assert position.position == 650
        assert position.section == "導入セクション"
        assert position.cta_type == "資料請求"

    def test_cta_position_defaults(self) -> None:
        """Test CTAPosition default values."""
        position = CTAPosition()
        assert position.position == 0
        assert position.section == ""
        assert position.cta_type == ""


class TestCTAPlacementsSchema:
    """CTAPlacements schema tests."""

    def test_cta_placements_creation(self) -> None:
        """Test CTAPlacements creation."""
        placements = CTAPlacements(
            early=CTAPosition(position=650, section="導入", cta_type="資料請求"),
            mid=CTAPosition(position=2800, section="本論", cta_type="無料相談"),
            final=CTAPosition(position=4500, section="まとめ", cta_type="問い合わせ"),
        )
        assert placements.early is not None
        assert placements.early.position == 650
        assert placements.mid is not None
        assert placements.final is not None

    def test_cta_placements_partial(self) -> None:
        """Test CTAPlacements with partial CTAs."""
        placements = CTAPlacements(
            early=CTAPosition(position=650, section="導入"),
        )
        assert placements.early is not None
        assert placements.mid is None
        assert placements.final is None

    def test_cta_placements_defaults(self) -> None:
        """Test CTAPlacements default values."""
        placements = CTAPlacements()
        assert placements.early is None
        assert placements.mid is None
        assert placements.final is None


class TestWordCountTrackingSchema:
    """WordCountTracking schema tests."""

    def test_word_count_tracking_creation(self) -> None:
        """Test WordCountTracking creation."""
        tracking = WordCountTracking(
            target=5000,
            sections_total=4800,
            variance=-200,
            variance_percentage=-4.0,
            is_within_tolerance=True,
        )
        assert tracking.target == 5000
        assert tracking.sections_total == 4800
        assert tracking.variance == -200
        assert tracking.is_within_tolerance is True

    def test_word_count_tracking_out_of_tolerance(self) -> None:
        """Test WordCountTracking when out of tolerance."""
        tracking = WordCountTracking(
            target=5000,
            sections_total=3500,
            variance=-1500,
            variance_percentage=-30.0,
            is_within_tolerance=False,
        )
        assert tracking.is_within_tolerance is False
        assert tracking.variance_percentage == -30.0

    def test_word_count_tracking_defaults(self) -> None:
        """Test WordCountTracking default values."""
        tracking = WordCountTracking()
        assert tracking.target == 0
        assert tracking.sections_total == 0
        assert tracking.is_within_tolerance is False


class TestStep4OutputSchema:
    """Step4Output schema tests."""

    def test_step4_output_minimal(self) -> None:
        """Test Step4Output with minimal required fields."""
        output = Step4Output(
            keyword="SEO対策",
            outline="# SEO対策の基本",
            metrics=OutlineMetrics(
                word_count=100,
                char_count=150,
                h2_count=3,
                h3_count=5,
                h4_count=0,
            ),
            quality=OutlineQuality(is_acceptable=True),
        )
        assert output.step == "step4"
        assert output.keyword == "SEO対策"
        assert output.metrics.h2_count == 3

    def test_step4_output_backward_compatible(self) -> None:
        """Test Step4Output is backward compatible (no V2 fields required)."""
        output = Step4Output(
            keyword="テスト",
            outline="テストアウトライン",
            metrics=OutlineMetrics(word_count=50, char_count=100, h2_count=2, h3_count=0, h4_count=0),
            quality=OutlineQuality(is_acceptable=True),
        )
        assert output.title_metadata is None
        assert output.three_phase_structure is None
        assert output.four_pillars_per_section == []
        assert output.cta_placements is None
        assert output.word_count_tracking is None

    def test_step4_output_with_v2_fields(self) -> None:
        """Test Step4Output with V2 fields."""
        output = Step4Output(
            keyword="SEO対策",
            article_title="SEO対策完全ガイド2025年版",
            outline="# SEO対策の基本",
            metrics=OutlineMetrics(
                word_count=5000,
                char_count=7500,
                h2_count=5,
                h3_count=10,
                h4_count=0,
            ),
            quality=OutlineQuality(is_acceptable=True),
            title_metadata=TitleMetadata(
                char_count=18,
                contains_number=True,
                contains_keyword=True,
                no_brackets=True,
                validation_passed=True,
            ),
            three_phase_structure=ThreePhaseStructure(
                phase1=PhaseSection(word_count_ratio=0.12),
                phase2=PhaseSection(word_count_ratio=0.70),
                phase3=PhaseSection(word_count_ratio=0.18),
                is_balanced=True,
            ),
            four_pillars_per_section=[
                SectionFourPillars(section_title="導入"),
                SectionFourPillars(section_title="本論"),
            ],
            cta_placements=CTAPlacements(
                early=CTAPosition(position=650),
                mid=CTAPosition(position=2800),
                final=CTAPosition(position=4500),
            ),
            word_count_tracking=WordCountTracking(
                target=5000,
                sections_total=5000,
                is_within_tolerance=True,
            ),
        )
        assert output.title_metadata is not None
        assert output.title_metadata.validation_passed is True
        assert output.three_phase_structure is not None
        assert output.three_phase_structure.is_balanced is True
        assert len(output.four_pillars_per_section) == 2
        assert output.cta_placements is not None
        assert output.word_count_tracking is not None

    def test_step4_output_serialization(self) -> None:
        """Test Step4Output serialization."""
        output = Step4Output(
            keyword="テスト",
            outline="テストアウトライン",
            metrics=OutlineMetrics(word_count=50, char_count=100, h2_count=2, h3_count=0, h4_count=0),
            quality=OutlineQuality(is_acceptable=True),
            title_metadata=TitleMetadata(char_count=10, validation_passed=True),
        )
        data = output.model_dump()
        assert data["step"] == "step4"
        assert data["title_metadata"]["char_count"] == 10
        assert data["title_metadata"]["validation_passed"] is True

    def test_step4_output_deserialization(self) -> None:
        """Test Step4Output deserialization."""
        data = {
            "keyword": "テスト",
            "outline": "テストアウトライン",
            "metrics": {
                "word_count": 50,
                "char_count": 100,
                "h2_count": 2,
                "h3_count": 0,
                "h4_count": 0,
            },
            "quality": {"is_acceptable": True},
            "title_metadata": {
                "char_count": 32,
                "contains_number": True,
                "contains_keyword": True,
                "no_brackets": True,
                "validation_passed": True,
            },
        }
        output = Step4Output.model_validate(data)
        assert output.keyword == "テスト"
        assert output.title_metadata is not None
        assert output.title_metadata.char_count == 32
