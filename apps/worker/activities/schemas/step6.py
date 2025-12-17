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
    usage: dict[str, int] = Field(default_factory=dict)
