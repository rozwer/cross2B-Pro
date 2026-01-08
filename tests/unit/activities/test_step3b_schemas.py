"""Step 3B schema tests.

Tests for Step3B schemas including:
- KeywordItem with blog.System Ver8.3 extensions (phase, behavioral_trigger)
- KeywordCluster with density_score
- ThreePhaseDistribution (3-phase neuroscience-based mapping)
- LLMOOptimizedKeywords (voice search, question format)
- BehavioralEconomicsTriggers (6 principles)
- CTAKeywords (conversion optimization)
- KeywordCategorization (Essential/Standard/Unique)
- Step3bOutput with all extensions
"""

import pytest
from pydantic import ValidationError

from apps.worker.activities.schemas.step3b import (
    BehavioralEconomicsTriggers,
    CompetitorKeywordGap,
    CTAKeywords,
    KeywordCategorization,
    KeywordCluster,
    KeywordDensityAnalysis,
    KeywordItem,
    LLMOOptimizedKeywords,
    Step3bOutput,
    ThreePhaseDistribution,
)


class TestKeywordItemBackwardCompatibility:
    """Test KeywordItem backward compatibility."""

    def test_keyword_item_minimal(self):
        """最小限のキーワードアイテム."""
        item = KeywordItem(keyword="派遣社員")
        assert item.keyword == "派遣社員"
        assert item.category == "cooccurrence"
        assert item.importance == 0.5
        assert item.frequency == 0
        assert item.context == ""
        # blog.System extensions default to None/0
        assert item.phase is None
        assert item.behavioral_trigger is None
        assert item.article_coverage == 0

    def test_keyword_item_all_categories(self):
        """全カテゴリのキーワード."""
        categories = ["cooccurrence", "lsi", "related", "synonym", "long_tail"]
        for cat in categories:
            item = KeywordItem(keyword="test", category=cat)
            assert item.category == cat

    def test_keyword_item_importance_bounds(self):
        """importance の境界値テスト."""
        KeywordItem(keyword="test", importance=0.0)
        KeywordItem(keyword="test", importance=1.0)

        with pytest.raises(ValidationError):
            KeywordItem(keyword="test", importance=-0.1)
        with pytest.raises(ValidationError):
            KeywordItem(keyword="test", importance=1.1)


class TestKeywordItemBlogSystemExtensions:
    """Test KeywordItem blog.System Ver8.3 extensions."""

    def test_keyword_item_with_phase(self):
        """フェーズ付きキーワード."""
        for phase in [1, 2, 3]:
            item = KeywordItem(keyword="test", phase=phase)
            assert item.phase == phase

    def test_keyword_item_invalid_phase(self):
        """無効なフェーズ."""
        with pytest.raises(ValidationError):
            KeywordItem(keyword="test", phase=0)
        with pytest.raises(ValidationError):
            KeywordItem(keyword="test", phase=4)

    def test_keyword_item_with_behavioral_trigger(self):
        """行動経済学トリガー付きキーワード."""
        triggers = [
            "loss_aversion",
            "social_proof",
            "authority",
            "consistency",
            "liking",
            "scarcity",
        ]
        for trigger in triggers:
            item = KeywordItem(keyword="test", behavioral_trigger=trigger)
            assert item.behavioral_trigger == trigger

    def test_keyword_item_invalid_behavioral_trigger(self):
        """無効な行動経済学トリガー."""
        with pytest.raises(ValidationError):
            KeywordItem(keyword="test", behavioral_trigger="unknown")

    def test_keyword_item_full_blog_system(self):
        """全blog.Systemフィールド付きキーワード."""
        item = KeywordItem(
            keyword="派遣社員 教育方法",
            category="cooccurrence",
            importance=0.9,
            frequency=15,
            context="人材教育の文脈で頻出",
            phase=2,
            behavioral_trigger="authority",
            article_coverage=7,
        )
        assert item.phase == 2
        assert item.behavioral_trigger == "authority"
        assert item.article_coverage == 7


class TestKeywordCluster:
    """Test KeywordCluster schema."""

    def test_cluster_minimal(self):
        """最小限のクラスタ."""
        cluster = KeywordCluster(theme="教育方法")
        assert cluster.theme == "教育方法"
        assert cluster.keywords == []
        assert cluster.relevance_to_main == 0.5
        assert cluster.density_score == 0.0

    def test_cluster_with_keywords(self):
        """キーワード付きクラスタ."""
        cluster = KeywordCluster(
            theme="コスト関連",
            keywords=[
                KeywordItem(keyword="採用コスト", importance=0.8),
                KeywordItem(keyword="教育費用", importance=0.7),
            ],
            relevance_to_main=0.85,
            density_score=0.6,
        )
        assert len(cluster.keywords) == 2
        assert cluster.density_score == 0.6

    def test_cluster_density_bounds(self):
        """density_score の境界値テスト."""
        KeywordCluster(theme="test", density_score=0.0)
        KeywordCluster(theme="test", density_score=1.0)

        with pytest.raises(ValidationError):
            KeywordCluster(theme="test", density_score=-0.1)
        with pytest.raises(ValidationError):
            KeywordCluster(theme="test", density_score=1.1)


class TestThreePhaseDistribution:
    """Test ThreePhaseDistribution schema."""

    def test_three_phase_defaults(self):
        """デフォルト値の確認."""
        dist = ThreePhaseDistribution()
        assert dist.phase1_keywords == []
        assert dist.phase2_keywords == []
        assert dist.phase3_keywords == []

    def test_three_phase_full(self):
        """全フェーズ付き分布."""
        dist = ThreePhaseDistribution(
            phase1_keywords=[
                KeywordItem(keyword="不安", phase=1),
                KeywordItem(keyword="課題", phase=1),
            ],
            phase2_keywords=[
                KeywordItem(keyword="比較", phase=2),
                KeywordItem(keyword="方法", phase=2),
                KeywordItem(keyword="メリット", phase=2),
            ],
            phase3_keywords=[
                KeywordItem(keyword="今すぐ", phase=3),
                KeywordItem(keyword="申し込み", phase=3),
            ],
        )
        assert len(dist.phase1_keywords) == 2
        assert len(dist.phase2_keywords) == 3
        assert len(dist.phase3_keywords) == 2


class TestLLMOOptimizedKeywords:
    """Test LLMOOptimizedKeywords schema."""

    def test_llmo_defaults(self):
        """デフォルト値の確認."""
        llmo = LLMOOptimizedKeywords()
        assert llmo.question_format == []
        assert llmo.voice_search == []

    def test_llmo_full(self):
        """全フィールド付きLLMOキーワード."""
        llmo = LLMOOptimizedKeywords(
            question_format=[
                "派遣社員 教育方法 とは",
                "派遣社員 定着 方法",
                "派遣社員 研修 やり方",
            ],
            voice_search=[
                "派遣社員を教育するにはどうすればいいですか",
                "なぜ派遣社員は辞めてしまうのか",
                "いつ派遣社員の研修をすべきか",
            ],
        )
        assert len(llmo.question_format) == 3
        assert len(llmo.voice_search) == 3
        assert "とは" in llmo.question_format[0]


class TestBehavioralEconomicsTriggers:
    """Test BehavioralEconomicsTriggers schema."""

    def test_triggers_defaults(self):
        """デフォルト値の確認."""
        triggers = BehavioralEconomicsTriggers()
        assert triggers.loss_aversion == []
        assert triggers.social_proof == []
        assert triggers.authority == []
        assert triggers.consistency == []
        assert triggers.liking == []
        assert triggers.scarcity == []

    def test_triggers_full(self):
        """全6原則付きトリガー."""
        triggers = BehavioralEconomicsTriggers(
            loss_aversion=["年間320万円の損失", "採用コストの無駄"],
            social_proof=["500社導入", "満足度95%"],
            authority=["厚生労働省推奨", "専門家監修"],
            consistency=["まずは資料請求", "次に無料相談"],
            liking=["お困りですよね", "よく分かります"],
            scarcity=["先着30社限定", "期間限定特典"],
        )
        assert len(triggers.loss_aversion) == 2
        assert "500社" in triggers.social_proof[0]
        assert "厚生労働省" in triggers.authority[0]


class TestCTAKeywords:
    """Test CTAKeywords schema."""

    def test_cta_defaults(self):
        """デフォルト値の確認."""
        cta = CTAKeywords()
        assert cta.urgency == []
        assert cta.ease == []
        assert cta.free == []
        assert cta.expertise == []

    def test_cta_full(self):
        """全フィールド付きCTAキーワード."""
        cta = CTAKeywords(
            urgency=["今すぐ", "即日対応", "すぐに"],
            ease=["簡単3ステップ", "手軽に", "たった5分"],
            free=["無料診断", "0円", "費用なし"],
            expertise=["専門家が対応", "プロ監修", "実績10年"],
        )
        assert "今すぐ" in cta.urgency
        assert "無料" in cta.free[0]


class TestKeywordDensityAnalysis:
    """Test KeywordDensityAnalysis schema."""

    def test_density_defaults(self):
        """デフォルト値の確認."""
        density = KeywordDensityAnalysis()
        assert density.main_keyword_density == 0.0
        assert density.cooccurrence_densities == {}

    def test_density_full(self):
        """全フィールド付き密度分析."""
        density = KeywordDensityAnalysis(
            main_keyword_density=1.8,
            cooccurrence_densities={
                "教育方法": 0.7,
                "研修": 0.5,
                "定着率": 0.4,
            },
        )
        assert density.main_keyword_density == 1.8
        assert density.cooccurrence_densities["教育方法"] == 0.7


class TestCompetitorKeywordGap:
    """Test CompetitorKeywordGap schema."""

    def test_gap_minimal(self):
        """最小限のギャップ分析."""
        gap = CompetitorKeywordGap(keyword="差別化キーワード")
        assert gap.keyword == "差別化キーワード"
        assert gap.coverage_rate == 0.0
        assert gap.differentiation_score == 0.0

    def test_gap_full(self):
        """全フィールド付きギャップ分析."""
        gap = CompetitorKeywordGap(
            keyword="AI教育プログラム",
            coverage_rate=0.2,
            differentiation_score=0.8,
        )
        assert gap.coverage_rate == 0.2
        assert gap.differentiation_score == 0.8

    def test_gap_bounds(self):
        """境界値テスト."""
        CompetitorKeywordGap(keyword="test", coverage_rate=0.0, differentiation_score=0.0)
        CompetitorKeywordGap(keyword="test", coverage_rate=1.0, differentiation_score=1.0)

        with pytest.raises(ValidationError):
            CompetitorKeywordGap(keyword="test", coverage_rate=-0.1)
        with pytest.raises(ValidationError):
            CompetitorKeywordGap(keyword="test", differentiation_score=1.1)


class TestKeywordCategorization:
    """Test KeywordCategorization schema."""

    def test_categorization_defaults(self):
        """デフォルト値の確認."""
        cat = KeywordCategorization()
        assert cat.essential == []
        assert cat.standard == []
        assert cat.unique == []

    def test_categorization_full(self):
        """全カテゴリ付き分類."""
        cat = KeywordCategorization(
            essential=[
                KeywordItem(keyword="派遣社員", article_coverage=9),
                KeywordItem(keyword="教育", article_coverage=8),
            ],
            standard=[
                KeywordItem(keyword="研修", article_coverage=5),
                KeywordItem(keyword="OJT", article_coverage=4),
            ],
            unique=[
                KeywordItem(keyword="AI活用", article_coverage=2),
                KeywordItem(keyword="リモート研修", article_coverage=1),
            ],
        )
        assert len(cat.essential) == 2
        assert len(cat.standard) == 2
        assert len(cat.unique) == 2
        assert cat.essential[0].article_coverage >= 7  # Essential: 70%+


class TestStep3bOutputBackwardCompatibility:
    """Test Step3bOutput backward compatibility."""

    def test_output_minimal(self):
        """最小限の出力（後方互換性）."""
        output = Step3bOutput(
            primary_keyword="派遣社員 教育方法",
            cooccurrence_keywords=[
                KeywordItem(keyword="研修"),
                KeywordItem(keyword="教育"),
                KeywordItem(keyword="スキル"),
                KeywordItem(keyword="定着"),
                KeywordItem(keyword="育成"),
            ],
        )
        assert output.primary_keyword == "派遣社員 教育方法"
        assert len(output.cooccurrence_keywords) == 5
        # blog.System extensions default to None
        assert output.keyword_categorization is None
        assert output.three_phase_distribution is None
        assert output.llmo_optimized_keywords is None
        assert output.behavioral_economics_triggers is None
        assert output.cta_keywords is None

    def test_output_cooccurrence_min_length(self):
        """共起語の最小数テスト."""
        # 5個以上必要
        with pytest.raises(ValidationError):
            Step3bOutput(
                primary_keyword="test",
                cooccurrence_keywords=[
                    KeywordItem(keyword="a"),
                    KeywordItem(keyword="b"),
                    KeywordItem(keyword="c"),
                    KeywordItem(keyword="d"),
                ],  # 4個しかない
            )


class TestStep3bOutputBlogSystemExtensions:
    """Test Step3bOutput blog.System Ver8.3 extensions."""

    def test_output_with_keyword_categorization(self):
        """カテゴリ分類付き出力."""
        output = Step3bOutput(
            primary_keyword="派遣社員 教育方法",
            cooccurrence_keywords=[KeywordItem(keyword=f"kw{i}") for i in range(5)],
            keyword_categorization=KeywordCategorization(
                essential=[KeywordItem(keyword="必須KW", article_coverage=8)],
                standard=[KeywordItem(keyword="標準KW", article_coverage=5)],
                unique=[KeywordItem(keyword="独自KW", article_coverage=2)],
            ),
        )
        assert output.keyword_categorization is not None
        assert len(output.keyword_categorization.essential) == 1

    def test_output_with_three_phase(self):
        """3フェーズ分布付き出力."""
        output = Step3bOutput(
            primary_keyword="派遣社員 教育方法",
            cooccurrence_keywords=[KeywordItem(keyword=f"kw{i}") for i in range(5)],
            three_phase_distribution=ThreePhaseDistribution(
                phase1_keywords=[KeywordItem(keyword="不安", phase=1)],
                phase2_keywords=[KeywordItem(keyword="比較", phase=2)],
                phase3_keywords=[KeywordItem(keyword="今すぐ", phase=3)],
            ),
        )
        assert output.three_phase_distribution is not None
        assert len(output.three_phase_distribution.phase1_keywords) == 1

    def test_output_with_llmo(self):
        """LLMOキーワード付き出力."""
        output = Step3bOutput(
            primary_keyword="派遣社員 教育方法",
            cooccurrence_keywords=[KeywordItem(keyword=f"kw{i}") for i in range(5)],
            llmo_optimized_keywords=LLMOOptimizedKeywords(
                question_format=["派遣社員 教育 とは"],
                voice_search=["派遣社員の教育方法は"],
            ),
        )
        assert output.llmo_optimized_keywords is not None
        assert len(output.llmo_optimized_keywords.question_format) == 1

    def test_output_with_behavioral_triggers(self):
        """行動経済学トリガー付き出力."""
        output = Step3bOutput(
            primary_keyword="派遣社員 教育方法",
            cooccurrence_keywords=[KeywordItem(keyword=f"kw{i}") for i in range(5)],
            behavioral_economics_triggers=BehavioralEconomicsTriggers(
                loss_aversion=["損失回避"],
                social_proof=["社会的証明"],
            ),
        )
        assert output.behavioral_economics_triggers is not None
        assert len(output.behavioral_economics_triggers.loss_aversion) == 1

    def test_output_with_cta_keywords(self):
        """CTAキーワード付き出力."""
        output = Step3bOutput(
            primary_keyword="派遣社員 教育方法",
            cooccurrence_keywords=[KeywordItem(keyword=f"kw{i}") for i in range(5)],
            cta_keywords=CTAKeywords(
                urgency=["今すぐ"],
                ease=["簡単"],
                free=["無料"],
            ),
        )
        assert output.cta_keywords is not None
        assert "今すぐ" in output.cta_keywords.urgency

    def test_output_with_density_analysis(self):
        """密度分析付き出力."""
        output = Step3bOutput(
            primary_keyword="派遣社員 教育方法",
            cooccurrence_keywords=[KeywordItem(keyword=f"kw{i}") for i in range(5)],
            keyword_density_analysis=KeywordDensityAnalysis(
                main_keyword_density=1.8,
                cooccurrence_densities={"教育": 0.6},
            ),
        )
        assert output.keyword_density_analysis is not None
        assert output.keyword_density_analysis.main_keyword_density == 1.8

    def test_output_with_competitor_gaps(self):
        """競合ギャップ分析付き出力."""
        output = Step3bOutput(
            primary_keyword="派遣社員 教育方法",
            cooccurrence_keywords=[KeywordItem(keyword=f"kw{i}") for i in range(5)],
            competitor_keyword_gaps=[
                CompetitorKeywordGap(
                    keyword="AI教育",
                    coverage_rate=0.1,
                    differentiation_score=0.9,
                ),
            ],
        )
        assert len(output.competitor_keyword_gaps) == 1
        assert output.competitor_keyword_gaps[0].differentiation_score == 0.9

    def test_output_with_extraction_summary(self):
        """抽出サマリー付き出力."""
        output = Step3bOutput(
            primary_keyword="派遣社員 教育方法",
            cooccurrence_keywords=[KeywordItem(keyword=f"kw{i}") for i in range(100)],
            related_keywords=[KeywordItem(keyword=f"rel{i}") for i in range(30)],
            extraction_summary={
                "cooccurrence": 100,
                "related": 30,
                "phase1": 15,
                "phase2": 45,
                "phase3": 10,
                "llmo_question": 20,
                "llmo_voice": 15,
            },
        )
        assert output.extraction_summary["cooccurrence"] == 100
        assert output.extraction_summary["phase1"] == 15

    def test_output_full_blog_system(self):
        """全blog.Systemフィールド付き出力."""
        output = Step3bOutput(
            primary_keyword="派遣社員 教育方法",
            total_articles_analyzed=10,
            cooccurrence_keywords=[KeywordItem(keyword=f"kw{i}") for i in range(100)],
            lsi_keywords=[KeywordItem(keyword=f"lsi{i}") for i in range(30)],
            related_keywords=[KeywordItem(keyword=f"rel{i}") for i in range(40)],
            long_tail_variations=[
                "派遣社員 教育方法 効果的",
                "派遣社員 研修 やり方",
            ],
            keyword_categorization=KeywordCategorization(
                essential=[KeywordItem(keyword="必須")],
                standard=[KeywordItem(keyword="標準")],
                unique=[KeywordItem(keyword="独自")],
            ),
            three_phase_distribution=ThreePhaseDistribution(
                phase1_keywords=[KeywordItem(keyword="不安")],
                phase2_keywords=[KeywordItem(keyword="比較")],
                phase3_keywords=[KeywordItem(keyword="行動")],
            ),
            llmo_optimized_keywords=LLMOOptimizedKeywords(
                question_format=["とは", "方法"],
                voice_search=["どうすれば"],
            ),
            behavioral_economics_triggers=BehavioralEconomicsTriggers(
                loss_aversion=["損失"],
                social_proof=["導入実績"],
            ),
            cta_keywords=CTAKeywords(urgency=["今すぐ"]),
            keyword_density_analysis=KeywordDensityAnalysis(main_keyword_density=1.5),
            competitor_keyword_gaps=[CompetitorKeywordGap(keyword="差別化", differentiation_score=0.8)],
            keyword_clusters=[KeywordCluster(theme="コスト", density_score=0.5)],
            recommendations=["共起語を150個に増やす", "フェーズ3のキーワードを強化"],
            raw_analysis="詳細な分析結果...",
            extraction_summary={
                "cooccurrence": 100,
                "lsi": 30,
                "related": 40,
            },
        )
        # 全フィールドが設定されていることを確認
        assert output.keyword_categorization is not None
        assert output.three_phase_distribution is not None
        assert output.llmo_optimized_keywords is not None
        assert output.behavioral_economics_triggers is not None
        assert output.cta_keywords is not None
        assert output.keyword_density_analysis is not None
        assert len(output.competitor_keyword_gaps) == 1
        assert len(output.keyword_clusters) == 1
        assert len(output.recommendations) == 2

    def test_output_serialization(self):
        """出力のシリアライズ."""
        output = Step3bOutput(
            primary_keyword="テスト",
            cooccurrence_keywords=[KeywordItem(keyword=f"kw{i}") for i in range(5)],
            three_phase_distribution=ThreePhaseDistribution(
                phase1_keywords=[KeywordItem(keyword="p1", phase=1)],
            ),
        )
        dumped = output.model_dump()

        assert "three_phase_distribution" in dumped
        assert "keyword_categorization" in dumped
        assert dumped["three_phase_distribution"]["phase1_keywords"][0]["keyword"] == "p1"
