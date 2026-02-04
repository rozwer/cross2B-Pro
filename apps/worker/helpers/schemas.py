"""Shared Pydantic schemas for worker helpers.

This module provides common data models used across all workflow steps:
- Quality validation results
- Parse results for LLM output
- Text and Markdown metrics
- Checkpoint metadata
- Base output classes
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# =============================================================================
# Quality-related schemas
# =============================================================================


class QualityResult(BaseModel):
    """Quality validation result (common for all validators)."""

    is_acceptable: bool
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        """Alias for is_acceptable for backward compatibility."""
        return self.is_acceptable


class InputValidationResult(BaseModel):
    """Input validation result."""

    is_valid: bool
    missing_required: list[str] = Field(default_factory=list)
    missing_recommended: list[str] = Field(default_factory=list)
    quality_issues: list[str] = Field(default_factory=list)


class CompletenessResult(BaseModel):
    """Completeness check result."""

    is_complete: bool
    is_truncated: bool = False
    issues: list[str] = Field(default_factory=list)


# =============================================================================
# Parse-related schemas
# =============================================================================


class ParseResult(BaseModel):
    """JSON parse result."""

    success: bool
    data: dict[str, Any] | list[Any] | None = None
    raw: str = ""
    format_detected: str = ""  # "json", "markdown", "unknown"
    fixes_applied: list[str] = Field(default_factory=list)


# =============================================================================
# Metrics-related schemas
# =============================================================================


class TextMetrics(BaseModel):
    """Text metrics."""

    char_count: int
    word_count: int
    paragraph_count: int
    sentence_count: int


class MarkdownMetrics(BaseModel):
    """Markdown metrics."""

    h1_count: int = 0
    h2_count: int = 0
    h3_count: int = 0
    h4_count: int = 0
    list_count: int = 0
    code_block_count: int = 0
    link_count: int = 0
    image_count: int = 0


# =============================================================================
# Checkpoint-related schemas
# =============================================================================


class CheckpointMetadata(BaseModel):
    """Checkpoint metadata."""

    phase: str
    created_at: datetime
    input_digest: str | None = None
    step_id: str = ""


# =============================================================================
# Activity output base class
# =============================================================================


class StepOutputBase(BaseModel):
    """Base class for step outputs."""

    step: str
    keyword: str
    execution_time_ms: int = 0
    token_usage: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
