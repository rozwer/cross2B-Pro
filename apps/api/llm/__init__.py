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

from .anthropic import AnthropicClient
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
from .nanobanana import ImageGenerationConfig, ImageGenerationResult, NanoBananaClient
from .openai import OpenAIClient
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
from .sanitizer import (
    UserInputSanitized,
    create_safe_user_message,
    escape_for_prompt,
    sanitize_user_input,
    validate_system_prompt,
)

__all__ = [
    # Base
    "LLMInterface",
    # Clients
    "AnthropicClient",
    "GeminiClient",
    "NanoBananaClient",
    "OpenAIClient",
    # Image Generation
    "ImageGenerationConfig",
    "ImageGenerationResult",
    # Schemas
    "LLMResponse",
    "LLMMessage",
    "LLMRequestConfig",
    "LLMCallMetadata",
    "TokenUsage",
    "RetryConfig",
    "GeminiConfig",
    "GeminiGroundingConfig",
    # Sanitizer (VULN-010)
    "sanitize_user_input",
    "escape_for_prompt",
    "UserInputSanitized",
    "create_safe_user_message",
    "validate_system_prompt",
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
