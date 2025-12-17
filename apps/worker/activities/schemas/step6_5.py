"""Step6.5 Integration Package output schema."""

from typing import Any

from pydantic import BaseModel, Field

from apps.worker.helpers.schemas import StepOutputBase


class InputSummary(BaseModel):
    """入力データサマリー."""

    step_id: str
    available: bool
    key_points: list[str] = Field(default_factory=list)
    data_quality: str = "unknown"  # good|fair|poor|unknown


class SectionBlueprint(BaseModel):
    """セクション設計図."""

    level: int = Field(default=2, ge=1, le=4)
    title: str = ""
    target_words: int = 0
    key_points: list[str] = Field(default_factory=list)
    sources_to_cite: list[str] = Field(default_factory=list)
    keywords_to_include: list[str] = Field(default_factory=list)


class PackageQuality(BaseModel):
    """パッケージ品質."""

    is_acceptable: bool = True
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)


class Step6_5Output(StepOutputBase):
    """Step6.5 の構造化出力."""

    step: str = "step6_5"
    integration_package: str = ""
    article_blueprint: dict[str, Any] = Field(default_factory=dict)
    section_blueprints: list[SectionBlueprint] = Field(default_factory=list)
    outline_summary: str = ""
    section_count: int = 0
    total_sources: int = 0
    input_summaries: list[InputSummary] = Field(default_factory=list)
    inputs_summary: dict[str, bool] = Field(default_factory=dict)
    quality: PackageQuality = Field(default_factory=PackageQuality)
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    handoff_notes: list[str] = Field(default_factory=list)
    model: str = ""
    usage: dict[str, int] = Field(default_factory=dict)
