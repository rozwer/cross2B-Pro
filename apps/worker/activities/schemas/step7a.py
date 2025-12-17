"""Step7a Draft Generation output schema."""

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
    """Step7a の構造化出力."""

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
    usage: dict[str, int] = Field(default_factory=dict)
