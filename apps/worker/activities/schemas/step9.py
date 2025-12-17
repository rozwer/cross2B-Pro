"""Step 9 output schemas.

Final rewrite step schemas:
- RewriteChange: Individual rewrite change tracking
- RewriteMetrics: Final rewrite comparison metrics
- Step9Output: Final step output
"""

from pydantic import BaseModel, Field

from apps.worker.helpers.schemas import StepOutputBase


class RewriteChange(BaseModel):
    """Individual rewrite change."""

    change_type: str = Field(
        default="",
        description="Type: factcheck_correction, faq_addition, style, structure",
    )
    section: str = Field(default="")
    description: str = Field(default="")


class RewriteMetrics(BaseModel):
    """Final rewrite comparison metrics."""

    original_word_count: int = 0
    final_word_count: int = 0
    word_diff: int = 0
    sections_count: int = 0
    faq_integrated: bool = False
    factcheck_corrections_applied: int = 0


class Step9Output(StepOutputBase):
    """Step 9 output schema."""

    final_content: str = Field(default="", description="Final rewritten content")
    meta_description: str = Field(
        default="",
        max_length=160,
        description="Meta description for SEO",
    )
    changes_summary: list[RewriteChange] = Field(
        default_factory=list,
        description="List of changes made",
    )
    rewrite_metrics: RewriteMetrics = Field(default_factory=RewriteMetrics)
    internal_link_suggestions: list[str] = Field(
        default_factory=list,
        description="Suggested internal links",
    )
    quality_warnings: list[str] = Field(default_factory=list)
    model: str = Field(default="")
