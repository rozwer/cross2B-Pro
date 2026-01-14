"""Step6 Enhanced Outline output schema."""

from pydantic import BaseModel, Field

from apps.worker.helpers.schemas import StepOutputBase


class EnhancedSection(BaseModel):
    """拡張されたセクション."""

    level: int = Field(..., ge=1, le=4)
    title: str
    original_content: str = ""
    enhanced_content: str = ""
    sources_referenced: list[str] = Field(default_factory=list)
    enhancement_type: str = "detail"  # elaboration|detail|evidence|example


class EnhancementSummary(BaseModel):
    """拡張サマリー."""

    sections_enhanced: int = 0
    sections_added: int = 0
    sources_integrated: int = 0
    total_word_increase: int = 0


class EnhancedOutlineMetrics(BaseModel):
    """拡張アウトラインメトリクス."""

    word_count: int = 0
    char_count: int = 0
    h2_count: int = 0
    h3_count: int = 0
    h4_count: int = 0
    original_word_count: int = 0
    word_increase: int = 0


class EnhancedOutlineQuality(BaseModel):
    """拡張アウトライン品質."""

    is_acceptable: bool = True
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)


class DataAnchorPlacement(BaseModel):
    """データアンカー配置情報."""

    section_title: str = Field(..., description="配置先セクションタイトル")
    anchor_type: str = Field(
        ...,
        description="アンカータイプ（intro_impact/section_evidence/summary）",
    )
    data_point: str = Field(..., description="データポイント（数値・事実）")
    source_citation: str = Field(default="", description="出典情報")


class FourPillarsVerification(BaseModel):
    """4本柱検証結果."""

    sections_verified: int = Field(default=0, ge=0, description="検証済みセクション数")
    issues_found: list[str] = Field(default_factory=list, description="発見された問題")
    auto_corrections: list[str] = Field(default_factory=list, description="自動修正内容")
    pillar_scores: dict[str, float] = Field(
        default_factory=dict, description="各本柱のスコア（neuroscience/behavioral_economics/llmo/kgi）"
    )


class CitationFormat(BaseModel):
    """出典フォーマット設定."""

    style: str = Field(default="inline", description="スタイル（inline/footnote）")
    examples: list[str] = Field(default_factory=list, description="フォーマット例")


class Step6Output(StepOutputBase):
    """Step6 の構造化出力."""

    step: str = "step6"
    enhanced_outline: str = ""
    sections: list[EnhancedSection] = Field(default_factory=list)
    enhancement_summary: EnhancementSummary = Field(default_factory=EnhancementSummary)
    source_citations: dict[str, list[str]] = Field(default_factory=dict)
    original_outline_hash: str = ""
    metrics: EnhancedOutlineMetrics = Field(default_factory=EnhancedOutlineMetrics)
    quality: EnhancedOutlineQuality = Field(default_factory=EnhancedOutlineQuality)
    sources_used: int = 0
    model: str = ""
    model_config_data: dict[str, str] = Field(default_factory=dict, description="モデル設定（platform, model）")
    token_usage: dict[str, int] = Field(default_factory=dict)

    # blog.System 統合用フィールド（オプショナル）
    data_anchor_placements: list[DataAnchorPlacement] = Field(default_factory=list, description="データアンカー配置情報")
    four_pillars_verification: FourPillarsVerification | None = Field(default=None, description="4本柱検証結果")
    citation_format: CitationFormat | None = Field(default=None, description="出典フォーマット設定")
