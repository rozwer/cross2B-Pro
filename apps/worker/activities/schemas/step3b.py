"""Step 3B: Co-occurrence & Related Keywords output schemas.

This is the HEART of the SEO analysis workflow.
blog.System Ver8.3 requires:
- 100-150 co-occurrence keywords
- 30-50 related keywords
- 3-phase distribution (anxiety -> understanding -> action)
- LLMO optimization (voice search, question format)
- Behavioral economics triggers (6 principles)
"""

from typing import Literal

from pydantic import BaseModel, Field


class KeywordItem(BaseModel):
    """Keyword item with metadata."""

    keyword: str
    category: Literal["cooccurrence", "lsi", "related", "synonym", "long_tail"] = "cooccurrence"
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    frequency: int = 0
    context: str = ""
    # blog.System extensions
    phase: Literal[1, 2, 3] | None = Field(
        default=None,
        description="3-phase mapping: 1=anxiety, 2=understanding, 3=action",
    )
    behavioral_trigger: (
        Literal[
            "loss_aversion",
            "social_proof",
            "authority",
            "consistency",
            "liking",
            "scarcity",
        ]
        | None
    ) = Field(default=None, description="Behavioral economics trigger type")
    article_coverage: int = Field(default=0, description="Number of competitor articles containing this keyword")


class KeywordCluster(BaseModel):
    """Keyword cluster by theme."""

    theme: str
    keywords: list[KeywordItem] = Field(default_factory=list)
    relevance_to_main: float = Field(default=0.5, ge=0.0, le=1.0)
    # blog.System extension
    density_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Keyword density within cluster")


class ThreePhaseDistribution(BaseModel):
    """3-phase keyword distribution based on neuroscience.

    Phase 1: Amygdala activation - anxiety, problem recognition
    Phase 2: Prefrontal cortex - logical processing, understanding
    Phase 3: Striatum - reward prediction, action decision
    """

    phase1_keywords: list[KeywordItem] = Field(
        default_factory=list,
        description="Anxiety/problem recognition KWs (0-30% of article)",
    )
    phase2_keywords: list[KeywordItem] = Field(
        default_factory=list,
        description="Understanding/comparison KWs (30-75% of article)",
    )
    phase3_keywords: list[KeywordItem] = Field(
        default_factory=list,
        description="Action/urgency KWs (75-100% of article)",
    )


class LLMOOptimizedKeywords(BaseModel):
    """LLMO (Large Language Model Optimization) keywords.

    Optimized for voice search and AI-generated answers.
    """

    question_format: list[str] = Field(
        default_factory=list,
        description="Question-format KWs: 〜とは, 〜方法, 〜やり方, etc.",
    )
    voice_search: list[str] = Field(
        default_factory=list,
        description="Voice search KWs: どのように, なぜ, いつ, etc.",
    )


class BehavioralEconomicsTriggers(BaseModel):
    """Behavioral economics 6 principles for psychological triggers."""

    loss_aversion: list[str] = Field(
        default_factory=list,
        description="Loss aversion: 損失, 無駄, 失う, ○○万円の損",
    )
    social_proof: list[str] = Field(
        default_factory=list,
        description="Social proof: ○○社導入, ○○%が満足, 実績○○件",
    )
    authority: list[str] = Field(
        default_factory=list,
        description="Authority: 専門家, ○○研究, 厚生労働省",
    )
    consistency: list[str] = Field(
        default_factory=list,
        description="Consistency: まずは, 次に, 最後に",
    )
    liking: list[str] = Field(
        default_factory=list,
        description="Liking: お困りですよね, よく分かります, 私たちも",
    )
    scarcity: list[str] = Field(
        default_factory=list,
        description="Scarcity: 期間限定, 先着○名, 残り○枠",
    )


class CTAKeywords(BaseModel):
    """CTA (Call To Action) keywords for conversion optimization."""

    urgency: list[str] = Field(
        default_factory=list,
        description="Urgency: 今すぐ, すぐに, 即座に",
    )
    ease: list[str] = Field(
        default_factory=list,
        description="Ease: 簡単, 手軽, 3ステップ",
    )
    free: list[str] = Field(
        default_factory=list,
        description="Free: 無料, 0円, 費用なし",
    )
    expertise: list[str] = Field(
        default_factory=list,
        description="Expertise: 専門家, プロ, 実績",
    )


class KeywordDensityAnalysis(BaseModel):
    """Keyword density analysis across competitor articles."""

    main_keyword_density: float = Field(default=0.0, description="Main keyword density (target: 1.5-2.0%)")
    cooccurrence_densities: dict[str, float] = Field(
        default_factory=dict,
        description="Density per co-occurrence keyword (target: 0.5-1.0%)",
    )


class CompetitorKeywordGap(BaseModel):
    """Competitor keyword gap analysis for differentiation."""

    keyword: str
    coverage_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Rate of competitors using this KW")
    differentiation_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Opportunity score (higher = better differentiation)",
    )


# =============================================================================
# P2: エンティティ連鎖モデル（Codex Review対応）
# =============================================================================


class EntityNode(BaseModel):
    """エンティティノード（親子関係を持つ）.

    SEOにおいて、エンティティ（概念・物・人など）の関係性を明示することで、
    検索エンジンがコンテンツの意味を正確に理解できるようになる。
    """

    name: str = Field(..., description="エンティティ名（例: ドライバー採用）")
    entity_type: str = Field(default="concept", description="エンティティタイプ（concept/person/organization/place/thing）")
    parent: str | None = Field(default=None, description="親エンティティ名")
    children: list[str] = Field(default_factory=list, description="子エンティティ名リスト")
    related: list[str] = Field(default_factory=list, description="関連エンティティ名リスト")
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="重要度スコア")


class EntityChain(BaseModel):
    """エンティティ連鎖（P2: トピッククラスター強化）.

    親→子→関連のエンティティ階層を表現。
    Step6のH2/H3構造と紐付けて、記事の意味構造を強化。
    """

    root_entity: str = Field(..., description="ルートエンティティ（主要キーワード）")
    nodes: list[EntityNode] = Field(default_factory=list, description="エンティティノードリスト")
    depth: int = Field(default=3, ge=1, le=5, description="連鎖の深さ")


class EntitySectionMapping(BaseModel):
    """エンティティとセクションのマッピング（P2）.

    各エンティティをどのセクション（H2/H3）で扱うかを指定。
    これにより、記事構成とエンティティ構造の整合性を保証。
    """

    entity_name: str = Field(..., description="エンティティ名")
    target_section: str = Field(..., description="対象セクション（H2/H3タイトル）")
    section_level: int = Field(default=2, ge=2, le=4, description="セクションレベル（2=H2, 3=H3）")
    coverage_depth: str = Field(default="overview", description="カバレッジ深度（overview/detailed/comprehensive）")


class SectionIntentMapping(BaseModel):
    """セクション別ユーザー意図マッピング（P2）.

    各セクションが満たすべきユーザーの検索意図を明示。
    これにより、記事全体で検索意図を網羅的にカバー。
    """

    section_title: str = Field(..., description="セクションタイトル")
    primary_intent: str = Field(
        default="informational",
        description="主要検索意図（informational/navigational/transactional/commercial）",
    )
    secondary_intents: list[str] = Field(default_factory=list, description="副次的検索意図")
    target_keywords: list[str] = Field(default_factory=list, description="このセクションで狙うキーワード")
    phase: int = Field(default=2, ge=1, le=3, description="3フェーズのどこに位置するか")


class KeywordCategorization(BaseModel):
    """Keyword categorization by competitor coverage.

    Essential: 7+ out of 10 articles
    Standard: 4-6 out of 10 articles
    Unique: 1-3 out of 10 articles (differentiation opportunity)
    """

    essential: list[KeywordItem] = Field(default_factory=list, description="Must-have KWs (70%+ coverage)")
    standard: list[KeywordItem] = Field(default_factory=list, description="Common KWs (40-60% coverage)")
    unique: list[KeywordItem] = Field(default_factory=list, description="Differentiation KWs (10-30% coverage)")


class Step3bOutput(BaseModel):
    """Step 3B output schema.

    This is the HEART of the SEO analysis - quality standards are strict.

    blog.System Ver8.3 requirements:
    - 100-150 co-occurrence keywords (was: 5)
    - 30-50 related keywords
    - 3-phase distribution
    - LLMO optimization
    - Behavioral economics triggers
    """

    primary_keyword: str
    total_articles_analyzed: int = Field(default=10, description="Number of competitors")

    # Core keyword lists (expanded targets)
    cooccurrence_keywords: list[KeywordItem] = Field(
        default_factory=list,
        min_length=5,  # Validation minimum, target is 100-150
        description="Target: 100-150 keywords",
    )
    lsi_keywords: list[KeywordItem] = Field(default_factory=list, description="Latent Semantic Indexing keywords")
    related_keywords: list[KeywordItem] = Field(default_factory=list, description="Target: 30-50 keywords")
    long_tail_variations: list[str] = Field(default_factory=list)

    # blog.System extensions
    keyword_categorization: KeywordCategorization | None = Field(default=None, description="Essential/Standard/Unique categorization")
    three_phase_distribution: ThreePhaseDistribution | None = Field(default=None, description="3-phase neuroscience-based mapping")
    llmo_optimized_keywords: LLMOOptimizedKeywords | None = Field(default=None, description="LLMO/voice search optimization")
    behavioral_economics_triggers: BehavioralEconomicsTriggers | None = Field(
        default=None, description="6 principles for psychological triggers"
    )
    cta_keywords: CTAKeywords | None = Field(default=None, description="CTA/conversion keywords")
    keyword_density_analysis: KeywordDensityAnalysis | None = Field(default=None, description="Density analysis across competitors")
    competitor_keyword_gaps: list[CompetitorKeywordGap] = Field(default_factory=list, description="Differentiation opportunities")

    # Clustering and recommendations
    keyword_clusters: list[KeywordCluster] = Field(default_factory=list, description="Semantic clusters")
    recommendations: list[str] = Field(default_factory=list)
    raw_analysis: str = ""

    # Quality metrics
    extraction_summary: dict[str, int] = Field(
        default_factory=dict,
        description="Summary counts: cooccurrence, related, phase1/2/3, etc.",
    )

    # P2: エンティティ連鎖（Codex Review対応）
    entity_chain: EntityChain | None = Field(
        default=None,
        description="エンティティ連鎖（親→子→関連）。Step6のH2/H3構造と紐付け",
    )
    entity_to_section_map: list[EntitySectionMapping] = Field(
        default_factory=list,
        description="エンティティとセクションのマッピング。各エンティティをどのセクションで扱うか",
    )
    section_intent_map: list[SectionIntentMapping] = Field(
        default_factory=list,
        description="セクション別ユーザー意図マッピング。検索意図の網羅性を保証",
    )
