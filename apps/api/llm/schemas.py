"""Schemas for LLM responses and related types."""

from enum import Enum
from pydantic import BaseModel, Field


class ErrorCategory(str, Enum):
    """Error classification for LLM operations.

    - RETRYABLE: Temporary failure (timeout, rate limit) - can retry with same conditions
    - NON_RETRYABLE: Permanent failure (auth error, invalid model) - should not retry
    - VALIDATION_FAIL: Output validation failed - may retry if repairable
    """
    RETRYABLE = "RETRYABLE"
    NON_RETRYABLE = "NON_RETRYABLE"
    VALIDATION_FAIL = "VALIDATION_FAIL"


class TokenUsage(BaseModel):
    """Token usage information from LLM response."""
    input: int = Field(..., description="Number of input tokens")
    output: int = Field(..., description="Number of output tokens")

    @property
    def total(self) -> int:
        return self.input + self.output


class LLMResponse(BaseModel):
    """Standard response from LLM operations."""
    content: str = Field(..., description="Generated content from LLM")
    token_usage: TokenUsage = Field(..., description="Token usage statistics")
    model: str = Field(..., description="Model identifier used for generation")
