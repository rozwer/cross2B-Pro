"""Step 6.5 schema tests.

Tests for backward compatibility and new blog.System Ver8.3 fields.

Note: Import directly from step6_5.py to avoid activities/__init__.py import issues.
"""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

# Add project root to path for direct import
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Import directly from schema file to avoid activities/__init__.py
from apps.worker.activities.schemas.step6_5 import (
    ComprehensiveBlueprint,
    FourPillarsFinalCheck,
    InputSummary,
    PackageQuality,
    ReferenceData,
    SectionBlueprint,
    SectionExecutionInstruction,
    Step6_5Output,
    VisualElementInstruction,
)


class TestStep6_5OutputBackwardCompatibility:
    """Test that existing data format still works."""

    def test_step6_5_output_with_existing_fields_only(self):
        """既存データ形式でも動作することを確認."""
        old_data = {
            "keyword": "テストキーワード",  # StepOutputBase required
            "integration_package": "統合パッケージテキスト",
            "article_blueprint": {"title": "記事タイトル"},
            "section_blueprints": [SectionBlueprint(title="セクション1", target_words=500)],
            "outline_summary": "概要サマリー",
            "section_count": 5,
            "total_sources": 10,
            "input_summaries": [InputSummary(step_id="step3a", available=True, data_quality="good")],
            "inputs_summary": {"step3a": True, "step3b": True},
            "quality": PackageQuality(is_acceptable=True, scores={"overall": 0.85}),
            "quality_score": 0.85,
            "handoff_notes": ["工程7への引き継ぎメモ"],
            "model": "gemini-1.5-pro",
            "usage": {"input_tokens": 1000, "output_tokens": 500},
        }
        output = Step6_5Output(**old_data)

        assert output.step == "step6_5"
        assert output.integration_package == "統合パッケージテキスト"
        assert output.section_count == 5
        assert output.quality_score == 0.85
        # 新フィールドは None またはデフォルト
        assert output.comprehensive_blueprint is None
        assert output.section_execution_instructions == []
        assert output.visual_element_instructions == []
        assert output.four_pillars_final_check is None

    def test_step6_5_output_minimal_fields(self):
        """最小限のフィールドで動作確認."""
        output = Step6_5Output(keyword="テスト")  # StepOutputBase required

        assert output.step == "step6_5"
        assert output.keyword == "テスト"
        assert output.integration_package == ""
        assert output.section_blueprints == []
        assert output.quality_score == 0.0
        assert output.comprehensive_blueprint is None


class TestReferenceData:
    """Test ReferenceData model."""

    def test_reference_data_creation(self):
        """ReferenceData の作成."""
        ref = ReferenceData(
            keywords=["SEO", "記事作成", "ブログ"],
            sources=["[S1] 厚労省統計", "[S2] 民間調査"],
            human_touch_elements=["共感フレーズ", "体験談"],
            cta_placements=["記事末尾", "中間セクション"],
        )

        assert len(ref.keywords) == 3
        assert ref.keywords[0] == "SEO"
        assert len(ref.sources) == 2
        assert len(ref.human_touch_elements) == 2
        assert len(ref.cta_placements) == 2

    def test_reference_data_defaults(self):
        """ReferenceData のデフォルト値."""
        ref = ReferenceData()

        assert ref.keywords == []
        assert ref.sources == []
        assert ref.human_touch_elements == []
        assert ref.cta_placements == []


class TestComprehensiveBlueprint:
    """Test ComprehensiveBlueprint model."""

    def test_comprehensive_blueprint_creation(self):
        """ComprehensiveBlueprint の作成."""
        blueprint = ComprehensiveBlueprint(
            part1_outline="# タイトル\n## セクション1\n## セクション2",
            part2_reference_data=ReferenceData(
                keywords=["キーワード1"],
                sources=["ソース1"],
            ),
        )

        assert "タイトル" in blueprint.part1_outline
        assert len(blueprint.part2_reference_data.keywords) == 1

    def test_comprehensive_blueprint_defaults(self):
        """ComprehensiveBlueprint のデフォルト値."""
        blueprint = ComprehensiveBlueprint()

        assert blueprint.part1_outline == ""
        assert blueprint.part2_reference_data.keywords == []

    def test_comprehensive_blueprint_nested_access(self):
        """ネストした ReferenceData へのアクセス."""
        blueprint = ComprehensiveBlueprint(
            part2_reference_data=ReferenceData(
                keywords=["KW1", "KW2"],
                human_touch_elements=["共感"],
            )
        )

        assert blueprint.part2_reference_data.keywords[1] == "KW2"
        assert blueprint.part2_reference_data.human_touch_elements[0] == "共感"


class TestSectionExecutionInstruction:
    """Test SectionExecutionInstruction model."""

    def test_section_execution_instruction_creation(self):
        """SectionExecutionInstruction の作成."""
        instruction = SectionExecutionInstruction(
            section_title="SEOの基本",
            logic_flow="PREP: Point→Reason→Example→Point",
            key_points=["検索エンジンの仕組み", "キーワード選定の重要性"],
            sources_to_cite=["[S1]", "[S2]"],
            keywords_to_include=["SEO", "検索エンジン最適化"],
            human_touch_to_apply=["読者への問いかけ"],
            word_count_target=800,
        )

        assert instruction.section_title == "SEOの基本"
        assert "PREP" in instruction.logic_flow
        assert len(instruction.key_points) == 2
        assert instruction.word_count_target == 800

    def test_section_execution_instruction_required_field(self):
        """section_title は必須."""
        with pytest.raises(ValidationError) as exc_info:
            SectionExecutionInstruction()

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("section_title",) for e in errors)

    def test_section_execution_instruction_word_count_non_negative(self):
        """word_count_target は 0 以上."""
        with pytest.raises(ValidationError) as exc_info:
            SectionExecutionInstruction(
                section_title="テスト",
                word_count_target=-100,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("word_count_target",) for e in errors)


class TestVisualElementInstruction:
    """Test VisualElementInstruction model."""

    def test_visual_element_instruction_creation(self):
        """VisualElementInstruction の作成."""
        instruction = VisualElementInstruction(
            element_type="table",
            placement_section="比較セクション",
            content_description="競合3社の機能比較表",
            purpose="視覚的に比較ポイントを明確化",
        )

        assert instruction.element_type == "table"
        assert instruction.placement_section == "比較セクション"
        assert "競合" in instruction.content_description
        assert "視覚的" in instruction.purpose

    def test_visual_element_instruction_required_fields(self):
        """element_type と placement_section は必須."""
        with pytest.raises(ValidationError) as exc_info:
            VisualElementInstruction()

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("element_type",) for e in errors)
        assert any(e["loc"] == ("placement_section",) for e in errors)

    def test_visual_element_instruction_various_types(self):
        """各種要素タイプ."""
        types = ["table", "chart", "diagram", "image"]
        for elem_type in types:
            instruction = VisualElementInstruction(
                element_type=elem_type,
                placement_section="セクション",
            )
            assert instruction.element_type == elem_type


class TestFourPillarsFinalCheck:
    """Test FourPillarsFinalCheck model."""

    def test_four_pillars_final_check_creation(self):
        """FourPillarsFinalCheck の作成."""
        check = FourPillarsFinalCheck(
            all_sections_compliant=True,
            neuroscience_coverage=0.85,
            behavioral_economics_coverage=0.75,
            llmo_coverage=0.90,
            kgi_coverage=0.80,
            issues=[],
            recommendations=["行動経済学要素を強化"],
        )

        assert check.all_sections_compliant is True
        assert check.neuroscience_coverage == 0.85
        assert check.behavioral_economics_coverage == 0.75
        assert check.llmo_coverage == 0.90
        assert check.kgi_coverage == 0.80
        assert len(check.recommendations) == 1

    def test_four_pillars_final_check_defaults(self):
        """FourPillarsFinalCheck のデフォルト値."""
        check = FourPillarsFinalCheck()

        assert check.all_sections_compliant is False
        assert check.neuroscience_coverage == 0.0
        assert check.behavioral_economics_coverage == 0.0
        assert check.llmo_coverage == 0.0
        assert check.kgi_coverage == 0.0
        assert check.issues == []
        assert check.recommendations == []

    def test_four_pillars_final_check_coverage_range(self):
        """カバー率が 0-1 の範囲."""
        # 正常値
        check = FourPillarsFinalCheck(
            neuroscience_coverage=0.5,
            behavioral_economics_coverage=1.0,
            llmo_coverage=0.0,
            kgi_coverage=0.99,
        )
        assert check.neuroscience_coverage == 0.5

        # 範囲外（上限超過）
        with pytest.raises(ValidationError):
            FourPillarsFinalCheck(neuroscience_coverage=1.5)

        # 範囲外（下限超過）
        with pytest.raises(ValidationError):
            FourPillarsFinalCheck(llmo_coverage=-0.1)

    def test_four_pillars_with_issues(self):
        """問題点がある場合."""
        check = FourPillarsFinalCheck(
            all_sections_compliant=False,
            neuroscience_coverage=0.2,
            issues=["神経科学要素がセクション3,5で不足", "KGI要素が導入部で欠如"],
            recommendations=["損失回避フレーズを追加", "数値目標を明示"],
        )

        assert check.all_sections_compliant is False
        assert len(check.issues) == 2
        assert len(check.recommendations) == 2


class TestStep6_5OutputWithNewFields:
    """Test Step6_5Output with new blog.System fields."""

    def test_step6_5_output_with_all_new_fields(self):
        """全ての新フィールドを持つ Step6_5Output."""
        output = Step6_5Output(
            keyword="テストキーワード",  # StepOutputBase required
            integration_package="統合パッケージ",
            section_count=5,
            comprehensive_blueprint=ComprehensiveBlueprint(
                part1_outline="構成案",
                part2_reference_data=ReferenceData(keywords=["KW1"]),
            ),
            section_execution_instructions=[
                SectionExecutionInstruction(
                    section_title="セクション1",
                    word_count_target=500,
                ),
                SectionExecutionInstruction(
                    section_title="セクション2",
                    word_count_target=700,
                ),
            ],
            visual_element_instructions=[
                VisualElementInstruction(
                    element_type="table",
                    placement_section="セクション1",
                ),
            ],
            four_pillars_final_check=FourPillarsFinalCheck(
                all_sections_compliant=True,
                neuroscience_coverage=0.8,
                behavioral_economics_coverage=0.7,
                llmo_coverage=0.9,
                kgi_coverage=0.85,
            ),
        )

        assert output.comprehensive_blueprint is not None
        assert output.comprehensive_blueprint.part1_outline == "構成案"
        assert len(output.section_execution_instructions) == 2
        assert output.section_execution_instructions[0].section_title == "セクション1"
        assert len(output.visual_element_instructions) == 1
        assert output.four_pillars_final_check is not None
        assert output.four_pillars_final_check.all_sections_compliant is True

    def test_step6_5_output_partial_new_fields(self):
        """一部の新フィールドのみ設定."""
        output = Step6_5Output(
            keyword="テストキーワード",  # StepOutputBase required
            integration_package="統合パッケージ",
            section_execution_instructions=[
                SectionExecutionInstruction(
                    section_title="テスト",
                    logic_flow="PREP",
                ),
            ],
            # comprehensive_blueprint と four_pillars_final_check は None
        )

        assert output.comprehensive_blueprint is None
        assert len(output.section_execution_instructions) == 1
        assert output.visual_element_instructions == []
        assert output.four_pillars_final_check is None


class TestStep6_5OutputSerialization:
    """Test serialization/deserialization."""

    def test_model_dump_includes_new_fields(self):
        """model_dump() に新フィールドが含まれる."""
        output = Step6_5Output(
            keyword="テスト",  # StepOutputBase required
            integration_package="テスト",
            comprehensive_blueprint=ComprehensiveBlueprint(part1_outline="概要"),
        )
        dumped = output.model_dump()

        assert "comprehensive_blueprint" in dumped
        assert "section_execution_instructions" in dumped
        assert "visual_element_instructions" in dumped
        assert "four_pillars_final_check" in dumped
        assert dumped["comprehensive_blueprint"]["part1_outline"] == "概要"

    def test_model_dump_excludes_none(self):
        """exclude_none=True で None フィールドを除外."""
        output = Step6_5Output(
            keyword="テスト",  # StepOutputBase required
            integration_package="テスト",
        )
        dumped = output.model_dump(exclude_none=True)

        # None のフィールドは除外される
        assert "comprehensive_blueprint" not in dumped
        assert "four_pillars_final_check" not in dumped
        # 空リストは除外されない
        assert "section_execution_instructions" in dumped

    def test_nested_serialization(self):
        """ネストした構造のシリアライズ."""
        output = Step6_5Output(
            keyword="テスト",  # StepOutputBase required
            comprehensive_blueprint=ComprehensiveBlueprint(
                part2_reference_data=ReferenceData(
                    keywords=["KW1", "KW2"],
                    sources=["S1"],
                ),
            ),
        )
        dumped = output.model_dump()

        nested_keywords = dumped["comprehensive_blueprint"]["part2_reference_data"]["keywords"]
        assert nested_keywords == ["KW1", "KW2"]


class TestInputSummary:
    """InputSummary tests (existing)."""

    def test_input_summary_creation(self):
        """InputSummary の作成."""
        summary = InputSummary(
            step_id="step3a",
            available=True,
            key_points=["クエリ分析完了", "意図判定: 情報収集"],
            data_quality="good",
        )

        assert summary.step_id == "step3a"
        assert summary.available is True
        assert len(summary.key_points) == 2
        assert summary.data_quality == "good"


class TestSectionBlueprint:
    """SectionBlueprint tests (existing)."""

    def test_section_blueprint_creation(self):
        """SectionBlueprint の作成."""
        blueprint = SectionBlueprint(
            level=2,
            title="SEOの基本",
            target_words=800,
            key_points=["検索エンジンの仕組み"],
            sources_to_cite=["[S1]"],
            keywords_to_include=["SEO"],
        )

        assert blueprint.level == 2
        assert blueprint.title == "SEOの基本"
        assert blueprint.target_words == 800

    def test_section_blueprint_level_range(self):
        """level は 1-4 の範囲."""
        with pytest.raises(ValidationError):
            SectionBlueprint(level=0)

        with pytest.raises(ValidationError):
            SectionBlueprint(level=5)


class TestPackageQuality:
    """PackageQuality tests (existing)."""

    def test_package_quality_creation(self):
        """PackageQuality の作成."""
        quality = PackageQuality(
            is_acceptable=True,
            issues=[],
            warnings=["ソース数が少ない"],
            scores={"completeness": 0.85, "coherence": 0.90},
        )

        assert quality.is_acceptable is True
        assert len(quality.warnings) == 1
        assert quality.scores["completeness"] == 0.85
