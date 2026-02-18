"""Anthropic Claude API client implementation."""

import asyncio
import json
import logging
import os
from typing import Any, cast

import httpx
from anthropic import (
    APIConnectionError,
    APIStatusError,
    AsyncAnthropic,
    AuthenticationError,
    RateLimitError,
)
from anthropic.types import MessageParam, ToolParam, ToolUseBlock

from .base import LLMInterface, _maybe_close_client
from .exceptions import NonRetryableLLMError, RetryableLLMError, ValidationLLMError
from .schemas import (
    AnthropicConfig,
    LLMCallMetadata,
    LLMMessage,
    LLMRequestConfig,
    LLMResponse,
    TokenUsage,
)

logger = logging.getLogger(__name__)

# Supported models (no fallback - explicit selection only)
# 最新: claude-opus-4.6, claude-sonnet-4.5
SUPPORTED_MODELS = [
    "claude-opus-4-6",  # 最新Opus 4.6
    "claude-opus-4-5-20251124",  # Opus 4.5
    "claude-sonnet-4-5-20250929",  # Sonnet 4.5
    "claude-haiku-4-5",  # Haiku 4.5（高速・低コスト）
    "claude-opus-4-1-20250805",  # Opus 4.1
    "claude-sonnet-4-20250514",  # Sonnet 4
    "claude-opus-4-20250514",  # Opus 4
]

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
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
        anthropic_config: AnthropicConfig | None = None,
    ):
        """Initialize Anthropic client.

        Args:
            api_key: Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
            model: Model identifier to use. Must be in SUPPORTED_MODELS.
            max_retries: Maximum retry attempts for retryable errors.
            anthropic_config: Anthropic固有の設定

        Raises:
            NonRetryableLLMError: If model is not in SUPPORTED_MODELS.
        """
        resolved_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise NonRetryableLLMError("ANTHROPIC_API_KEY is not set")

        if model not in SUPPORTED_MODELS:
            # 警告のみ（DBで管理されているモデルリストを優先）
            logger.warning(f"Model '{model}' is not in known models list. Available: {SUPPORTED_MODELS}")

        # Configure httpx client with connection pool limits
        # max_connections: total connection pool size
        # max_keepalive_connections: connections kept alive for reuse
        http_client = httpx.AsyncClient(
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
            ),
            timeout=httpx.Timeout(timeout=600.0, connect=30.0),
        )
        self.client = AsyncAnthropic(api_key=resolved_key, http_client=http_client)
        self._http_client = http_client
        self._model = model
        self.max_retries = max_retries
        self._anthropic_config = anthropic_config or AnthropicConfig()
        logger.info(f"AnthropicClient initialized with model={model}, max_retries={max_retries}")

    def configure_extended_thinking(
        self,
        enabled: bool = True,
        budget_tokens: int | None = None,
    ) -> None:
        """Extended Thinkingを設定（Claude 4系向け）

        Args:
            enabled: Extended Thinkingを有効にするかどうか
            budget_tokens: Thinking用のトークン予算（最小1024）
        """
        self._anthropic_config.extended_thinking.enabled = enabled
        if budget_tokens is not None:
            self._anthropic_config.extended_thinking.budget_tokens = budget_tokens
        logger.info(f"Extended thinking {'enabled' if enabled else 'disabled'}, budget_tokens={budget_tokens}")

    def set_effort(self, effort: str | None = None) -> None:
        """Effort levelを設定（Claude Opus 4.5向け）

        Args:
            effort: low, medium, high
        """
        self._anthropic_config.effort = effort
        logger.info(f"Effort set to: {effort}")

    @property
    def provider_name(self) -> str:
        """プロバイダー名を返す"""
        return "anthropic"

    @property
    def default_model(self) -> str:
        """デフォルトモデルIDを返す"""
        return DEFAULT_MODEL

    @property
    def available_models(self) -> list[str]:
        """利用可能なモデル一覧を返す"""
        return SUPPORTED_MODELS

    @property
    def model(self) -> str:
        """現在のモデルを返す"""
        return self._model

    async def close(self) -> None:
        """Close underlying client resources if available."""
        await _maybe_close_client(self.client)
        if hasattr(self, "_http_client") and self._http_client:
            await self._http_client.aclose()

    async def health_check(self) -> bool:
        """ヘルスチェック"""
        try:
            await self.client.messages.create(
                model=self._model,
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}],
            )
            return True
        except Exception:
            return False

    async def generate(
        self,
        messages: list[dict[str, str]] | list[LLMMessage],
        system_prompt: str,
        config: LLMRequestConfig | None = None,
        metadata: LLMCallMetadata | None = None,
    ) -> LLMResponse:
        """Generate text response from Claude.

        Args:
            messages: List of message dicts with 'role' and 'content' keys.
                     Supported roles: 'user', 'assistant'
            system_prompt: System-level instructions for the model
            config: リクエスト設定
            metadata: 追跡用メタデータ

        Returns:
            LLMResponse with content, token_usage, and model info

        Raises:
            RetryableLLMError: For temporary failures
            NonRetryableLLMError: For permanent failures
        """
        config = config or LLMRequestConfig()
        normalized_messages = self._normalize_messages(messages)

        self._log_request("generate", self.model, metadata)

        retry_config = self._get_retry_config()
        attempt = 0

        while attempt < retry_config.max_attempts:
            attempt += 1
            try:
                logger.info(
                    "Anthropic API call attempt %d/%d, model=%s, temp=%s, max=%d",
                    attempt,
                    retry_config.max_attempts,
                    self.model,
                    config.temperature,
                    config.max_tokens,
                )

                # Convert messages to Anthropic format
                anthropic_messages = self._convert_messages(normalized_messages)

                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=config.max_tokens,
                    system=system_prompt,
                    messages=anthropic_messages,
                    temperature=config.temperature,
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

                # stop_reason検証とログ出力
                stop_reason = response.stop_reason
                self._validate_stop_reason(
                    stop_reason,
                    token_usage.output,
                    config.max_tokens,
                )

                logger.info(f"Anthropic API call succeeded, input_tokens={token_usage.input}, output_tokens={token_usage.output}")

                return LLMResponse(
                    content=content,
                    token_usage=token_usage,
                    model=response.model,
                    provider="anthropic",
                    finish_reason=stop_reason,
                )

            except AuthenticationError as e:
                # Auth errors are non-retryable
                logger.error(f"Authentication error: {e}")
                raise NonRetryableLLMError(f"Authentication failed: {e}")

            except RateLimitError as e:
                # Rate limit is retryable with exponential backoff
                logger.warning(f"Rate limit error (attempt {attempt}/{retry_config.max_attempts}): {e}")
                if attempt >= retry_config.max_attempts:
                    raise RetryableLLMError(f"Rate limit exceeded after {retry_config.max_attempts} attempts: {e}")
                # Exponential backoff before next attempt
                delay = min(
                    retry_config.base_delay * (retry_config.exponential_base ** (attempt - 1)),
                    retry_config.max_delay,
                )
                logger.info(f"Retrying in {delay:.1f}s after rate limit")
                await asyncio.sleep(delay)

            except APIConnectionError as e:
                # Connection errors are retryable with exponential backoff
                logger.warning(f"Connection error (attempt {attempt}/{retry_config.max_attempts}): {e}")
                if attempt >= retry_config.max_attempts:
                    raise RetryableLLMError(f"Connection failed after {retry_config.max_attempts} attempts: {e}")
                # Exponential backoff before next attempt
                delay = min(
                    retry_config.base_delay * (retry_config.exponential_base ** (attempt - 1)),
                    retry_config.max_delay,
                )
                logger.info(f"Retrying in {delay:.1f}s after connection error")
                await asyncio.sleep(delay)

            except APIStatusError as e:
                # Check if the error is retryable based on status code
                if e.status_code >= 500:
                    logger.warning(f"Server error (attempt {attempt}/{retry_config.max_attempts}): {e}")
                    if attempt >= retry_config.max_attempts:
                        raise RetryableLLMError(f"Server error after {retry_config.max_attempts} attempts: {e}")
                    # Exponential backoff before next attempt
                    delay = min(
                        retry_config.base_delay * (retry_config.exponential_base ** (attempt - 1)),
                        retry_config.max_delay,
                    )
                    logger.info(f"Retrying in {delay:.1f}s after server error")
                    await asyncio.sleep(delay)
                else:
                    # Client errors (4xx except rate limit) are non-retryable
                    logger.error(f"API error: {e}")
                    raise NonRetryableLLMError(f"API error: {e}")

            except TimeoutError as e:
                # Timeout errors are retryable
                logger.warning(f"Timeout error (attempt {attempt}/{retry_config.max_attempts}): {e}")
                if attempt >= retry_config.max_attempts:
                    raise RetryableLLMError(f"Timeout after {retry_config.max_attempts} attempts: {e}")
                delay = min(
                    retry_config.base_delay * (retry_config.exponential_base ** (attempt - 1)),
                    retry_config.max_delay,
                )
                logger.info(f"Retrying in {delay:.1f}s after timeout")
                await asyncio.sleep(delay)

            except OSError as e:
                # Network-level errors (connection refused, etc.) are retryable
                logger.warning(f"OS/Network error (attempt {attempt}/{retry_config.max_attempts}): {e}")
                if attempt >= retry_config.max_attempts:
                    raise RetryableLLMError(f"Network error after {retry_config.max_attempts} attempts: {e}")
                delay = min(
                    retry_config.base_delay * (retry_config.exponential_base ** (attempt - 1)),
                    retry_config.max_delay,
                )
                logger.info(f"Retrying in {delay:.1f}s after network error")
                await asyncio.sleep(delay)

            except Exception as e:
                # Unknown errors are treated as non-retryable
                logger.error(f"Unexpected error: {e}", exc_info=True)
                raise NonRetryableLLMError(f"Unexpected error: {e}")

        # Should not reach here, but handle edge case
        raise RetryableLLMError(f"Failed after {retry_config.max_attempts} attempts")

    async def generate_json(
        self,
        messages: list[dict[str, str]] | list[LLMMessage],
        system_prompt: str,
        schema: dict[str, Any],
        config: LLMRequestConfig | None = None,
        metadata: LLMCallMetadata | None = None,
    ) -> dict[str, Any]:
        """Generate JSON output from Claude with schema validation.

        Uses tool_use feature to ensure structured JSON output.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            system_prompt: System-level instructions for the model
            schema: JSON Schema for output validation
            config: リクエスト設定
            metadata: 追跡用メタデータ

        Returns:
            Parsed and validated JSON dict

        Raises:
            RetryableLLMError: For temporary failures
            NonRetryableLLMError: For permanent failures
            ValidationLLMError: For JSON parsing/validation failures
        """
        config = config or LLMRequestConfig()
        normalized_messages = self._normalize_messages(messages)

        retry_config = self._get_retry_config()
        attempt = 0

        # Create a tool definition from the schema
        tool_name = "json_output"
        tools: list[ToolParam] = [
            {
                "name": tool_name,
                "description": "Output the result as structured JSON",
                "input_schema": schema,
            }
        ]

        while attempt < retry_config.max_attempts:
            attempt += 1
            try:
                logger.info(f"Anthropic API JSON call attempt {attempt}/{retry_config.max_attempts}, model={self.model}")

                # Convert messages to Anthropic format
                anthropic_messages = self._convert_messages(normalized_messages)

                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=config.max_tokens,
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
                raise NonRetryableLLMError(f"Authentication failed: {e}")

            except RateLimitError as e:
                logger.warning(f"Rate limit error (attempt {attempt}/{retry_config.max_attempts}): {e}")
                if attempt >= retry_config.max_attempts:
                    raise RetryableLLMError(f"Rate limit exceeded after {retry_config.max_attempts} attempts: {e}")
                # Exponential backoff before next attempt
                delay = min(
                    retry_config.base_delay * (retry_config.exponential_base ** (attempt - 1)),
                    retry_config.max_delay,
                )
                logger.info(f"Retrying in {delay:.1f}s after rate limit")
                await asyncio.sleep(delay)

            except APIConnectionError as e:
                logger.warning(f"Connection error (attempt {attempt}/{retry_config.max_attempts}): {e}")
                if attempt >= retry_config.max_attempts:
                    raise RetryableLLMError(f"Connection failed after {retry_config.max_attempts} attempts: {e}")
                # Exponential backoff before next attempt
                delay = min(
                    retry_config.base_delay * (retry_config.exponential_base ** (attempt - 1)),
                    retry_config.max_delay,
                )
                logger.info(f"Retrying in {delay:.1f}s after connection error")
                await asyncio.sleep(delay)

            except APIStatusError as e:
                if e.status_code >= 500:
                    logger.warning(f"Server error (attempt {attempt}/{retry_config.max_attempts}): {e}")
                    if attempt >= retry_config.max_attempts:
                        raise RetryableLLMError(f"Server error after {retry_config.max_attempts} attempts: {e}")
                    # Exponential backoff before next attempt
                    delay = min(
                        retry_config.base_delay * (retry_config.exponential_base ** (attempt - 1)),
                        retry_config.max_delay,
                    )
                    logger.info(f"Retrying in {delay:.1f}s after server error")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"API error: {e}")
                    raise NonRetryableLLMError(f"API error: {e}")

            except ValidationLLMError:
                # Re-raise validation errors without retry
                raise

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                raise ValidationLLMError(f"Failed to parse JSON response: {e}")

            except TimeoutError as e:
                # Timeout errors are retryable
                logger.warning(f"Timeout error (attempt {attempt}/{retry_config.max_attempts}): {e}")
                if attempt >= retry_config.max_attempts:
                    raise RetryableLLMError(f"Timeout after {retry_config.max_attempts} attempts: {e}")
                delay = min(
                    retry_config.base_delay * (retry_config.exponential_base ** (attempt - 1)),
                    retry_config.max_delay,
                )
                logger.info(f"Retrying in {delay:.1f}s after timeout")
                await asyncio.sleep(delay)

            except OSError as e:
                # Network-level errors (connection refused, etc.) are retryable
                logger.warning(f"OS/Network error (attempt {attempt}/{retry_config.max_attempts}): {e}")
                if attempt >= retry_config.max_attempts:
                    raise RetryableLLMError(f"Network error after {retry_config.max_attempts} attempts: {e}")
                delay = min(
                    retry_config.base_delay * (retry_config.exponential_base ** (attempt - 1)),
                    retry_config.max_delay,
                )
                logger.info(f"Retrying in {delay:.1f}s after network error")
                await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                raise NonRetryableLLMError(f"Unexpected error: {e}")

        raise RetryableLLMError(f"Failed after {retry_config.max_attempts} attempts")

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

    def _validate_stop_reason(
        self,
        stop_reason: str | None,
        output_tokens: int,
        max_tokens: int,
    ) -> None:
        """stop_reasonと出力トークン比率を検証してログ出力

        Args:
            stop_reason: APIから返されたstop_reason
            output_tokens: 実際の出力トークン数
            max_tokens: リクエスト時のmax_tokens設定
        """
        # stop_reasonの検証
        # Anthropic stop_reason: end_turn, max_tokens, stop_sequence, tool_use
        if stop_reason:
            if stop_reason == "max_tokens":
                logger.warning(
                    "Output was truncated due to max_tokens limit",
                    extra={
                        "provider": "anthropic",
                        "model": self._model,
                        "stop_reason": stop_reason,
                        "output_tokens": output_tokens,
                        "max_tokens": max_tokens,
                    },
                )

        # 出力トークン比率チェック
        # max_tokensで切れた場合（stop_reason=="max_tokens"）や
        # tool_use（JSON出力）の場合は警告をスキップ
        # max_tokensが小さい場合（1000未満）もスキップ（短い応答が期待されている）
        if (
            max_tokens
            and max_tokens >= 1000  # 短い応答が期待される場合はスキップ
            and output_tokens > 0
            and stop_reason in ("end_turn", None)  # 正常終了時のみチェック
        ):
            ratio = output_tokens / max_tokens
            # 5%未満は警告（期待より大幅に少ない出力、閾値を10%→5%に下げて誤警告を減らす）
            if ratio < 0.05:
                logger.warning(
                    f"Output token ratio is very low: {ratio:.1%} ({output_tokens}/{max_tokens})",
                    extra={
                        "provider": "anthropic",
                        "model": self._model,
                        "output_tokens": output_tokens,
                        "max_tokens": max_tokens,
                        "ratio": ratio,
                        "stop_reason": stop_reason,
                    },
                )
