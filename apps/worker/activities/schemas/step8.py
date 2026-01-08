"""Step 8 output schemas.

Fact check and FAQ generation step schemas:
- Claim: Individual claim extracted from content
- VerificationResult: Verification result for a claim
- FAQItem: FAQ question-answer pair
- Step8Output: Final step output

blog.System Ver8.3 enhancements:
- Verification categories (numeric, source, timeline, logical)
- FAQ LLMO optimization (voice search, structured data)
- Enhanced rejection analysis with severity levels
- Four pillars FAQ integration (neuroscience, behavioral economics, LLMO, KGI)
- Auto-correction prohibition (human review required)
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
    # blog.System extensions
    verification_category: Literal["numeric_data", "source_accuracy", "timeline_consistency", "logical_consistency"] | None = Field(
        default=None,
        description="Category of verification required",
    )
    data_anchor_id: str | None = Field(
        default=None,
        description="Reference to data anchor (e.g., [PS-01])",
    )


class VerificationResult(BaseModel):
    """Verification result for a claim."""

    claim_id: str = Field(default="")
    status: Literal["verified", "unverified", "contradicted", "partially_verified"] = Field(default="unverified")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: str = Field(default="", description="Supporting evidence")
    source: str = Field(default="", description="Source of verification")
    recommendation: str = Field(default="", description="Action recommendation")
    # blog.System extensions
    verification_method: str = Field(
        default="",
        description="Method used for verification (e.g., web search, source check)",
    )
    url_checked: bool = Field(default=False, description="Whether URL was verified")
    url_valid: bool | None = Field(default=None, description="URL validity result")


class VerificationCategoryResult(BaseModel):
    """Verification results by category.

    blog.System Ver8.3: Detailed verification categorization.
    """

    claims_checked: int = Field(default=0, description="Number of claims checked")
    verified: int = Field(default=0, description="Number verified successfully")
    issues: list[str] = Field(default_factory=list, description="Issues found")


class VerificationCategories(BaseModel):
    """Verification results organized by category.

    blog.System Ver8.3 requirement for detailed verification tracking.
    """

    numeric_data: VerificationCategoryResult = Field(
        default_factory=VerificationCategoryResult,
        description="Numeric data verification (statistics, percentages, amounts)",
    )
    source_accuracy: VerificationCategoryResult = Field(
        default_factory=VerificationCategoryResult,
        description="Source accuracy verification (organization names, publication titles)",
    )
    timeline_consistency: VerificationCategoryResult = Field(
        default_factory=VerificationCategoryResult,
        description="Timeline consistency verification (dates, years, sequences)",
    )
    logical_consistency: VerificationCategoryResult = Field(
        default_factory=VerificationCategoryResult,
        description="Logical consistency verification (comparisons, context, interpretations)",
    )


class FAQFourPillars(BaseModel):
    """Four pillars application for FAQ item.

    blog.System Ver8.3: Each FAQ must apply four pillars.
    """

    # 神経科学
    neuroscience_applied: bool = Field(
        default=False,
        description="Conclusion-first, Aha moment applied",
    )
    neuroscience_details: str = Field(
        default="",
        description="How neuroscience principles were applied",
    )

    # 行動経済学
    behavioral_economics_applied: bool = Field(
        default=False,
        description="Social proof, decision simplification applied",
    )
    behavioral_economics_details: str = Field(
        default="",
        description="How behavioral economics principles were applied",
    )

    # LLMO
    llmo_optimized: bool = Field(
        default=False,
        description="Voice search optimized, Q&A clearly separated",
    )
    llmo_details: str = Field(
        default="",
        description="LLMO optimization details",
    )

    # KGI
    kgi_integrated: bool = Field(
        default=False,
        description="CTA integration, internal link applied",
    )
    kgi_details: str = Field(
        default="",
        description="KGI integration details (CTA placement, internal links)",
    )


class FAQItem(BaseModel):
    """FAQ question-answer pair."""

    question: str = Field(default="")
    answer: str = Field(default="")
    related_claims: list[str] = Field(
        default_factory=list,
        description="Related claim IDs",
    )
    # blog.System extensions
    voice_search_optimized: bool = Field(
        default=False,
        description="Whether question is optimized for voice search",
    )
    question_word_used: str | None = Field(
        default=None,
        description="Interrogative word used (どのくらい, どのように, なぜ, いつ, etc.)",
    )
    answer_length: int = Field(
        default=0,
        description="Answer character count (target: 120-180 chars or bullet points)",
    )
    has_data_anchor: bool = Field(
        default=False,
        description="Whether answer includes data anchor",
    )
    has_cta: bool = Field(
        default=False,
        description="Whether FAQ includes CTA integration",
    )
    has_internal_link: bool = Field(
        default=False,
        description="Whether FAQ includes internal link to article section",
    )
    four_pillars: FAQFourPillars | None = Field(
        default=None,
        description="Four pillars application details",
    )


class FAQLLMOOptimization(BaseModel):
    """FAQ LLMO optimization summary.

    blog.System Ver8.3: Voice search and structured data optimization.
    """

    question_format_count: int = Field(
        default=0,
        description="Number of FAQs with proper question format",
    )
    voice_search_friendly: bool = Field(
        default=False,
        description="Whether FAQs are voice search friendly overall",
    )
    structured_data_ready: bool = Field(
        default=False,
        description="Whether FAQs are ready for structured data markup (FAQ schema)",
    )
    natural_language_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Score for natural language usage (vs keyword-stuffed)",
    )
    average_answer_length: int = Field(
        default=0,
        description="Average answer length in characters",
    )


class RejectionAnalysis(BaseModel):
    """Enhanced rejection analysis.

    blog.System Ver8.3: Detailed rejection recommendation with severity.
    IMPORTANT: Auto-correction is prohibited - human review required.
    """

    should_reject: bool = Field(
        default=False,
        description="Whether rejection is recommended",
    )
    severity: Literal["critical", "major", "minor", "none"] = Field(
        default="none",
        description="Severity level of issues",
    )
    reasons: list[str] = Field(
        default_factory=list,
        description="Reasons for rejection recommendation",
    )
    human_review_required: bool = Field(
        default=True,
        description="Whether human review is required (always true for contradictions)",
    )
    auto_correction_prohibited: bool = Field(
        default=True,
        description="Auto-correction is prohibited per blog.System rules",
    )
    suggested_actions: list[str] = Field(
        default_factory=list,
        description="Suggested actions for human reviewer",
    )


class VerificationSummary(BaseModel):
    """Summary of verification results."""

    verified_count: int = 0
    unverified_count: int = 0
    contradicted_count: int = 0
    partially_verified_count: int = 0
    # blog.System extensions
    total_claims: int = Field(default=0, description="Total number of claims checked")
    verification_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Percentage of claims fully verified",
    )
    data_anchors_verified: int = Field(
        default=0,
        description="Number of data anchors verified",
    )
    urls_checked: int = Field(default=0, description="Number of URLs checked")
    urls_valid: int = Field(default=0, description="Number of valid URLs")


class FAQSummary(BaseModel):
    """Summary of FAQ generation results.

    blog.System Ver8.3: FAQ statistics with four pillars compliance.
    """

    faq_count: int = Field(default=0, description="Number of FAQs generated (target: 10-15)")
    voice_search_optimized_count: int = Field(
        default=0,
        description="Number of voice-search optimized FAQs",
    )
    four_pillars_compliance_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Percentage of FAQs with all four pillars applied",
    )
    cta_integrated_count: int = Field(
        default=0,
        description="Number of FAQs with CTA integration",
    )
    internal_link_count: int = Field(
        default=0,
        description="Number of FAQs with internal links",
    )


class Step8Output(StepOutputBase):
    """Step 8 output schema.

    blog.System Ver8.3 enhancements:
    - Verification categories (numeric, source, timeline, logical)
    - FAQ LLMO optimization
    - Enhanced rejection analysis with severity
    - Auto-correction prohibition (human review required)
    """

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

    # blog.System Ver8.3 extensions
    verification_categories: VerificationCategories | None = Field(
        default=None,
        description="Detailed verification by category (numeric, source, timeline, logical)",
    )
    faq_llmo_optimization: FAQLLMOOptimization | None = Field(
        default=None,
        description="FAQ LLMO optimization summary",
    )
    faq_summary: FAQSummary | None = Field(
        default=None,
        description="FAQ generation summary with four pillars compliance",
    )
    rejection_analysis: RejectionAnalysis | None = Field(
        default=None,
        description="Enhanced rejection analysis with severity",
    )
    faq_section_markdown: str = Field(
        default="",
        description="Generated FAQ section in Markdown format",
    )
    references_verified: bool = Field(
        default=False,
        description="Whether all references were verified",
    )
