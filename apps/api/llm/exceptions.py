"""Custom exceptions for LLM operations."""

from .schemas import ErrorCategory


class LLMError(Exception):
    """Base exception for LLM operations."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        original_error: Exception | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.original_error = original_error

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, category={self.category})"


class RetryableLLMError(LLMError):
    """Retryable LLM error (timeout, rate limit, temporary API issues)."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message, ErrorCategory.RETRYABLE, original_error)


class NonRetryableLLMError(LLMError):
    """Non-retryable LLM error (auth error, invalid model, permanent failure)."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message, ErrorCategory.NON_RETRYABLE, original_error)


class ValidationLLMError(LLMError):
    """Validation failure error (invalid JSON output, schema mismatch)."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message, ErrorCategory.VALIDATION_FAIL, original_error)
