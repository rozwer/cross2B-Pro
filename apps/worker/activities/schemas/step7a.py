"""Step7a Draft Generation output schema.

Extended for blog.System Ver8.3 integration with:
- Section-level word count tracking
- Four pillars implementation tracking per section
- CTA implementation tracking (early/mid/final)
- Split generation support for large articles
- Word count progress tracking
"""

from typing import Any

from pydantic import BaseModel, Field

from apps.worker.helpers.schemas import StepOutputBase


class DraftSection(BaseModel):
    """ドラフトセクション."""

    level: int = Field(default=2, ge=1, le=4)
    title: str = ""
    content: str = ""
    word_count: int = 0
    has_subheadings: bool = False


# ============================================================
# blog.System Ver8.3 Extensions
# ============================================================


class SectionWordCount(BaseModel):
    """Section-level word count tracking for blog.System Ver8.3.

    Tracks target vs actual word count per section with variance analysis.
    """

    section_title: str = Field(
        default="",
        description="Section H2 title",
    )
    target: int = Field(
        default=0,
        ge=0,
        description="Target word count for this section (400-600 tokens typically)",
    )
    actual: int = Field(
        default=0,
        ge=0,
        description="Actual word count generated",
    )
    variance: int = Field(
        default=0,
        description="Difference between actual and target (can be negative)",
    )
    is_within_tolerance: bool = Field(
        default=True,
        description="Whether variance is within acceptable range (±20%)",
    )


class NeuroscienceImplementation(BaseModel):
    """Neuroscience pillar implementation details."""

    applied: bool = Field(
        default=False,
        description="Whether neuroscience principles were applied",
    )
    details: str = Field(
        default="",
        description="Details of how neuroscience was applied (e.g., emotional triggers used)",
    )


class BehavioralEconomicsImplementation(BaseModel):
    """Behavioral economics pillar implementation details."""

    principles_used: list[str] = Field(
        default_factory=list,
        description="List of principles used (損失回避, 社会的証明, 権威, 希少性)",
    )


class LLMOImplementation(BaseModel):
    """LLMO (Large Language Model Optimization) pillar implementation details."""

    token_count: int = Field(
        default=0,
        ge=0,
        description="Token count for this section",
    )
    is_independent: bool = Field(
        default=False,
        description="Whether section is independently understandable",
    )


class KGIImplementation(BaseModel):
    """KGI (Key Goal Indicator) pillar implementation details."""

    cta_present: bool = Field(
        default=False,
        description="Whether CTA is present in this section",
    )
    cta_type: str | None = Field(
        default=None,
        description="Type of CTA if present (inquiry, purchase, signup, etc.)",
    )


class FourPillarsImplementation(BaseModel):
    """Four pillars implementation tracking for a single section.

    Tracks implementation of the 4 pillars (神経科学, 行動経済学, LLMO, KGI)
    for each section in the article.
    """

    section_title: str = Field(
        default="",
        description="Section H2 title",
    )
    neuroscience: NeuroscienceImplementation = Field(
        default_factory=NeuroscienceImplementation,
        description="Neuroscience pillar implementation",
    )
    behavioral_economics: BehavioralEconomicsImplementation = Field(
        default_factory=BehavioralEconomicsImplementation,
        description="Behavioral economics pillar implementation",
    )
    llmo: LLMOImplementation = Field(
        default_factory=LLMOImplementation,
        description="LLMO pillar implementation",
    )
    kgi: KGIImplementation = Field(
        default_factory=KGIImplementation,
        description="KGI pillar implementation",
    )


class CTAPosition(BaseModel):
    """CTA position tracking for a specific placement."""

    position: int = Field(
        default=0,
        ge=0,
        description="Section index where CTA should be placed",
    )
    implemented: bool = Field(
        default=False,
        description="Whether CTA was actually implemented at this position",
    )


class CTAImplementation(BaseModel):
    """CTA implementation tracking for early/mid/final positions.

    Blog articles typically have 3 CTA positions:
    - early: After first major section (hook readers early)
    - mid: Middle of article (re-engage readers)
    - final: Before conclusion (final conversion push)
    """

    early: CTAPosition = Field(
        default_factory=CTAPosition,
        description="Early CTA position (after first H2)",
    )
    mid: CTAPosition = Field(
        default_factory=CTAPosition,
        description="Mid CTA position (article midpoint)",
    )
    final: CTAPosition = Field(
        default_factory=CTAPosition,
        description="Final CTA position (before conclusion)",
    )


class WordCountTracking(BaseModel):
    """Overall word count progress tracking.

    Used to monitor progress during split generation and ensure
    target word count is achieved.
    """

    target: int = Field(
        default=0,
        ge=0,
        description="Target total word count",
    )
    current: int = Field(
        default=0,
        ge=0,
        description="Current word count achieved",
    )
    remaining: int = Field(
        default=0,
        ge=0,
        description="Remaining words to generate",
    )
    progress_percent: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Progress percentage (0-100)",
    )


class SplitGeneration(BaseModel):
    """Split generation tracking for large articles.

    When article exceeds token limits, generation is split into 3-5 parts.
    This tracks the progress of split generation.
    """

    total_parts: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Total number of parts for this article (1 = no split)",
    )
    current_part: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Current part being generated",
    )
    completed_sections: list[str] = Field(
        default_factory=list,
        description="List of completed section titles",
    )


class DraftQualityMetrics(BaseModel):
    """ドラフト品質メトリクス."""

    word_count: int = 0
    char_count: int = 0
    section_count: int = 0
    avg_section_length: int = 0
    keyword_density: float = 0.0
    has_introduction: bool = False
    has_conclusion: bool = False


class DraftQuality(BaseModel):
    """ドラフト品質."""

    is_acceptable: bool = True
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)


class GenerationStats(BaseModel):
    """生成統計."""

    word_count: int = 0
    char_count: int = 0
    llm_reported_word_count: int = 0
    continuation_used: bool = False
    checkpoint_resumed: bool = False


class Step7aOutput(StepOutputBase):
    """Step7a の構造化出力.

    Extended for blog.System Ver8.3 integration with:
    - Section-level word count tracking
    - Four pillars implementation tracking per section
    - CTA implementation tracking (early/mid/final)
    - Split generation support
    - Word count progress tracking
    """

    step: str = "step7a"
    draft: str = ""
    sections: list[DraftSection] = Field(default_factory=list)
    section_count: int = 0
    cta_positions: list[str] = Field(default_factory=list)
    quality_metrics: DraftQualityMetrics = Field(default_factory=DraftQualityMetrics)
    quality: DraftQuality = Field(default_factory=DraftQuality)
    stats: GenerationStats = Field(default_factory=GenerationStats)
    generation_stats: dict[str, Any] = Field(default_factory=dict)
    continued: bool = False  # 分割生成で続きを生成した場合
    model: str = ""
    token_usage: dict[str, int] = Field(default_factory=dict)
    # blog.System Ver8.3 extensions
    section_word_counts: list[SectionWordCount] = Field(
        default_factory=list,
        description="Section-level word count tracking with variance analysis",
    )
    four_pillars_implementation: list[FourPillarsImplementation] = Field(
        default_factory=list,
        description="Four pillars implementation tracking per section",
    )
    cta_implementation: CTAImplementation = Field(
        default_factory=CTAImplementation,
        description="CTA implementation tracking (early/mid/final)",
    )
    word_count_tracking: WordCountTracking = Field(
        default_factory=WordCountTracking,
        description="Overall word count progress tracking",
    )
    split_generation: SplitGeneration = Field(
        default_factory=SplitGeneration,
        description="Split generation tracking for large articles",
    )
