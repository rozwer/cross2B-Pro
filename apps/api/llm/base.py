"""Base interface for LLM clients."""

from abc import ABC, abstractmethod
from typing import Any

from .schemas import LLMResponse


class LLMInterface(ABC):
    """Abstract base class for LLM clients.

    All LLM clients must implement this interface to ensure consistent
    behavior across different providers (Gemini, OpenAI, Anthropic).

    Important:
        - No fallback to other models/providers is allowed
        - Retry is allowed only with same conditions (max 3 times, with logging)
        - Token usage must be recorded for all operations
    """

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate text response from LLM.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            system_prompt: System-level instructions for the model
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response

        Returns:
            LLMResponse with content, token_usage, and model info

        Raises:
            RetryableLLMError: For temporary failures (can retry)
            NonRetryableLLMError: For permanent failures (should not retry)
        """
        pass

    @abstractmethod
    async def generate_json(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate JSON output from LLM with schema validation.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            system_prompt: System-level instructions for the model
            schema: JSON Schema for output validation

        Returns:
            Parsed and validated JSON dict

        Raises:
            RetryableLLMError: For temporary failures (can retry)
            NonRetryableLLMError: For permanent failures (should not retry)
            ValidationLLMError: For JSON parsing/validation failures
        """
        pass
