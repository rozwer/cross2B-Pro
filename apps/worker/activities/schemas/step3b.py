"""Step 3B: Co-occurrence & Related Keywords output schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class KeywordItem(BaseModel):
    """Keyword item with metadata."""

    keyword: str
    category: Literal[
        "cooccurrence", "lsi", "related", "synonym", "long_tail"
    ] = "cooccurrence"
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    frequency: int = 0
    context: str = ""


class KeywordCluster(BaseModel):
    """Keyword cluster by theme."""

    theme: str
    keywords: list[KeywordItem] = Field(default_factory=list)
    relevance_to_main: float = Field(default=0.5, ge=0.0, le=1.0)


class Step3bOutput(BaseModel):
    """Step 3B output schema.

    This is the HEART of the SEO analysis - quality standards are strict.
    """

    primary_keyword: str
    cooccurrence_keywords: list[KeywordItem] = Field(
        default_factory=list, min_length=5
    )
    lsi_keywords: list[KeywordItem] = Field(default_factory=list)
    long_tail_variations: list[str] = Field(default_factory=list)
    keyword_clusters: list[KeywordCluster] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    raw_analysis: str
