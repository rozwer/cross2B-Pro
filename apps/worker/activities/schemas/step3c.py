"""Step 3C: Competitor Analysis output schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class CompetitorProfile(BaseModel):
    """Competitor profile analysis."""

    url: str
    title: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    content_focus: list[str] = Field(default_factory=list)
    unique_value: str = ""
    threat_level: Literal["high", "medium", "low"] = "medium"


class DifferentiationStrategy(BaseModel):
    """Differentiation strategy recommendation."""

    category: Literal["content", "expertise", "format", "depth", "perspective"]
    description: str
    priority: Literal["must", "should", "nice_to_have"] = "should"
    implementation_hint: str = ""


class GapOpportunity(BaseModel):
    """Market gap opportunity."""

    gap_type: str
    description: str
    competitors_missing: list[str] = Field(default_factory=list)
    value_potential: float = Field(default=0.5, ge=0.0, le=1.0)


class Step3cOutput(BaseModel):
    """Step 3C output schema."""

    keyword: str
    competitor_profiles: list[CompetitorProfile] = Field(default_factory=list)
    market_overview: str = ""
    differentiation_strategies: list[DifferentiationStrategy] = Field(
        default_factory=list
    )
    gap_opportunities: list[GapOpportunity] = Field(default_factory=list)
    content_recommendations: list[str] = Field(default_factory=list)
    raw_analysis: str
