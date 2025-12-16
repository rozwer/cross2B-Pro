"""Anthropic Claude API client implementation."""

import json
import logging
import os
from typing import Any, cast

from anthropic import AsyncAnthropic, APIError, APIConnectionError, RateLimitError, AuthenticationError, APIStatusError
from anthropic.types import MessageParam, ToolParam, ToolUseBlock

from .base import LLMInterface
from .schemas import LLMResponse, TokenUsage
from .exceptions import RetryableLLMError, NonRetryableLLMError, ValidationLLMError

logger = logging.getLogger(__name__)

# Supported models (no fallback - explicit selection only)
SUPPORTED_MODELS = [
    "claude-sonnet-4-20250514",
    "claude-opus-4-20250514",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
]

DEFAULT_MODEL = "claude-sonnet-4-20250514"
MAX_RETRIES = 3


class AnthropicClient(LLMInterface):
    """Anthropic Claude API client.

    Implements LLMInterface for Anthropic's Claude models.

    Important:
        - No fallback to other models is allowed
        - Retry is allowed only with same conditions (max 3 times)
        - All operations are logged
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        max_retries: int = MAX_RETRIES,
    ):
        """Initialize Anthropic client.

        Args:
            api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
            model: Model identifier to use. Must be in SUPPORTED_MODELS.
            max_retries: Maximum retry attempts for retryable errors.

        Raises:
            NonRetryableLLMError: If model is not in SUPPORTED_MODELS.
        """
        resolved_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise NonRetryableLLMError("ANTHROPIC_API_KEY is not set")

        if model not in SUPPORTED_MODELS:
            raise NonRetryableLLMError(
                f"Model '{model}' is not supported. Supported models: {SUPPORTED_MODELS}"
            )

        self.client = AsyncAnthropic(api_key=resolved_key)
        self.model = model
        self.max_retries = max_retries
        logger.info(f"AnthropicClient initialized with model={model}, max_retries={max_retries}")

    async def generate(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate text response from Claude.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
                     Supported roles: 'user', 'assistant'
            system_prompt: System-level instructions for the model
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens in response

        Returns:
            LLMResponse with content, token_usage, and model info

        Raises:
            RetryableLLMError: For temporary failures
            NonRetryableLLMError: For permanent failures
        """
        attempt = 0
        last_error: Exception | None = None

        while attempt < self.max_retries:
            attempt += 1
            try:
                logger.info(
                    f"Anthropic API call attempt {attempt}/{self.max_retries}, "
                    f"model={self.model}, temperature={temperature}, max_tokens={max_tokens}"
                )

                # Convert messages to Anthropic format
                anthropic_messages = self._convert_messages(messages)

                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=anthropic_messages,
                    temperature=temperature,
                )

                # Extract content from response
                content = ""
                for block in response.content:
                    if block.type == "text":
                        content += block.text

                token_usage = TokenUsage(
                    input=response.usage.input_tokens,
                    output=response.usage.output_tokens,
                )

                logger.info(
                    f"Anthropic API call succeeded, "
                    f"input_tokens={token_usage.input}, output_tokens={token_usage.output}"
                )

                return LLMResponse(
                    content=content,
                    token_usage=token_usage,
                    model=response.model,
                )

            except AuthenticationError as e:
                # Auth errors are non-retryable
                logger.error(f"Authentication error: {e}")
                raise NonRetryableLLMError(
                    f"Authentication failed: {e}",
                    original_error=e,
                )

            except RateLimitError as e:
                # Rate limit is retryable
                logger.warning(f"Rate limit error (attempt {attempt}/{self.max_retries}): {e}")
                last_error = e
                if attempt >= self.max_retries:
                    raise RetryableLLMError(
                        f"Rate limit exceeded after {self.max_retries} attempts: {e}",
                        original_error=e,
                    )
                # Continue to next attempt

            except APIConnectionError as e:
                # Connection errors are retryable
                logger.warning(f"Connection error (attempt {attempt}/{self.max_retries}): {e}")
                last_error = e
                if attempt >= self.max_retries:
                    raise RetryableLLMError(
                        f"Connection failed after {self.max_retries} attempts: {e}",
                        original_error=e,
                    )
                # Continue to next attempt

            except APIStatusError as e:
                # Check if the error is retryable based on status code
                if e.status_code >= 500:
                    logger.warning(f"Server error (attempt {attempt}/{self.max_retries}): {e}")
                    last_error = e
                    if attempt >= self.max_retries:
                        raise RetryableLLMError(
                            f"Server error after {self.max_retries} attempts: {e}",
                            original_error=e,
                        )
                    # Continue to next attempt
                else:
                    # Client errors (4xx except rate limit) are non-retryable
                    logger.error(f"API error: {e}")
                    raise NonRetryableLLMError(
                        f"API error: {e}",
                        original_error=e,
                    )

            except Exception as e:
                # Unknown errors are treated as non-retryable
                logger.error(f"Unexpected error: {e}")
                raise NonRetryableLLMError(
                    f"Unexpected error: {e}",
                    original_error=e,
                )

        # Should not reach here, but handle edge case
        raise RetryableLLMError(
            f"Failed after {self.max_retries} attempts",
            original_error=last_error,
        )

    async def generate_json(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate JSON output from Claude with schema validation.

        Uses tool_use feature to ensure structured JSON output.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            system_prompt: System-level instructions for the model
            schema: JSON Schema for output validation

        Returns:
            Parsed and validated JSON dict

        Raises:
            RetryableLLMError: For temporary failures
            NonRetryableLLMError: For permanent failures
            ValidationLLMError: For JSON parsing/validation failures
        """
        attempt = 0
        last_error: Exception | None = None

        # Create a tool definition from the schema
        tool_name = "json_output"
        tools: list[ToolParam] = [
            {
                "name": tool_name,
                "description": "Output the result as structured JSON",
                "input_schema": schema,
            }
        ]

        while attempt < self.max_retries:
            attempt += 1
            try:
                logger.info(
                    f"Anthropic API JSON call attempt {attempt}/{self.max_retries}, "
                    f"model={self.model}"
                )

                # Convert messages to Anthropic format
                anthropic_messages = self._convert_messages(messages)

                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=anthropic_messages,
                    tools=tools,
                    tool_choice={"type": "tool", "name": tool_name},
                )

                # Extract tool use from response
                for block in response.content:
                    if isinstance(block, ToolUseBlock) and block.name == tool_name:
                        logger.info(
                            f"Anthropic API JSON call succeeded, "
                            f"input_tokens={response.usage.input_tokens}, "
                            f"output_tokens={response.usage.output_tokens}"
                        )
                        return cast(dict[str, Any], block.input)

                # No tool use found - validation error
                logger.error("No tool_use block found in response")
                raise ValidationLLMError("No JSON output found in response")

            except AuthenticationError as e:
                logger.error(f"Authentication error: {e}")
                raise NonRetryableLLMError(
                    f"Authentication failed: {e}",
                    original_error=e,
                )

            except RateLimitError as e:
                logger.warning(f"Rate limit error (attempt {attempt}/{self.max_retries}): {e}")
                last_error = e
                if attempt >= self.max_retries:
                    raise RetryableLLMError(
                        f"Rate limit exceeded after {self.max_retries} attempts: {e}",
                        original_error=e,
                    )

            except APIConnectionError as e:
                logger.warning(f"Connection error (attempt {attempt}/{self.max_retries}): {e}")
                last_error = e
                if attempt >= self.max_retries:
                    raise RetryableLLMError(
                        f"Connection failed after {self.max_retries} attempts: {e}",
                        original_error=e,
                    )

            except APIStatusError as e:
                if e.status_code >= 500:
                    logger.warning(f"Server error (attempt {attempt}/{self.max_retries}): {e}")
                    last_error = e
                    if attempt >= self.max_retries:
                        raise RetryableLLMError(
                            f"Server error after {self.max_retries} attempts: {e}",
                            original_error=e,
                        )
                else:
                    logger.error(f"API error: {e}")
                    raise NonRetryableLLMError(
                        f"API error: {e}",
                        original_error=e,
                    )

            except ValidationLLMError:
                # Re-raise validation errors without retry
                raise

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                raise ValidationLLMError(
                    f"Failed to parse JSON response: {e}",
                    original_error=e,
                )

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise NonRetryableLLMError(
                    f"Unexpected error: {e}",
                    original_error=e,
                )

        raise RetryableLLMError(
            f"Failed after {self.max_retries} attempts",
            original_error=last_error,
        )

    def _convert_messages(self, messages: list[dict[str, Any]]) -> list[MessageParam]:
        """Convert standard message format to Anthropic format.

        Args:
            messages: List of message dicts with 'role' and 'content' keys

        Returns:
            List of messages in Anthropic MessageParam format
        """
        anthropic_messages: list[MessageParam] = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Anthropic only supports 'user' and 'assistant' roles
            # 'system' role is handled separately
            if role == "system":
                # Skip system messages - they should be passed via system parameter
                continue
            elif role == "user":
                anthropic_messages.append({"role": "user", "content": content})
            elif role == "assistant":
                anthropic_messages.append({"role": "assistant", "content": content})
            else:
                # Map unknown roles to 'user'
                logger.warning(f"Unknown role '{role}' mapped to 'user'")
                anthropic_messages.append({"role": "user", "content": content})

        return anthropic_messages
