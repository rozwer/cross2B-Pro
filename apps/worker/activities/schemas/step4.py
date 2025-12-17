"""Step4 Strategic Outline output schema."""

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


class Step4Output(BaseModel):
    """Step4 の構造化出力."""

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
