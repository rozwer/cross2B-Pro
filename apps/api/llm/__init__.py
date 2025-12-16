"""LLMクライアントモジュール

各プロバイダー（Gemini, OpenAI, Anthropic等）のLLMクライアントを提供。

使用例:
    from apps.api.llm import GeminiClient, LLMResponse

    client = GeminiClient()
    response = await client.generate(
        messages=[{"role": "user", "content": "Hello"}],
        system_prompt="You are a helpful assistant.",
    )
"""

from .base import LLMInterface
from .exceptions import (
    ErrorCategory,
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMContentFilterError,
    LLMError,
    LLMInvalidRequestError,
    LLMJSONParseError,
    LLMRateLimitError,
    LLMServiceUnavailableError,
    LLMTimeoutError,
    LLMValidationError,
)
from .gemini import GeminiClient
from .schemas import (
    GeminiConfig,
    GeminiGroundingConfig,
    LLMCallMetadata,
    LLMMessage,
    LLMRequestConfig,
    LLMResponse,
    RetryConfig,
    TokenUsage,
)

__all__ = [
    # Base
    "LLMInterface",
    # Clients
    "GeminiClient",
    # Schemas
    "LLMResponse",
    "LLMMessage",
    "LLMRequestConfig",
    "LLMCallMetadata",
    "TokenUsage",
    "RetryConfig",
    "GeminiConfig",
    "GeminiGroundingConfig",
    # Exceptions
    "ErrorCategory",
    "LLMError",
    "LLMTimeoutError",
    "LLMRateLimitError",
    "LLMAuthenticationError",
    "LLMInvalidRequestError",
    "LLMContentFilterError",
    "LLMValidationError",
    "LLMJSONParseError",
    "LLMServiceUnavailableError",
    "LLMConfigurationError",
]
