"""Step 3C: Competitor Analysis output schemas."""

from typing import Literal

from pydantic import BaseModel, Field

# =============================================================================
# 既存スキーマ（後方互換性維持）
# =============================================================================


class CompetitorProfile(BaseModel):
    """Competitor profile analysis."""

    url: str
    title: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    content_focus: list[str] = Field(default_factory=list)
    unique_value: str = ""
    threat_level: Literal["high", "medium", "low"] = "medium"


class DifferentiationStrategy(BaseModel):
    """Differentiation strategy recommendation."""

    category: Literal["content", "expertise", "format", "depth", "perspective"]
    description: str
    priority: Literal["must", "should", "nice_to_have"] = "should"
    implementation_hint: str = ""


class GapOpportunity(BaseModel):
    """Market gap opportunity."""

    gap_type: str
    description: str
    competitors_missing: list[str] = Field(default_factory=list)
    value_potential: float = Field(default=0.5, ge=0.0, le=1.0)


# =============================================================================
# 新規スキーマ: WordCountAnalysis（文字数分析）
# =============================================================================


class CompetitorStatistics(BaseModel):
    """競合記事の文字数統計."""

    average_word_count: float = Field(..., description="平均文字数")
    median_word_count: float = Field(..., description="中央値文字数")
    max_word_count: int = Field(..., description="最大文字数")
    min_word_count: int = Field(..., description="最小文字数")
    standard_deviation: float = Field(default=0.0, description="標準偏差")
    data_points: int = Field(..., description="有効データ数")


class ArticleDetail(BaseModel):
    """個別記事の文字数詳細."""

    rank: int
    title: str
    url: str
    word_count: int
    notes: str = ""  # 0文字の場合の理由等


class AISuggestion(BaseModel):
    """AI提案の文字数."""

    ai_suggested_word_count: int = Field(..., description="AI提案文字数")
    suggestion_logic: str = Field(..., description="算出ロジックの説明")
    note: str = ""


class WordCountRange(BaseModel):
    """目標文字数レンジ."""

    min: int = Field(..., description="最小目標（ai_suggested - 300）")
    min_relaxed: int = Field(..., description="緩和下限（ai_suggested - 500）")
    max: int = Field(..., description="最大目標（ai_suggested + 300、厳格）")
    target: int = Field(..., description="目標値そのまま")


class WordCountAnalysis(BaseModel):
    """競合記事の文字数分析."""

    mode: str = Field(..., description="word_count_mode をそのまま転記")
    analysis_skipped: bool = Field(default=False, description="manual時はtrue")
    skip_reason: str = ""
    target_keyword: str = ""

    competitor_statistics: CompetitorStatistics | None = None
    article_details: list[ArticleDetail] = Field(default_factory=list)

    ai_suggestion: AISuggestion | None = None
    ai_suggested_word_count: int | None = None  # 後方互換用
    rationale: str = ""  # 後方互換用

    target_word_count_range: WordCountRange | None = None
    note: str = ""  # 後工程への注意事項


# =============================================================================
# 新規スキーマ: RankingFactorAnalysis（5 Whys深層分析）
# =============================================================================


class FiveWhysAnalysis(BaseModel):
    """5 Whys手法による深掘り分析."""

    article_feature: str = Field(..., description="分析対象の記事特徴")
    level_1: str = Field(..., description="この特徴でユーザーが得られるもの")
    level_2: str = Field(..., description="なぜそれが価値か")
    level_3: str = Field(..., description="その価値がないとどんな問題か")
    level_4: str = Field(..., description="問題の背景にある課題")
    level_5_root: str = Field(..., description="根本ニーズ（カテゴリから選択）")


class SatisfactionDeepDive(BaseModel):
    """3軸×5 Whys手法による満足要因の深掘り."""

    cognitive_satisfaction: FiveWhysAnalysis = Field(..., description="認知的満足（頭で理解）")
    emotional_satisfaction: FiveWhysAnalysis = Field(..., description="感情的満足（心で安心）")
    actionable_satisfaction: FiveWhysAnalysis = Field(..., description="行動的満足（体で動ける）")
    root_cause_categories_used: list[str] = Field(default_factory=list)


class GoogleEvaluationFactors(BaseModel):
    """Google評価要因（E-E-A-T）."""

    experience: str = Field(default="", description="E-E-A-Tの体験")
    expertise: str = Field(default="", description="専門性")
    authoritativeness: str = Field(default="", description="権威性")
    trustworthiness: str = Field(default="", description="信頼性")
    search_intent_fulfillment: str = Field(default="", description="検索意図充足度")
    user_experience_signals: str = Field(default="", description="UXシグナル")


class TopArticleAnalysis(BaseModel):
    """上位記事の詳細分析."""

    rank: int
    title: str
    url: str
    satisfaction_deep_dive: SatisfactionDeepDive
    google_evaluation_factors: GoogleEvaluationFactors
    user_journey_fulfillment: str = ""


class SatisfactionPatterns(BaseModel):
    """ユーザー満足のパターン分類."""

    informational_satisfaction: list[str] = Field(default_factory=list)
    emotional_satisfaction: list[str] = Field(default_factory=list)
    actionable_satisfaction: list[str] = Field(default_factory=list)


class ArticleImplications(BaseModel):
    """自社記事への示唆."""

    must_include: list[str] = Field(default_factory=list, description="必ず含めるべき要素")
    differentiation_opportunities: list[str] = Field(default_factory=list)
    user_journey_design: str = ""


class RankingFactorAnalysis(BaseModel):
    """上位表示要因・ユーザー満足深層分析."""

    analysis_summary: str = Field(default="", description="全体サマリー（200字程度）")

    top_articles_deep_analysis: list[TopArticleAnalysis] = Field(default_factory=list, description="上位3記事の詳細分析")

    common_ranking_factors: list[str] = Field(default_factory=list, description="共通要因（5-7個）")
    satisfaction_patterns: SatisfactionPatterns | None = None
    actionable_insights: list[str] = Field(default_factory=list, description="後工程活用知見（5-10個）")
    implications_for_our_article: ArticleImplications | None = None


# =============================================================================
# 新規スキーマ: FourPillarsDifferentiation（4本柱差別化）
# =============================================================================


class PhaseDiff(BaseModel):
    """フェーズ別差別化."""

    competitor_approach: str = Field(default="", description="競合のアプローチ")
    our_differentiation: str = Field(default="", description="自社の差別化")
    expected_effect: str = Field(default="", description="期待効果")


class NeuroscienceDiff(BaseModel):
    """神経科学での差別化（3フェーズ）."""

    phase1_fear_recognition: PhaseDiff = Field(default_factory=PhaseDiff, description="不安・課題認識")
    phase2_understanding: PhaseDiff = Field(default_factory=PhaseDiff, description="理解・納得")
    phase3_action: PhaseDiff = Field(default_factory=PhaseDiff, description="行動決定")


class PrincipleDiff(BaseModel):
    """原則別差別化."""

    competitor_approach: str = Field(default="", description="競合のアプローチ")
    our_differentiation: str = Field(default="", description="自社の差別化")


class BehavioralEconomicsDiff(BaseModel):
    """行動経済学6原則での差別化."""

    loss_aversion: PrincipleDiff = Field(default_factory=PrincipleDiff, description="損失回避")
    social_proof: PrincipleDiff = Field(default_factory=PrincipleDiff, description="社会的証明")
    authority: PrincipleDiff = Field(default_factory=PrincipleDiff, description="権威性")
    consistency: PrincipleDiff = Field(default_factory=PrincipleDiff, description="一貫性")
    liking: PrincipleDiff = Field(default_factory=PrincipleDiff, description="好意")
    scarcity: PrincipleDiff = Field(default_factory=PrincipleDiff, description="希少性")


class QuestionHeadingsDiff(BaseModel):
    """質問形式見出しの差別化."""

    competitor_count: int = Field(default=0, description="競合平均")
    our_target: int = Field(default=5, description="自社目標")


class SectionIndependenceDiff(BaseModel):
    """セクション独立性の差別化."""

    competitor_issue: str = Field(default="", description="競合の問題点")
    our_approach: str = Field(default="", description="自社のアプローチ")


class LLMODiff(BaseModel):
    """LLMO（AI検索最適化）での差別化."""

    question_headings: QuestionHeadingsDiff = Field(default_factory=QuestionHeadingsDiff)
    section_independence: SectionIndependenceDiff = Field(default_factory=SectionIndependenceDiff)
    expected_effect: str = Field(default="", description="期待効果")


class CTAPlacementDiff(BaseModel):
    """CTA配置の差別化."""

    competitor_average: float = Field(default=0.0, description="競合平均CTA数")
    our_strategy: str = Field(default="", description="自社戦略")


class CTAAppealDiff(BaseModel):
    """CTA訴求の差別化."""

    competitor_approach: str = Field(default="", description="競合のアプローチ")
    our_differentiation: str = Field(default="", description="自社の差別化")


class KGIDiff(BaseModel):
    """KGI（CVR向上）での差別化."""

    cta_placement: CTAPlacementDiff = Field(default_factory=CTAPlacementDiff)
    cta_appeal: CTAAppealDiff = Field(default_factory=CTAAppealDiff)
    expected_effect: str = Field(default="", description="期待効果")


class FourPillarsDifferentiation(BaseModel):
    """4本柱での差別化設計."""

    neuroscience: NeuroscienceDiff = Field(default_factory=NeuroscienceDiff)
    behavioral_economics: BehavioralEconomicsDiff = Field(default_factory=BehavioralEconomicsDiff)
    llmo: LLMODiff = Field(default_factory=LLMODiff)
    kgi: KGIDiff = Field(default_factory=KGIDiff)


# =============================================================================
# 新規スキーマ: ThreePhaseDifferentiationStrategy（3フェーズ差別化）
# =============================================================================


class PhaseStrategy(BaseModel):
    """フェーズ戦略."""

    phase_name: str
    user_state: str = Field(default="", description="このフェーズでのユーザー心理")
    competitor_weakness: str = Field(default="", description="競合の弱点")
    our_differentiation: list[str] = Field(default_factory=list)
    expected_metrics: str = Field(default="", description="期待効果")


class ThreePhaseDifferentiationStrategy(BaseModel):
    """3フェーズごとの差別化戦略."""

    phase1: PhaseStrategy = Field(default_factory=lambda: PhaseStrategy(phase_name="不安・課題認識"))
    phase2: PhaseStrategy = Field(default_factory=lambda: PhaseStrategy(phase_name="理解・納得"))
    phase3: PhaseStrategy = Field(default_factory=lambda: PhaseStrategy(phase_name="行動決定"))


# =============================================================================
# 新規スキーマ: CompetitorCTAAnalysis
# =============================================================================


class CompetitorCTAAnalysis(BaseModel):
    """競合CTA分析."""

    cta_deployment_rate: float = Field(default=0.0, description="CTA設置率")
    average_cta_count: float = Field(default=0.0, description="平均CTA回数")
    main_cta_positions: list[str] = Field(default_factory=list, description="主なCTA配置位置")
    our_differentiation_strategy: str = Field(default="", description="自社の差別化戦略")


# =============================================================================
# 拡張版 Step3cOutput
# =============================================================================


class Step3cOutput(BaseModel):
    """Step 3C output schema."""

    # 既存フィールド（後方互換性維持）
    keyword: str
    competitor_profiles: list[CompetitorProfile] = Field(default_factory=list)
    market_overview: str = ""
    differentiation_strategies: list[DifferentiationStrategy] = Field(default_factory=list)
    gap_opportunities: list[GapOpportunity] = Field(default_factory=list)
    content_recommendations: list[str] = Field(default_factory=list)
    raw_analysis: str = ""

    # 新規フィールド（blog.System統合）
    word_count_analysis: WordCountAnalysis | None = Field(default=None, description="競合文字数分析")
    target_word_count: int | None = Field(default=None, description="最終確定文字数（ai_*モード時）")
    ranking_factor_analysis: RankingFactorAnalysis | None = Field(default=None, description="上位表示要因・ユーザー満足深層分析")
    four_pillars_differentiation: FourPillarsDifferentiation | None = Field(default=None, description="4本柱での差別化設計")
    three_phase_differentiation_strategy: ThreePhaseDifferentiationStrategy | None = Field(
        default=None, description="3フェーズごとの差別化戦略"
    )
    competitor_cta_analysis: CompetitorCTAAnalysis | None = Field(default=None, description="競合CTA分析")
