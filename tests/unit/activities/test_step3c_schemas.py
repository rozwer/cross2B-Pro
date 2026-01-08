"""Step 3C schema tests.

Tests for Step3C schemas including:
- Backward compatibility with existing schemas
- New blog.System Ver8.3 schemas (WordCountAnalysis, RankingFactorAnalysis, etc.)
- FourPillarsDifferentiation and related schemas
"""

import pytest
from pydantic import ValidationError

from apps.worker.activities.schemas.step3c import (
    # 新規スキーマ（blog.System Ver8.3）
    AISuggestion,
    ArticleDetail,
    ArticleImplications,
    BehavioralEconomicsDiff,
    CompetitorCTAAnalysis,
    # 既存スキーマ
    CompetitorProfile,
    CompetitorStatistics,
    CTAAppealDiff,
    CTAPlacementDiff,
    DifferentiationStrategy,
    FiveWhysAnalysis,
    FourPillarsDifferentiation,
    GapOpportunity,
    GoogleEvaluationFactors,
    KGIDiff,
    LLMODiff,
    NeuroscienceDiff,
    PhaseDiff,
    PhaseStrategy,
    PrincipleDiff,
    QuestionHeadingsDiff,
    RankingFactorAnalysis,
    SatisfactionDeepDive,
    SatisfactionPatterns,
    SectionIndependenceDiff,
    Step3cOutput,
    ThreePhaseDifferentiationStrategy,
    TopArticleAnalysis,
    WordCountAnalysis,
    WordCountRange,
)


class TestCompetitorProfileBackwardCompatibility:
    """Test CompetitorProfile backward compatibility."""

    def test_competitor_profile_minimal(self):
        """最小限のプロファイル."""
        profile = CompetitorProfile(url="https://example.com", title="テスト記事")
        assert profile.url == "https://example.com"
        assert profile.title == "テスト記事"
        assert profile.strengths == []
        assert profile.weaknesses == []
        assert profile.threat_level == "medium"

    def test_competitor_profile_full(self):
        """全フィールド付きプロファイル."""
        profile = CompetitorProfile(
            url="https://example.com/article",
            title="競合記事タイトル",
            strengths=["詳細な解説", "豊富な事例"],
            weaknesses=["更新が古い", "CTA弱い"],
            content_focus=["初心者向け", "実践的"],
            unique_value="独自調査データ",
            threat_level="high",
        )
        assert len(profile.strengths) == 2
        assert len(profile.weaknesses) == 2
        assert profile.threat_level == "high"

    def test_competitor_profile_threat_levels(self):
        """threat_level の全レベル."""
        for level in ["high", "medium", "low"]:
            profile = CompetitorProfile(url="https://example.com", title="test", threat_level=level)
            assert profile.threat_level == level


class TestDifferentiationStrategyBackwardCompatibility:
    """Test DifferentiationStrategy backward compatibility."""

    def test_differentiation_strategy_minimal(self):
        """最小限の差別化戦略."""
        strategy = DifferentiationStrategy(category="content", description="独自コンテンツで差別化")
        assert strategy.category == "content"
        assert strategy.priority == "should"

    def test_differentiation_strategy_all_categories(self):
        """全カテゴリのテスト."""
        for cat in ["content", "expertise", "format", "depth", "perspective"]:
            strategy = DifferentiationStrategy(category=cat, description="test")
            assert strategy.category == cat

    def test_differentiation_strategy_priorities(self):
        """全優先度のテスト."""
        for pri in ["must", "should", "nice_to_have"]:
            strategy = DifferentiationStrategy(category="content", description="test", priority=pri)
            assert strategy.priority == pri


class TestGapOpportunityBackwardCompatibility:
    """Test GapOpportunity backward compatibility."""

    def test_gap_opportunity_minimal(self):
        """最小限のギャップ機会."""
        gap = GapOpportunity(gap_type="未カバートピック", description="〇〇について言及なし")
        assert gap.gap_type == "未カバートピック"
        assert gap.value_potential == 0.5

    def test_gap_opportunity_full(self):
        """全フィールド付きギャップ機会."""
        gap = GapOpportunity(
            gap_type="最新データ不足",
            description="2024年以降のデータがない",
            competitors_missing=["https://a.com", "https://b.com"],
            value_potential=0.8,
        )
        assert len(gap.competitors_missing) == 2
        assert gap.value_potential == 0.8

    def test_gap_opportunity_value_bounds(self):
        """value_potential の境界値テスト."""
        GapOpportunity(gap_type="test", description="test", value_potential=0.0)
        GapOpportunity(gap_type="test", description="test", value_potential=1.0)

        with pytest.raises(ValidationError):
            GapOpportunity(gap_type="test", description="test", value_potential=-0.1)
        with pytest.raises(ValidationError):
            GapOpportunity(gap_type="test", description="test", value_potential=1.1)


class TestStep3cOutputBackwardCompatibility:
    """Test Step3cOutput backward compatibility."""

    def test_step3c_output_minimal(self):
        """最小限の出力."""
        output = Step3cOutput(keyword="テストキーワード")
        assert output.keyword == "テストキーワード"
        assert output.competitor_profiles == []
        assert output.raw_analysis == ""
        # 新規フィールドは None
        assert output.word_count_analysis is None
        assert output.target_word_count is None

    def test_step3c_output_with_legacy_fields(self):
        """レガシーフィールド付き出力."""
        output = Step3cOutput(
            keyword="派遣社員 教育方法",
            competitor_profiles=[
                CompetitorProfile(url="https://a.com", title="記事A"),
            ],
            market_overview="市場概要...",
            differentiation_strategies=[
                DifferentiationStrategy(category="content", description="独自コンテンツ"),
            ],
            gap_opportunities=[
                GapOpportunity(gap_type="トピック", description="説明"),
            ],
            content_recommendations=["推奨1", "推奨2"],
            raw_analysis="分析結果...",
        )
        assert len(output.competitor_profiles) == 1
        assert len(output.differentiation_strategies) == 1


# =============================================================================
# 新規スキーマテスト: WordCountAnalysis
# =============================================================================


class TestCompetitorStatistics:
    """Test CompetitorStatistics schema."""

    def test_competitor_statistics(self):
        """競合統計."""
        stats = CompetitorStatistics(
            average_word_count=5000.5,
            median_word_count=4800.0,
            max_word_count=8000,
            min_word_count=3000,
            standard_deviation=1200.5,
            data_points=10,
        )
        assert stats.average_word_count == 5000.5
        assert stats.data_points == 10


class TestArticleDetail:
    """Test ArticleDetail schema."""

    def test_article_detail(self):
        """記事詳細."""
        detail = ArticleDetail(rank=1, title="記事タイトル", url="https://example.com", word_count=5000)
        assert detail.rank == 1
        assert detail.notes == ""

    def test_article_detail_with_notes(self):
        """ノート付き記事詳細."""
        detail = ArticleDetail(
            rank=1,
            title="記事タイトル",
            url="https://example.com",
            word_count=0,
            notes="コンテンツ取得失敗",
        )
        assert detail.notes == "コンテンツ取得失敗"


class TestAISuggestion:
    """Test AISuggestion schema."""

    def test_ai_suggestion(self):
        """AI提案."""
        suggestion = AISuggestion(ai_suggested_word_count=6000, suggestion_logic="平均5000字 × 1.2（SEO最適化）= 6000字")
        assert suggestion.ai_suggested_word_count == 6000


class TestWordCountRange:
    """Test WordCountRange schema."""

    def test_word_count_range(self):
        """文字数レンジ."""
        range_ = WordCountRange(
            min=5700,
            min_relaxed=5500,
            max=6300,
            target=6000,
        )
        assert range_.target == 6000
        assert range_.min == 5700
        assert range_.min_relaxed == 5500
        assert range_.max == 6300


class TestWordCountAnalysis:
    """Test WordCountAnalysis schema."""

    def test_word_count_analysis_skipped(self):
        """スキップ時の文字数分析."""
        analysis = WordCountAnalysis(
            mode="manual",
            analysis_skipped=True,
            skip_reason="manualモードのため算出スキップ",
        )
        assert analysis.analysis_skipped is True

    def test_word_count_analysis_full(self):
        """全フィールド付き文字数分析."""
        analysis = WordCountAnalysis(
            mode="ai_seo_optimized",
            analysis_skipped=False,
            target_keyword="テストキーワード",
            competitor_statistics=CompetitorStatistics(
                average_word_count=5000,
                median_word_count=4800,
                max_word_count=8000,
                min_word_count=3000,
                data_points=10,
            ),
            article_details=[
                ArticleDetail(rank=1, title="記事1", url="https://a.com", word_count=5000),
            ],
            ai_suggestion=AISuggestion(
                ai_suggested_word_count=6000,
                suggestion_logic="平均5000字 × 1.2 = 6000字",
            ),
            ai_suggested_word_count=6000,
            rationale="平均5000字 × 1.2 = 6000字",
            target_word_count_range=WordCountRange(
                min=5700,
                min_relaxed=5500,
                max=6300,
                target=6000,
            ),
            note="この文字数は達成すべき目標値です。",
        )
        assert analysis.ai_suggested_word_count == 6000
        assert analysis.target_word_count_range.target == 6000


# =============================================================================
# 新規スキーマテスト: RankingFactorAnalysis
# =============================================================================


class TestFiveWhysAnalysis:
    """Test FiveWhysAnalysis schema."""

    def test_five_whys_analysis(self):
        """5 Whys分析."""
        analysis = FiveWhysAnalysis(
            article_feature="5ステップで整理された解説",
            level_1="情報が理解しやすい",
            level_2="整理する負担が減る",
            level_3="判断に時間がかかり他の仕事に影響",
            level_4="限られた時間で複数タスクをこなす必要がある",
            level_5_root="認知負荷の軽減",
        )
        assert analysis.level_5_root == "認知負荷の軽減"


class TestSatisfactionDeepDive:
    """Test SatisfactionDeepDive schema."""

    def test_satisfaction_deep_dive(self):
        """満足深掘り分析."""
        deep_dive = SatisfactionDeepDive(
            cognitive_satisfaction=FiveWhysAnalysis(
                article_feature="5ステップ解説",
                level_1="理解しやすい",
                level_2="負担軽減",
                level_3="時間影響",
                level_4="複数タスク",
                level_5_root="認知負荷の軽減",
            ),
            emotional_satisfaction=FiveWhysAnalysis(
                article_feature="成功事例掲載",
                level_1="安心感",
                level_2="失敗恐れ軽減",
                level_3="行動先延ばし",
                level_4="評価心配",
                level_5_root="社会的リスクの回避",
            ),
            actionable_satisfaction=FiveWhysAnalysis(
                article_feature="テンプレートDL可能",
                level_1="すぐ使える",
                level_2="手間省ける",
                level_3="着手遅れ",
                level_4="早く結果",
                level_5_root="自己効力感の向上",
            ),
            root_cause_categories_used=["認知負荷の軽減", "社会的リスクの回避", "自己効力感の向上"],
        )
        assert len(deep_dive.root_cause_categories_used) == 3


class TestGoogleEvaluationFactors:
    """Test GoogleEvaluationFactors schema."""

    def test_google_evaluation_factors(self):
        """Google評価要因."""
        factors = GoogleEvaluationFactors(
            experience="実体験に基づく記述あり",
            expertise="専門的知識の深さ",
            authoritativeness="引用元の信頼性",
            trustworthiness="情報の正確性",
            search_intent_fulfillment="検索意図への対応度が高い",
            user_experience_signals="読みやすく構成が良い",
        )
        assert factors.experience == "実体験に基づく記述あり"


class TestRankingFactorAnalysis:
    """Test RankingFactorAnalysis schema."""

    def test_ranking_factor_analysis_minimal(self):
        """最小限のランキング要因分析."""
        analysis = RankingFactorAnalysis()
        assert analysis.analysis_summary == ""
        assert analysis.top_articles_deep_analysis == []

    def test_ranking_factor_analysis_full(self):
        """全フィールド付きランキング要因分析."""
        analysis = RankingFactorAnalysis(
            analysis_summary="上位記事は詳細な解説と実践的なコンテンツが特徴",
            top_articles_deep_analysis=[
                TopArticleAnalysis(
                    rank=1,
                    title="記事1",
                    url="https://a.com",
                    satisfaction_deep_dive=SatisfactionDeepDive(
                        cognitive_satisfaction=FiveWhysAnalysis(
                            article_feature="test",
                            level_1="1",
                            level_2="2",
                            level_3="3",
                            level_4="4",
                            level_5_root="認知負荷の軽減",
                        ),
                        emotional_satisfaction=FiveWhysAnalysis(
                            article_feature="test",
                            level_1="1",
                            level_2="2",
                            level_3="3",
                            level_4="4",
                            level_5_root="社会的リスクの回避",
                        ),
                        actionable_satisfaction=FiveWhysAnalysis(
                            article_feature="test",
                            level_1="1",
                            level_2="2",
                            level_3="3",
                            level_4="4",
                            level_5_root="自己効力感の向上",
                        ),
                    ),
                    google_evaluation_factors=GoogleEvaluationFactors(),
                ),
            ],
            common_ranking_factors=["詳細な解説", "実践的", "最新データ", "専門性", "読みやすさ"],
            satisfaction_patterns=SatisfactionPatterns(
                informational_satisfaction=["理解しやすい構成"],
                emotional_satisfaction=["安心感を与える事例"],
                actionable_satisfaction=["すぐ実践できる手順"],
            ),
            actionable_insights=["詳細な解説を含める", "事例を3つ以上提示"],
            implications_for_our_article=ArticleImplications(
                must_include=["詳細な解説", "成功事例"],
                differentiation_opportunities=["最新データの提示", "独自調査"],
                user_journey_design="問題認識→解決策理解→行動促進の流れ",
            ),
        )
        assert len(analysis.common_ranking_factors) == 5
        assert len(analysis.actionable_insights) == 2


# =============================================================================
# 新規スキーマテスト: FourPillarsDifferentiation
# =============================================================================


class TestPhaseDiff:
    """Test PhaseDiff schema."""

    def test_phase_diff(self):
        """フェーズ別差別化."""
        diff = PhaseDiff(
            competitor_approach="一般的な課題列挙",
            our_differentiation="具体的損失額の明示",
            expected_effect="扁桃体活性化+30%",
        )
        assert "扁桃体" in diff.expected_effect


class TestNeuroscienceDiff:
    """Test NeuroscienceDiff schema."""

    def test_neuroscience_diff_defaults(self):
        """デフォルト値."""
        diff = NeuroscienceDiff()
        assert diff.phase1_fear_recognition.competitor_approach == ""

    def test_neuroscience_diff_full(self):
        """全フェーズ付き神経科学差別化."""
        diff = NeuroscienceDiff(
            phase1_fear_recognition=PhaseDiff(
                competitor_approach="一般的な課題",
                our_differentiation="具体的損失額",
                expected_effect="扁桃体活性化+30%",
            ),
            phase2_understanding=PhaseDiff(
                competitor_approach="一般的な解決策",
                our_differentiation="予算別プラン+最新データ",
                expected_effect="前頭前野処理満足度+40%",
            ),
            phase3_action=PhaseDiff(
                competitor_approach="単一CTA",
                our_differentiation="3段階CTA",
                expected_effect="CVR+50%",
            ),
        )
        assert diff.phase3_action.expected_effect == "CVR+50%"


class TestBehavioralEconomicsDiff:
    """Test BehavioralEconomicsDiff schema."""

    def test_behavioral_economics_diff_defaults(self):
        """デフォルト値."""
        diff = BehavioralEconomicsDiff()
        assert diff.loss_aversion.competitor_approach == ""
        assert diff.social_proof.competitor_approach == ""

    def test_behavioral_economics_diff_full(self):
        """全6原則付き行動経済学差別化."""
        diff = BehavioralEconomicsDiff(
            loss_aversion=PrincipleDiff(competitor_approach="抽象的な損失", our_differentiation="具体的金額"),
            social_proof=PrincipleDiff(competitor_approach="少数事例", our_differentiation="多数実績+数値"),
            authority=PrincipleDiff(competitor_approach="一般統計", our_differentiation="公的データ+専門家"),
            consistency=PrincipleDiff(competitor_approach="単発CTA", our_differentiation="段階的コミットメント"),
            liking=PrincipleDiff(competitor_approach="フォーマル", our_differentiation="共感的トーン"),
            scarcity=PrincipleDiff(competitor_approach="希少性なし", our_differentiation="適度な緊急性"),
        )
        assert diff.loss_aversion.our_differentiation == "具体的金額"


class TestLLMODiff:
    """Test LLMODiff schema."""

    def test_llmo_diff_defaults(self):
        """デフォルト値."""
        diff = LLMODiff()
        assert diff.question_headings.competitor_count == 0
        assert diff.question_headings.our_target == 5

    def test_llmo_diff_full(self):
        """全フィールド付きLLMO差別化."""
        diff = LLMODiff(
            question_headings=QuestionHeadingsDiff(competitor_count=2, our_target=5),
            section_independence=SectionIndependenceDiff(
                competitor_issue="セクション独立性が低い",
                our_approach="各セクションを独立させRAG検索最適化",
            ),
            expected_effect="AI引用率+35%",
        )
        assert diff.expected_effect == "AI引用率+35%"


class TestKGIDiff:
    """Test KGIDiff schema."""

    def test_kgi_diff_defaults(self):
        """デフォルト値."""
        diff = KGIDiff()
        assert diff.cta_placement.competitor_average == 0.0

    def test_kgi_diff_full(self):
        """全フィールド付きKGI差別化."""
        diff = KGIDiff(
            cta_placement=CTAPlacementDiff(
                competitor_average=1.2,
                our_strategy="3段階CTA（Early/Mid/Final）",
            ),
            cta_appeal=CTAAppealDiff(
                competitor_approach="お問い合わせのみ",
                our_differentiation="具体的ベネフィット+無料性訴求",
            ),
            expected_effect="CVR+50%",
        )
        assert diff.expected_effect == "CVR+50%"


class TestFourPillarsDifferentiation:
    """Test FourPillarsDifferentiation schema."""

    def test_four_pillars_defaults(self):
        """デフォルト値."""
        diff = FourPillarsDifferentiation()
        assert diff.neuroscience.phase1_fear_recognition.competitor_approach == ""
        assert diff.behavioral_economics.loss_aversion.competitor_approach == ""
        assert diff.llmo.question_headings.our_target == 5
        assert diff.kgi.cta_placement.competitor_average == 0.0

    def test_four_pillars_full(self):
        """全4本柱付き差別化."""
        diff = FourPillarsDifferentiation(
            neuroscience=NeuroscienceDiff(
                phase1_fear_recognition=PhaseDiff(expected_effect="扁桃体+30%"),
            ),
            behavioral_economics=BehavioralEconomicsDiff(
                loss_aversion=PrincipleDiff(our_differentiation="具体的金額"),
            ),
            llmo=LLMODiff(expected_effect="AI引用率+35%"),
            kgi=KGIDiff(expected_effect="CVR+50%"),
        )
        assert diff.kgi.expected_effect == "CVR+50%"


# =============================================================================
# 新規スキーマテスト: ThreePhaseDifferentiationStrategy
# =============================================================================


class TestPhaseStrategy:
    """Test PhaseStrategy schema."""

    def test_phase_strategy(self):
        """フェーズ戦略."""
        strategy = PhaseStrategy(
            phase_name="不安・課題認識",
            user_state="問題の深刻さに気づき始めた状態",
            competitor_weakness="課題提示が弱い",
            our_differentiation=["具体的損失額の明示", "共感的なトーン"],
            expected_metrics="離脱率-13pt",
        )
        assert strategy.phase_name == "不安・課題認識"
        assert len(strategy.our_differentiation) == 2


class TestThreePhaseDifferentiationStrategy:
    """Test ThreePhaseDifferentiationStrategy schema."""

    def test_three_phase_defaults(self):
        """デフォルト値."""
        strategy = ThreePhaseDifferentiationStrategy()
        assert strategy.phase1.phase_name == "不安・課題認識"
        assert strategy.phase2.phase_name == "理解・納得"
        assert strategy.phase3.phase_name == "行動決定"

    def test_three_phase_full(self):
        """全フェーズ付き3フェーズ戦略."""
        strategy = ThreePhaseDifferentiationStrategy(
            phase1=PhaseStrategy(
                phase_name="不安・課題認識",
                expected_metrics="離脱率-13pt",
            ),
            phase2=PhaseStrategy(
                phase_name="理解・納得",
                expected_metrics="滞在時間+40%",
            ),
            phase3=PhaseStrategy(
                phase_name="行動決定",
                expected_metrics="CVR+50%",
            ),
        )
        assert strategy.phase3.expected_metrics == "CVR+50%"


# =============================================================================
# 新規スキーマテスト: CompetitorCTAAnalysis
# =============================================================================


class TestCompetitorCTAAnalysis:
    """Test CompetitorCTAAnalysis schema."""

    def test_competitor_cta_analysis_defaults(self):
        """デフォルト値."""
        analysis = CompetitorCTAAnalysis()
        assert analysis.cta_deployment_rate == 0.0
        assert analysis.average_cta_count == 0.0

    def test_competitor_cta_analysis_full(self):
        """全フィールド付きCTA分析."""
        analysis = CompetitorCTAAnalysis(
            cta_deployment_rate=0.8,
            average_cta_count=1.2,
            main_cta_positions=["記事末尾", "サイドバー"],
            our_differentiation_strategy="3段階CTA（Early/Mid/Final）で競合の3倍のCTA機会を設置",
        )
        assert analysis.cta_deployment_rate == 0.8
        assert len(analysis.main_cta_positions) == 2


# =============================================================================
# Step3cOutput with new fields
# =============================================================================


class TestStep3cOutputWithNewFields:
    """Test Step3cOutput with blog.System integration fields."""

    def test_step3c_output_with_word_count_analysis(self):
        """word_count_analysis付き出力."""
        output = Step3cOutput(
            keyword="テストキーワード",
            word_count_analysis=WordCountAnalysis(
                mode="ai_seo_optimized",
                analysis_skipped=False,
            ),
            target_word_count=6000,
        )
        assert output.target_word_count == 6000
        assert output.word_count_analysis.mode == "ai_seo_optimized"

    def test_step3c_output_with_ranking_factor_analysis(self):
        """ranking_factor_analysis付き出力."""
        output = Step3cOutput(
            keyword="テストキーワード",
            ranking_factor_analysis=RankingFactorAnalysis(
                analysis_summary="上位記事の特徴分析",
                common_ranking_factors=["詳細解説", "実践的"],
            ),
        )
        assert len(output.ranking_factor_analysis.common_ranking_factors) == 2

    def test_step3c_output_with_four_pillars(self):
        """four_pillars_differentiation付き出力."""
        output = Step3cOutput(
            keyword="テストキーワード",
            four_pillars_differentiation=FourPillarsDifferentiation(
                kgi=KGIDiff(expected_effect="CVR+50%"),
            ),
        )
        assert output.four_pillars_differentiation.kgi.expected_effect == "CVR+50%"

    def test_step3c_output_with_three_phase_strategy(self):
        """three_phase_differentiation_strategy付き出力."""
        output = Step3cOutput(
            keyword="テストキーワード",
            three_phase_differentiation_strategy=ThreePhaseDifferentiationStrategy(),
        )
        assert output.three_phase_differentiation_strategy.phase1.phase_name == "不安・課題認識"

    def test_step3c_output_with_cta_analysis(self):
        """competitor_cta_analysis付き出力."""
        output = Step3cOutput(
            keyword="テストキーワード",
            competitor_cta_analysis=CompetitorCTAAnalysis(
                cta_deployment_rate=0.8,
                average_cta_count=1.2,
            ),
        )
        assert output.competitor_cta_analysis.cta_deployment_rate == 0.8

    def test_step3c_output_full_integration(self):
        """全新規フィールド付きの完全な出力."""
        output = Step3cOutput(
            keyword="派遣社員 教育方法",
            competitor_profiles=[
                CompetitorProfile(url="https://a.com", title="記事A"),
            ],
            market_overview="市場概要",
            differentiation_strategies=[
                DifferentiationStrategy(category="content", description="独自コンテンツ"),
            ],
            raw_analysis="分析結果",
            # 新規フィールド
            word_count_analysis=WordCountAnalysis(
                mode="ai_seo_optimized",
                target_keyword="派遣社員 教育方法",
                ai_suggested_word_count=6000,
            ),
            target_word_count=6000,
            ranking_factor_analysis=RankingFactorAnalysis(
                analysis_summary="上位記事の特徴",
            ),
            four_pillars_differentiation=FourPillarsDifferentiation(),
            three_phase_differentiation_strategy=ThreePhaseDifferentiationStrategy(),
            competitor_cta_analysis=CompetitorCTAAnalysis(),
        )
        assert output.target_word_count == 6000
        assert output.word_count_analysis.ai_suggested_word_count == 6000
        assert output.four_pillars_differentiation is not None
        assert output.three_phase_differentiation_strategy is not None

    def test_step3c_output_serialization(self):
        """出力のシリアライズ."""
        output = Step3cOutput(
            keyword="テスト",
            target_word_count=6000,
            word_count_analysis=WordCountAnalysis(mode="ai_balanced"),
        )
        dumped = output.model_dump()

        assert "word_count_analysis" in dumped
        assert "target_word_count" in dumped
        assert dumped["target_word_count"] == 6000
