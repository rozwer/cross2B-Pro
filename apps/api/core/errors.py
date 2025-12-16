"""Error classification for workflow steps.

ErrorCategory determines retry behavior:
- RETRYABLE: Temporary failures, can retry with same parameters
- NON_RETRYABLE: Permanent failures, no retry will help
- VALIDATION_FAIL: Output validation failed, may need different approach
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ErrorCategory(str, Enum):
    """Classification of step errors for retry decisions."""

    RETRYABLE = "retryable"
    NON_RETRYABLE = "non_retryable"
    VALIDATION_FAIL = "validation_fail"


class StepError(BaseModel):
    """Error details from a failed step execution."""

    step_id: str = Field(..., description="Identifier of the failed step")
    category: ErrorCategory = Field(..., description="Error classification for retry logic")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(default=None, description="Additional error details")
    occurred_at: datetime = Field(..., description="When the error occurred")
    attempt: int = Field(..., ge=1, description="Which attempt number failed")

    def is_retryable(self) -> bool:
        """Check if this error allows retry."""
        return self.category == ErrorCategory.RETRYABLE

    def is_validation_failure(self) -> bool:
        """Check if this is a validation failure."""
        return self.category == ErrorCategory.VALIDATION_FAIL
