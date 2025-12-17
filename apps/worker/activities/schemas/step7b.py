"""Step 7B output schemas.

Polishing and brush-up step schemas:
- PolishChange: Individual change tracking
- PolishMetrics: Polishing comparison metrics
- Step7bOutput: Final step output
"""

from pydantic import BaseModel, Field

from apps.worker.helpers.schemas import StepOutputBase


class PolishChange(BaseModel):
    """Individual polishing change."""

    change_type: str = Field(
        default="",
        description="Type: wording, flow, clarity, tone, restructure",
    )
    original_snippet: str = Field(default="")
    polished_snippet: str = Field(default="")
    section: str = Field(default="")


class PolishMetrics(BaseModel):
    """Polishing comparison metrics."""

    original_word_count: int = 0
    polished_word_count: int = 0
    word_diff: int = 0
    word_diff_percent: float = 0.0
    sections_preserved: int = 0
    sections_modified: int = 0


class Step7bOutput(StepOutputBase):
    """Step 7B output schema."""

    polished: str = Field(default="", description="Polished content (Markdown)")
    changes_summary: str = Field(default="", description="Summary of changes made")
    change_count: int = Field(default=0, description="Number of changes made")
    polish_metrics: PolishMetrics = Field(default_factory=PolishMetrics)
    quality_warnings: list[str] = Field(default_factory=list)
    model: str = Field(default="")
