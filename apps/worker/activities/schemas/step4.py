"""Step4 Strategic Outline output schema.

blog.System Ver8.3 対応:
- TitleMetadata: タイトルルール検証（32文字、括弧禁止、数字含む）
- PhaseStructure: 3フェーズ構成（Phase1/2/3文字数配分）
- SectionFourPillars: セクション別4本柱実装
- CTAPlacements: 3段階CTA配置（Early/Mid/Final）
- WordCountTracking: 文字数管理
"""

from pydantic import BaseModel, Field


class OutlineSection(BaseModel):
    """アウトラインセクション."""

    level: int = Field(..., ge=1, le=4)
    title: str
    description: str = ""
    target_word_count: int = 0
    keywords_to_include: list[str] = Field(default_factory=list)
    subsections: list["OutlineSection"] = Field(default_factory=list)


OutlineSection.model_rebuild()


class OutlineQuality(BaseModel):
    """アウトライン品質."""

    is_acceptable: bool
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)


class OutlineMetrics(BaseModel):
    """アウトラインメトリクス."""

    word_count: int
    char_count: int
    h2_count: int
    h3_count: int
    h4_count: int


# =============================================================================
# blog.System Ver8.3 対応モデル
# =============================================================================


class TitleMetadata(BaseModel):
    """タイトルメタデータ.

    タイトルルール検証:
    - 32文字前後
    - 括弧禁止
    - 数字を含む
    - キーワードを含む
    """

    char_count: int = Field(default=0, ge=0, description="タイトル文字数（32文字前後が理想）")
    contains_number: bool = Field(default=False, description="数字を含むか")
    contains_keyword: bool = Field(default=False, description="キーワードを含むか")
    no_brackets: bool = Field(default=True, description="括弧を含まないか")
    validation_passed: bool = Field(default=False, description="全ルールをパスしたか")
    issues: list[str] = Field(default_factory=list, description="違反項目")


class NeuroscienceConfig(BaseModel):
    """神経科学設定."""

    cognitive_load: str = Field(default="medium", description="認知負荷レベル（low/medium/high）")
    phase: str = Field(default="2", description="フェーズ（1/2/3）")
    attention_hooks: list[str] = Field(default_factory=list, description="注意を引く要素")


class BehavioralEconomicsConfig(BaseModel):
    """行動経済学設定."""

    principles_applied: list[str] = Field(default_factory=list, description="適用する原則")
    bias_triggers: list[str] = Field(default_factory=list, description="バイアストリガー")


class LLMOConfig(BaseModel):
    """LLMO設定."""

    token_target: int = Field(default=500, ge=100, le=1000, description="目標トークン数（400-600が理想）")
    question_heading: bool = Field(default=False, description="疑問形見出しか")
    structured_data: bool = Field(default=False, description="構造化データを含むか")


class KGIConfig(BaseModel):
    """KGI設定."""

    cta_placement: str = Field(default="none", description="CTA配置（none/early/mid/final）")
    conversion_goal: str = Field(default="", description="コンバージョン目標")


class SectionFourPillars(BaseModel):
    """セクション別4本柱実装.

    各H2セクションに4本柱（神経科学・行動経済学・LLMO・KGI）を実装。
    """

    section_title: str = Field(..., description="セクションタイトル")
    neuroscience: NeuroscienceConfig = Field(default_factory=NeuroscienceConfig, description="神経科学設定")
    behavioral_economics: BehavioralEconomicsConfig = Field(default_factory=BehavioralEconomicsConfig, description="行動経済学設定")
    llmo: LLMOConfig = Field(default_factory=LLMOConfig, description="LLMO設定")
    kgi: KGIConfig = Field(default_factory=KGIConfig, description="KGI設定")


class PhaseSection(BaseModel):
    """フェーズ別セクション."""

    word_count_ratio: float = Field(default=0.0, ge=0.0, le=1.0, description="文字数比率")
    target_word_count: int = Field(default=0, ge=0, description="目標文字数")
    sections: list[str] = Field(default_factory=list, description="含まれるセクションタイトル")


class ThreePhaseStructure(BaseModel):
    """3フェーズ構成.

    Phase1: 不安・課題認識（10-15%）
    Phase2: 理解・納得（65-75%）
    Phase3: 行動決定（10-15%）
    """

    phase1: PhaseSection = Field(default_factory=PhaseSection, description="Phase1: 不安・課題認識")
    phase2: PhaseSection = Field(default_factory=PhaseSection, description="Phase2: 理解・納得")
    phase3: PhaseSection = Field(default_factory=PhaseSection, description="Phase3: 行動決定")
    is_balanced: bool = Field(default=False, description="バランスが取れているか")
    balance_issues: list[str] = Field(default_factory=list, description="バランスの問題点")


class CTAPosition(BaseModel):
    """CTA配置位置."""

    position: int = Field(default=0, ge=0, description="配置位置（文字数）")
    section: str = Field(default="", description="配置セクション")
    cta_type: str = Field(default="", description="CTAタイプ")


class CTAPlacements(BaseModel):
    """3段階CTA配置.

    Early: 650文字付近
    Mid: 2800文字付近
    Final: target - 500文字付近
    """

    early: CTAPosition | None = Field(default=None, description="Early CTA（650文字付近）")
    mid: CTAPosition | None = Field(default=None, description="Mid CTA（2800文字付近）")
    final: CTAPosition | None = Field(default=None, description="Final CTA（末尾付近）")


class WordCountTracking(BaseModel):
    """文字数管理."""

    target: int = Field(default=0, ge=0, description="目標文字数")
    sections_total: int = Field(default=0, ge=0, description="セクション合計")
    variance: int = Field(default=0, description="差分")
    variance_percentage: float = Field(default=0.0, description="差分率（%）")
    is_within_tolerance: bool = Field(default=False, description="許容範囲内か（±10%）")


class Step4Output(BaseModel):
    """Step4 の構造化出力.

    blog.System Ver8.3 対応:
    - title_metadata: タイトルルール検証
    - three_phase_structure: 3フェーズ構成
    - four_pillars_per_section: セクション別4本柱実装
    - cta_placements: 3段階CTA配置
    - word_count_tracking: 文字数管理
    """

    step: str = "step4"
    keyword: str
    article_title: str = ""
    meta_description: str = ""
    outline: str
    sections: list[OutlineSection] = Field(default_factory=list)
    key_differentiators: list[str] = Field(default_factory=list)
    metrics: OutlineMetrics
    quality: OutlineQuality
    model: str = ""
    usage: dict[str, int] = Field(default_factory=dict)

    # blog.System Ver8.3 対応フィールド（後方互換性のため Optional）
    title_metadata: TitleMetadata | None = Field(default=None, description="タイトルルール検証")
    three_phase_structure: ThreePhaseStructure | None = Field(default=None, description="3フェーズ構成")
    four_pillars_per_section: list[SectionFourPillars] = Field(default_factory=list, description="セクション別4本柱実装")
    cta_placements: CTAPlacements | None = Field(default=None, description="3段階CTA配置")
    word_count_tracking: WordCountTracking | None = Field(default=None, description="文字数管理")
