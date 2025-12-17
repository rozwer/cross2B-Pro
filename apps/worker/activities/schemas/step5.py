"""Step5 Primary Collection output schema."""

from typing import Literal

from pydantic import BaseModel, Field


class PrimarySource(BaseModel):
    """一次資料."""

    url: str
    title: str
    source_type: Literal[
        "academic_paper",
        "government_report",
        "statistics",
        "official_document",
        "industry_report",
        "news_article",
        "other",
    ] = "other"
    excerpt: str = Field(default="", max_length=500)
    credibility_score: float = Field(default=0.5, ge=0.0, le=1.0)
    verified: bool = False


class CollectionStats(BaseModel):
    """収集統計."""

    total_collected: int = 0
    total_verified: int = 0
    failed_queries: int = 0


class Step5Output(BaseModel):
    """Step5 の構造化出力."""

    step: str = "step5"
    keyword: str
    search_queries: list[str] = Field(default_factory=list)
    sources: list[PrimarySource] = Field(default_factory=list)
    invalid_sources: list[PrimarySource] = Field(default_factory=list)
    failed_queries: list[dict[str, str]] = Field(default_factory=list)
    collection_stats: CollectionStats = Field(default_factory=CollectionStats)
