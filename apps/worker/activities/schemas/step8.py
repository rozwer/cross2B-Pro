"""Step 8 output schemas.

Fact check and FAQ generation step schemas:
- Claim: Individual claim extracted from content
- VerificationResult: Verification result for a claim
- FAQItem: FAQ question-answer pair
- Step8Output: Final step output
"""

from typing import Literal

from pydantic import BaseModel, Field

from apps.worker.helpers.schemas import StepOutputBase


class Claim(BaseModel):
    """Individual claim extracted from content."""

    claim_id: str = Field(default="", description="Unique claim identifier")
    text: str = Field(default="", description="Claim text")
    source_section: str = Field(default="", description="Source section in article")
    claim_type: Literal["statistic", "fact", "opinion", "definition"] = Field(
        default="fact",
        description="Type of claim",
    )


class VerificationResult(BaseModel):
    """Verification result for a claim."""

    claim_id: str = Field(default="")
    status: Literal[
        "verified", "unverified", "contradicted", "partially_verified"
    ] = Field(default="unverified")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: str = Field(default="", description="Supporting evidence")
    source: str = Field(default="", description="Source of verification")
    recommendation: str = Field(default="", description="Action recommendation")


class FAQItem(BaseModel):
    """FAQ question-answer pair."""

    question: str = Field(default="")
    answer: str = Field(default="")
    related_claims: list[str] = Field(
        default_factory=list,
        description="Related claim IDs",
    )


class VerificationSummary(BaseModel):
    """Summary of verification results."""

    verified_count: int = 0
    unverified_count: int = 0
    contradicted_count: int = 0
    partially_verified_count: int = 0


class Step8Output(StepOutputBase):
    """Step 8 output schema."""

    claims: list[Claim] = Field(default_factory=list, description="Extracted claims")
    verification_results: list[VerificationResult] = Field(
        default_factory=list,
        description="Verification results",
    )
    faq_items: list[FAQItem] = Field(default_factory=list, description="Generated FAQ")
    summary: VerificationSummary = Field(default_factory=VerificationSummary)
    has_contradictions: bool = Field(
        default=False,
        description="Whether contradictions were found",
    )
    critical_issues: list[str] = Field(
        default_factory=list,
        description="Critical issues found",
    )
    recommend_rejection: bool = Field(
        default=False,
        description="Whether rejection is recommended",
    )
    model: str = Field(default="")
