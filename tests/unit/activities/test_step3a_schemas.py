"""Step 3A schema tests.

Tests for Step3A schemas including:
- Backward compatibility with existing schemas
- New blog.System Ver8.3 schemas (CoreQuestion, BehavioralEconomicsProfile, etc.)
- V2 output schema (Step3aOutputV2)
"""

import pytest
from pydantic import ValidationError

from apps.worker.activities.schemas.step3a import (
    BehavioralEconomicsPrinciple,
    # 新規スキーマ（blog.System Ver8.3）
    BehavioralEconomicsProfile,
    CoreQuestion,
    DetailedPersona,
    EmotionalState,
    Phase1Anxiety,
    Phase2Understanding,
    Phase3Action,
    PhaseState,
    QuestionHierarchy,
    # 既存スキーマ
    SearchIntent,
    SearchScenario,
    Step3aOutput,
    Step3aOutputV2,
    ThreePhaseMapping,
    UserPersona,
)


class TestSearchIntentBackwardCompatibility:
    """Test SearchIntent backward compatibility."""

    def test_search_intent_basic(self):
        """基本的な検索意図の作成."""
        intent = SearchIntent(primary="informational")
        assert intent.primary == "informational"
        assert intent.secondary == []
        assert intent.confidence == 0.5

    def test_search_intent_all_types(self):
        """全タイプの検索意図."""
        for intent_type in ["informational", "navigational", "transactional", "commercial"]:
            intent = SearchIntent(primary=intent_type)
            assert intent.primary == intent_type

    def test_search_intent_with_secondary(self):
        """二次的意図付きの検索意図."""
        intent = SearchIntent(
            primary="commercial",
            secondary=["informational", "transactional"],
            confidence=0.85,
        )
        assert intent.secondary == ["informational", "transactional"]
        assert intent.confidence == 0.85

    def test_search_intent_confidence_bounds(self):
        """confidence の境界値テスト."""
        # 有効な値
        SearchIntent(primary="informational", confidence=0.0)
        SearchIntent(primary="informational", confidence=1.0)

        # 無効な値
        with pytest.raises(ValidationError):
            SearchIntent(primary="informational", confidence=-0.1)
        with pytest.raises(ValidationError):
            SearchIntent(primary="informational", confidence=1.1)


class TestUserPersonaBackwardCompatibility:
    """Test UserPersona backward compatibility."""

    def test_user_persona_minimal(self):
        """最小限のペルソナ."""
        persona = UserPersona(name="田中太郎")
        assert persona.name == "田中太郎"
        assert persona.demographics == ""
        assert persona.goals == []
        assert persona.pain_points == []

    def test_user_persona_full(self):
        """全フィールド付きペルソナ."""
        persona = UserPersona(
            name="鈴木花子",
            demographics="30代女性、東京都在住",
            goals=["売上向上", "業務効率化"],
            pain_points=["人手不足", "予算制約"],
            search_context="業務中にスマホで検索",
        )
        assert persona.goals == ["売上向上", "業務効率化"]
        assert len(persona.pain_points) == 2


class TestStep3aOutputBackwardCompatibility:
    """Test Step3aOutput backward compatibility."""

    def test_step3a_output_minimal(self):
        """最小限の出力."""
        output = Step3aOutput(
            keyword="派遣社員 教育方法",
            search_intent=SearchIntent(primary="commercial"),
            raw_analysis="分析結果...",
        )
        assert output.keyword == "派遣社員 教育方法"
        assert output.personas == []
        assert output.recommended_tone == ""

    def test_step3a_output_full(self):
        """全フィールド付き出力."""
        output = Step3aOutput(
            keyword="派遣社員 教育方法",
            search_intent=SearchIntent(primary="commercial", confidence=0.8),
            personas=[
                UserPersona(name="人事担当者", goals=["定着率向上"]),
            ],
            content_expectations=["具体的な方法", "事例"],
            recommended_tone="実践的で共感的",
            raw_analysis="詳細な分析...",
        )
        assert len(output.personas) == 1
        assert output.recommended_tone == "実践的で共感的"


# =============================================================================
# 新規スキーマテスト（blog.System Ver8.3）
# =============================================================================


class TestCoreQuestion:
    """Test CoreQuestion schema."""

    def test_core_question_minimal(self):
        """最小限の核心的疑問."""
        cq = CoreQuestion(primary="派遣社員を定着させる効果的な方法は？")
        assert "定着" in cq.primary
        assert cq.time_sensitivity == "medium"
        assert cq.sub_questions == []

    def test_core_question_full(self):
        """全フィールド付き核心的疑問."""
        cq = CoreQuestion(
            primary="派遣社員を定着させる効果的な方法は？",
            underlying_concern="採用コストの増加と組織の疲弊",
            time_sensitivity="high",
            urgency_reason="経営層から改善指示",
            sub_questions=[
                "教育期間はどれくらい必要か？",
                "OJTとOff-JTの比率は？",
                "メンター制度は有効か？",
            ],
        )
        assert cq.time_sensitivity == "high"
        assert len(cq.sub_questions) == 3


class TestQuestionHierarchy:
    """Test QuestionHierarchy schema."""

    def test_question_hierarchy_minimal(self):
        """最小限の階層構造."""
        qh = QuestionHierarchy()
        assert qh.level_1_primary == []
        assert qh.level_2_secondary == {}

    def test_question_hierarchy_full(self):
        """全フィールド付き階層構造."""
        qh = QuestionHierarchy(
            level_1_primary=[
                "教育方法は？",
                "期間は？",
                "効果測定は？",
            ],
            level_2_secondary={
                "教育方法は？": ["OJTの進め方", "Off-JTの内容"],
                "期間は？": ["初期研修", "フォローアップ"],
            },
        )
        assert len(qh.level_1_primary) == 3
        assert len(qh.level_2_secondary["教育方法は？"]) == 2


class TestBehavioralEconomicsPrinciple:
    """Test BehavioralEconomicsPrinciple schema."""

    def test_principle_minimal(self):
        """最小限の原則."""
        p = BehavioralEconomicsPrinciple()
        assert p.trigger == ""
        assert p.examples == []
        assert p.content_strategy == ""

    def test_principle_full(self):
        """全フィールド付き原則."""
        p = BehavioralEconomicsPrinciple(
            trigger="採用コストの無駄",
            examples=[
                "年間320万円の損失",
                "離職率42%は10人中4人が退職",
            ],
            content_strategy="Phase 1で損失フレームを強調",
        )
        assert "320万" in p.examples[0]


class TestBehavioralEconomicsProfile:
    """Test BehavioralEconomicsProfile schema."""

    def test_profile_defaults(self):
        """デフォルト値の確認."""
        profile = BehavioralEconomicsProfile()
        assert profile.loss_aversion.trigger == ""
        assert profile.social_proof.trigger == ""
        assert profile.authority.trigger == ""
        assert profile.consistency.trigger == ""
        assert profile.liking.trigger == ""
        assert profile.scarcity.trigger == ""

    def test_profile_full(self):
        """全6原則付きプロファイル."""
        profile = BehavioralEconomicsProfile(
            loss_aversion=BehavioralEconomicsPrinciple(
                trigger="採用コスト損失",
                content_strategy="Phase 1で強調",
            ),
            social_proof=BehavioralEconomicsPrinciple(
                trigger="同業他社の成功事例",
                content_strategy="Phase 2で提示",
            ),
            authority=BehavioralEconomicsPrinciple(
                trigger="専門家の意見",
                content_strategy="Phase 2で引用",
            ),
            consistency=BehavioralEconomicsPrinciple(
                trigger="過去の行動との整合性",
                content_strategy="段階的CTA",
            ),
            liking=BehavioralEconomicsPrinciple(
                trigger="共感的なトーン",
                content_strategy="Phase 1で共感を示す",
            ),
            scarcity=BehavioralEconomicsPrinciple(
                trigger="期間限定の特典",
                content_strategy="Phase 3で適度な緊急性",
            ),
        )
        assert profile.loss_aversion.content_strategy == "Phase 1で強調"
        assert profile.scarcity.content_strategy == "Phase 3で適度な緊急性"


class TestPhaseState:
    """Test PhaseState and derived classes."""

    def test_phase_state_base(self):
        """基底クラスのテスト."""
        state = PhaseState(
            emotions=["不安", "焦り"],
            brain_trigger="衝撃的なデータ",
            content_strategy="共感を示す",
        )
        assert len(state.emotions) == 2
        assert state.brain_trigger == "衝撃的なデータ"

    def test_phase1_anxiety(self):
        """Phase 1: 不安・課題認識."""
        phase1 = Phase1Anxiety(
            emotions=["不安", "危機感", "焦り"],
            brain_trigger="離職率42%のデータ",
            content_needs=["課題の明確化", "解決の可能性"],
            content_strategy="共感→課題→希望の流れ",
        )
        assert "不安" in phase1.emotions
        assert phase1.brain_trigger == "離職率42%のデータ"

    def test_phase2_understanding(self):
        """Phase 2: 理解・納得."""
        phase2 = Phase2Understanding(
            emotions=["理解欲求", "比較検討"],
            brain_trigger="比較表とデータ",
            logic_points=["費用対効果", "導入難易度"],
            comparison_needs=["OJT vs Off-JT", "予算別プラン"],
        )
        assert len(phase2.logic_points) == 2
        assert len(phase2.comparison_needs) == 2

    def test_phase3_action(self):
        """Phase 3: 行動決定."""
        phase3 = Phase3Action(
            emotions=["決断", "期待"],
            brain_trigger="3ステップで開始可能",
            action_barriers=["予算承認", "時間確保"],
            urgency_factors=["法改正対応", "採用難"],
            cvr_targets={"early_cta": 3.0, "mid_cta": 4.0, "final_cta": 5.5},
        )
        assert len(phase3.action_barriers) == 2
        assert phase3.cvr_targets["final_cta"] == 5.5

    def test_phase3_default_cvr_targets(self):
        """Phase 3 のデフォルト CVR 目標."""
        phase3 = Phase3Action()
        assert phase3.cvr_targets == {"early_cta": 3.0, "mid_cta": 4.0, "final_cta": 5.0}


class TestThreePhaseMapping:
    """Test ThreePhaseMapping schema."""

    def test_three_phase_mapping_defaults(self):
        """デフォルト値の確認."""
        mapping = ThreePhaseMapping()
        assert mapping.phase1_anxiety.emotions == []
        assert mapping.phase2_understanding.logic_points == []
        assert mapping.phase3_action.cvr_targets["early_cta"] == 3.0

    def test_three_phase_mapping_full(self):
        """全フェーズ付きマッピング."""
        mapping = ThreePhaseMapping(
            phase1_anxiety=Phase1Anxiety(
                emotions=["不安"],
                brain_trigger="扁桃体活性化",
            ),
            phase2_understanding=Phase2Understanding(
                emotions=["理解"],
                brain_trigger="前頭前野活性化",
                logic_points=["データ分析"],
            ),
            phase3_action=Phase3Action(
                emotions=["決断"],
                brain_trigger="線条体活性化",
                cvr_targets={"early_cta": 4.0, "mid_cta": 5.0, "final_cta": 6.0},
            ),
        )
        assert mapping.phase1_anxiety.brain_trigger == "扁桃体活性化"
        assert mapping.phase3_action.cvr_targets["final_cta"] == 6.0


class TestSearchScenario:
    """Test SearchScenario schema."""

    def test_search_scenario_defaults(self):
        """デフォルト値の確認."""
        scenario = SearchScenario()
        assert scenario.trigger_event == ""
        assert scenario.conversion_likelihood == 0.0

    def test_search_scenario_full(self):
        """全フィールド付き検索シーン."""
        scenario = SearchScenario(
            trigger_event="派遣社員が退職した直後",
            search_timing="平日午前10時",
            device="会社PC",
            prior_knowledge="基礎知識あり",
            expected_action="資料DL or 問い合わせ",
            conversion_likelihood=35.0,
        )
        assert scenario.conversion_likelihood == 35.0

    def test_search_scenario_conversion_bounds(self):
        """conversion_likelihood の境界値テスト."""
        SearchScenario(conversion_likelihood=0.0)
        SearchScenario(conversion_likelihood=100.0)

        with pytest.raises(ValidationError):
            SearchScenario(conversion_likelihood=-1.0)
        with pytest.raises(ValidationError):
            SearchScenario(conversion_likelihood=101.0)


class TestEmotionalState:
    """Test EmotionalState schema."""

    def test_emotional_state_defaults(self):
        """デフォルト値の確認."""
        state = EmotionalState()
        assert state.anxiety_level == "medium"
        assert state.motivation_type == "loss_aversion"
        assert state.openness_to_external_help == "medium"

    def test_emotional_state_full(self):
        """全フィールド付き感情状態."""
        state = EmotionalState(
            anxiety_level="high",
            anxiety_sources=["経営層からのプレッシャー", "離職の連鎖"],
            urgency="high",
            urgency_reason="四半期評価前",
            motivation_type="loss_aversion",
            motivation_detail="年間320万円の採用コスト削減",
            confidence_level="low",
            openness_to_external_help="high",
        )
        assert state.anxiety_level == "high"
        assert len(state.anxiety_sources) == 2

    def test_emotional_state_invalid_values(self):
        """無効な値のテスト."""
        with pytest.raises(ValidationError):
            EmotionalState(anxiety_level="very_high")  # 無効なレベル
        with pytest.raises(ValidationError):
            EmotionalState(motivation_type="unknown")  # 無効なタイプ


class TestDetailedPersona:
    """Test DetailedPersona schema."""

    def test_detailed_persona_defaults(self):
        """デフォルト値の確認."""
        persona = DetailedPersona()
        assert persona.name == ""
        assert persona.age == 35
        assert persona.experience_years == 5

    def test_detailed_persona_full(self):
        """全フィールド付き拡張ペルソナ."""
        persona = DetailedPersona(
            name="鈴木太郎",
            age=42,
            job_title="人事部 教育研修課長",
            company_size="従業員150名の中堅企業",
            experience_years=15,
            department="人事部",
            responsibilities=["派遣社員教育", "研修企画", "定着率改善"],
            pain_points=[
                "離職率42%と高い",
                "教育予算が限られている",
                "専任スタッフがいない",
            ],
            goals=[
                "定着率60%以上に向上",
                "3ヶ月以内に教育体系構築",
            ],
            constraints=["予算50万円以下", "週10時間のみ"],
            search_scenario=SearchScenario(
                trigger_event="退職報告を受けた直後",
                conversion_likelihood=40.0,
            ),
            emotional_state=EmotionalState(
                anxiety_level="high",
                motivation_type="loss_aversion",
            ),
        )
        assert persona.age == 42
        assert len(persona.pain_points) == 3
        assert persona.search_scenario.conversion_likelihood == 40.0

    def test_detailed_persona_age_bounds(self):
        """age の境界値テスト."""
        DetailedPersona(age=18)
        DetailedPersona(age=80)

        with pytest.raises(ValidationError):
            DetailedPersona(age=17)
        with pytest.raises(ValidationError):
            DetailedPersona(age=81)


class TestStep3aOutputV2:
    """Test Step3aOutputV2 schema."""

    def test_v2_output_backward_compatible(self):
        """V1形式のデータでも動作."""
        output = Step3aOutputV2(
            keyword="派遣社員 教育方法",
            search_intent=SearchIntent(primary="commercial"),
            raw_analysis="分析結果...",
        )
        assert output.keyword == "派遣社員 教育方法"
        # 新規フィールドは None
        assert output.core_question is None
        assert output.behavioral_economics_profile is None
        assert output.three_phase_mapping is None

    def test_v2_output_with_new_fields(self):
        """新フィールド付きV2出力."""
        output = Step3aOutputV2(
            keyword="派遣社員 教育方法",
            search_intent=SearchIntent(primary="commercial", confidence=0.8),
            personas=[UserPersona(name="人事担当者")],
            raw_analysis="詳細分析...",
            # 新規フィールド
            core_question=CoreQuestion(
                primary="派遣社員を定着させる効果的な方法は？",
                time_sensitivity="high",
            ),
            question_hierarchy=QuestionHierarchy(
                level_1_primary=["教育方法は？", "期間は？"],
            ),
            detailed_persona=DetailedPersona(
                name="鈴木太郎",
                age=42,
                job_title="人事課長",
            ),
            behavioral_economics_profile=BehavioralEconomicsProfile(
                loss_aversion=BehavioralEconomicsPrinciple(
                    trigger="採用コスト損失",
                ),
            ),
            three_phase_mapping=ThreePhaseMapping(
                phase1_anxiety=Phase1Anxiety(emotions=["不安"]),
            ),
        )
        assert output.core_question is not None
        assert output.core_question.time_sensitivity == "high"
        assert output.behavioral_economics_profile.loss_aversion.trigger == "採用コスト損失"
        assert output.three_phase_mapping.phase1_anxiety.emotions == ["不安"]

    def test_v2_output_serialization(self):
        """V2出力のシリアライズ."""
        output = Step3aOutputV2(
            keyword="テスト",
            search_intent=SearchIntent(primary="informational"),
            core_question=CoreQuestion(primary="テスト質問"),
        )
        dumped = output.model_dump()

        assert "core_question" in dumped
        assert "behavioral_economics_profile" in dumped
        assert dumped["core_question"]["primary"] == "テスト質問"

    def test_v2_output_partial_new_fields(self):
        """一部の新フィールドのみ設定."""
        output = Step3aOutputV2(
            keyword="テスト",
            search_intent=SearchIntent(primary="informational"),
            core_question=CoreQuestion(primary="質問"),
            # 他の新フィールドは None
        )
        assert output.core_question is not None
        assert output.behavioral_economics_profile is None
        assert output.three_phase_mapping is None
