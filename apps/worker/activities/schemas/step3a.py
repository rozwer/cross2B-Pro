"""Step 3A: Query Analysis output schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class SearchIntent(BaseModel):
    """Search intent classification."""

    primary: Literal["informational", "navigational", "transactional", "commercial"]
    secondary: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class UserPersona(BaseModel):
    """User persona definition."""

    name: str
    demographics: str = ""
    goals: list[str] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    search_context: str = ""


class Step3aOutput(BaseModel):
    """Step 3A output schema."""

    keyword: str
    search_intent: SearchIntent
    personas: list[UserPersona] = Field(default_factory=list)
    content_expectations: list[str] = Field(default_factory=list)
    recommended_tone: str = ""
    raw_analysis: str
