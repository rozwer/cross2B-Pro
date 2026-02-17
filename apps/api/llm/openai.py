"""OpenAI API クライアント実装.

フォールバック禁止: 別モデル/別プロバイダへの自動切替は行わない。
同一条件でのリトライのみ許容（上限3回、ログ必須）。
"""

import asyncio
import json
import logging
import os
from typing import Any

import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
)

from .base import LLMInterface, _maybe_close_client
from .exceptions import ErrorCategory, LLMError, LLMValidationError
from .schemas import (
    LLMCallMetadata,
    LLMMessage,
    LLMRequestConfig,
    LLMResponse,
    OpenAIConfig,
    TokenUsage,
)

logger = logging.getLogger(__name__)


class OpenAIClient(LLMInterface):
    """OpenAI API クライアント.

    対応モデル: gpt-5.2, gpt-5.1, gpt-5 等
    """

    PROVIDER = "openai"
    DEFAULT_MODEL = "gpt-5.2"
    MAX_RETRIES = 3

    AVAILABLE_MODELS = [
        "gpt-5.2",  # 最新: Thinking + Instant + Pro
        "gpt-5.2-pro",  # 最高精度
        "gpt-5.2-codex",  # Codex最新（コーディング特化）
        "gpt-5.2-chat-latest",  # Instant版
        "gpt-5.1",  # 前バージョン
        "gpt-5.1-codex",  # Codex（コーディング特化）
        "gpt-5.1-codex-mini",  # Codex軽量版
        "gpt-5.1-chat-latest",  # Instant版
        "gpt-5-codex",  # GPT-5 Codex
        "gpt-5",  # 初代GPT-5
    ]

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_retries: int | None = None,
        openai_config: OpenAIConfig | None = None,
    ) -> None:
        """初期化.

        Args:
            api_key: OpenAI APIキー（省略時は環境変数から取得）
            model: 使用するモデル名
            max_retries: 最大リトライ回数
            openai_config: OpenAI固有の設定
        """
        resolved_api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_api_key:
            raise LLMError(
                message="OPENAI_API_KEY is not set",
                category=ErrorCategory.NON_RETRYABLE,
                provider=self.PROVIDER,
            )

        # Configure httpx client with connection pool limits
        # max_connections: total connection pool size
        # max_keepalive_connections: connections kept alive for reuse
        http_client = httpx.AsyncClient(
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
            ),
            timeout=httpx.Timeout(timeout=120.0, connect=10.0),
        )
        self.client = AsyncOpenAI(api_key=resolved_api_key, http_client=http_client)
        self._http_client = http_client
        self.model = model or self.DEFAULT_MODEL
        self.max_retries = max_retries or self.MAX_RETRIES
        self._openai_config = openai_config or OpenAIConfig()

        # 警告のみ（DBで管理されているモデルリストを優先）
        if self.model not in self.AVAILABLE_MODELS:
            logger.warning(f"Model '{self.model}' is not in known models list. Available: {self.AVAILABLE_MODELS}")

    def configure_reasoning(self, effort: str | None = None) -> None:
        """Reasoning effortを設定（GPT-5系向け）

        Args:
            effort: none, low, medium, high, xhigh
        """
        self._openai_config.reasoning.effort = effort
        logger.info(f"Reasoning effort set to: {effort}")

    def enable_web_search(self, enabled: bool = True) -> None:
        """Web Searchを有効/無効化

        Args:
            enabled: Web Searchを有効にするかどうか
        """
        self._openai_config.web_search.enabled = enabled
        logger.info(f"Web search {'enabled' if enabled else 'disabled'}")

    def set_verbosity(self, verbosity: str | None = None) -> None:
        """出力の詳細度を設定

        Args:
            verbosity: concise or detailed
        """
        self._openai_config.verbosity = verbosity
        logger.info(f"Verbosity set to: {verbosity}")

    @property
    def provider_name(self) -> str:
        """プロバイダー名を返す"""
        return self.PROVIDER

    @property
    def default_model(self) -> str:
        """デフォルトモデルIDを返す"""
        return self.DEFAULT_MODEL

    @property
    def available_models(self) -> list[str]:
        """利用可能なモデル一覧を返す"""
        return self.AVAILABLE_MODELS.copy()

    async def close(self) -> None:
        """Close underlying client resources if available."""
        await _maybe_close_client(self.client)
        if hasattr(self, "_http_client") and self._http_client:
            await self._http_client.aclose()

    async def health_check(self) -> bool:
        """ヘルスチェック"""
        try:
            await self.client.models.list()
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
        """テキスト生成を実行する.

        Args:
            messages: 会話履歴（role/content形式）
            system_prompt: システムプロンプト
            config: リクエスト設定
            metadata: 追跡用メタデータ

        Returns:
            LLMResponse: 生成結果とメタデータ

        Raises:
            LLMError: API呼び出しエラー時
        """
        config = config or LLMRequestConfig()
        normalized_messages = self._normalize_messages(messages)
        full_messages = [{"role": "system", "content": system_prompt}, *normalized_messages]

        self._log_request("generate", self.model, metadata)
        retry_config = self._get_retry_config()

        for attempt in range(1, retry_config.max_attempts + 1):
            try:
                logger.info(
                    "OpenAI API call: model=%s, attempt=%d/%d",
                    self.model,
                    attempt,
                    retry_config.max_attempts,
                )

                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=full_messages,  # type: ignore[arg-type]
                    temperature=config.temperature,
                    max_completion_tokens=config.max_tokens,  # GPT-5系はmax_completion_tokens
                )

                choice = response.choices[0]
                usage = response.usage

                token_usage = TokenUsage(
                    input=usage.prompt_tokens if usage else 0,
                    output=usage.completion_tokens if usage else 0,
                )

                logger.info(
                    "OpenAI API success: model=%s, tokens=%d",
                    self.model,
                    token_usage.total,
                )

                return LLMResponse(
                    content=choice.message.content or "",
                    token_usage=token_usage,
                    model=response.model,
                    finish_reason=choice.finish_reason,
                    provider=self.PROVIDER,
                )

            except (RateLimitError, APIConnectionError) as e:
                logger.warning(
                    "OpenAI API retryable error: model=%s, attempt=%d/%d, error=%s",
                    self.model,
                    attempt,
                    retry_config.max_attempts,
                    str(e),
                )
                if attempt == retry_config.max_attempts:
                    raise LLMError(
                        message=f"OpenAI API failed after {retry_config.max_attempts} attempts: {e}",
                        category=ErrorCategory.RETRYABLE,
                        provider=self.PROVIDER,
                        model=self.model,
                    ) from e
                # Exponential backoff before next attempt
                delay = min(
                    retry_config.base_delay * (retry_config.exponential_base ** (attempt - 1)),
                    retry_config.max_delay,
                )
                logger.info(f"Retrying in {delay:.1f}s after error")
                await asyncio.sleep(delay)
                continue

            except AuthenticationError as e:
                logger.error("OpenAI API authentication error: %s", str(e))
                raise LLMError(
                    message=f"OpenAI API authentication failed: {e}",
                    category=ErrorCategory.NON_RETRYABLE,
                    provider=self.PROVIDER,
                    model=self.model,
                ) from e

            except BadRequestError as e:
                logger.error("OpenAI API bad request: %s", str(e))
                raise LLMError(
                    message=f"OpenAI API bad request: {e}",
                    category=ErrorCategory.NON_RETRYABLE,
                    provider=self.PROVIDER,
                    model=self.model,
                ) from e

            except APIStatusError as e:
                if e.status_code >= 500:
                    logger.warning(
                        "OpenAI API server error: model=%s, attempt=%d/%d, status=%d",
                        self.model,
                        attempt,
                        retry_config.max_attempts,
                        e.status_code,
                    )
                    if attempt == retry_config.max_attempts:
                        msg = f"OpenAI server error after {retry_config.max_attempts} tries: {e}"
                        raise LLMError(
                            message=msg,
                            category=ErrorCategory.RETRYABLE,
                            provider=self.PROVIDER,
                            model=self.model,
                        ) from e
                    # Exponential backoff before next attempt
                    delay = min(
                        retry_config.base_delay * (retry_config.exponential_base ** (attempt - 1)),
                        retry_config.max_delay,
                    )
                    logger.info(f"Retrying in {delay:.1f}s after server error")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("OpenAI API error: status=%d, %s", e.status_code, str(e))
                    raise LLMError(
                        message=f"OpenAI API error: {e}",
                        category=ErrorCategory.NON_RETRYABLE,
                        provider=self.PROVIDER,
                        model=self.model,
                    ) from e

        raise LLMError(
            message=f"OpenAI API failed after {retry_config.max_attempts} attempts",
            category=ErrorCategory.RETRYABLE,
            provider=self.PROVIDER,
            model=self.model,
        )

    async def generate_json(
        self,
        messages: list[dict[str, str]] | list[LLMMessage],
        system_prompt: str,
        schema: dict[str, Any],
        config: LLMRequestConfig | None = None,
        metadata: LLMCallMetadata | None = None,
    ) -> dict[str, Any]:
        """JSON形式での出力を保証する生成を実行する.

        response_format={"type": "json_object"} を使用して
        JSON出力を保証する。

        Args:
            messages: 会話履歴
            system_prompt: システムプロンプト
            schema: 期待するJSONスキーマ（検証用）
            config: リクエスト設定
            metadata: 追跡用メタデータ

        Returns:
            dict: パース済みJSONオブジェクト

        Raises:
            LLMError: API呼び出しエラー時
            LLMValidationError: JSON検証エラー時
        """
        enhanced_system_prompt = (
            f"{system_prompt}\n\n"
            f"You must respond with valid JSON that conforms to this schema:\n"
            f"```json\n{json.dumps(schema, indent=2)}\n```"
        )

        normalized_messages = self._normalize_messages(messages)
        full_messages = [
            {"role": "system", "content": enhanced_system_prompt},
            *normalized_messages,
        ]
        retry_config = self._get_retry_config()

        for attempt in range(1, retry_config.max_attempts + 1):
            try:
                logger.info(
                    "OpenAI API JSON call: model=%s, attempt=%d/%d",
                    self.model,
                    attempt,
                    retry_config.max_attempts,
                )

                response = await self.client.chat.completions.create(  # type: ignore[call-overload]
                    model=self.model,
                    messages=full_messages,
                    response_format={"type": "json_object"},
                )

                choice = response.choices[0]
                content = choice.message.content or "{}"

                try:
                    parsed = json.loads(content)
                except json.JSONDecodeError as e:
                    # Log truncated content for readability, but preserve full content in error
                    truncated_for_log = content[:500]
                    if len(content) > 500:
                        truncated_for_log += f"... (total {len(content)} chars)"
                    logger.error(
                        "OpenAI API JSON parse error: model=%s, attempt=%d/%d, error=%s, content=%s",
                        self.model,
                        attempt,
                        retry_config.max_attempts,
                        str(e),
                        truncated_for_log,
                    )
                    raise LLMValidationError(
                        message=f"Failed to parse JSON response: {e}",
                        provider=self.PROVIDER,
                        model=self.model,
                        # Preserve full content for debugging/artifact storage
                        validation_errors=[content],
                        raw_output=content,
                    ) from e

                logger.info(
                    "OpenAI API JSON success: model=%s, tokens=%d",
                    self.model,
                    (response.usage.total_tokens if response.usage else 0),
                )

                return dict(parsed)

            except (RateLimitError, APIConnectionError) as e:
                logger.warning(
                    "OpenAI API JSON retryable error: model=%s, attempt=%d/%d, error=%s",
                    self.model,
                    attempt,
                    retry_config.max_attempts,
                    str(e),
                )
                if attempt == retry_config.max_attempts:
                    raise LLMError(
                        message=f"OpenAI API JSON failed after {retry_config.max_attempts} attempts: {e}",
                        category=ErrorCategory.RETRYABLE,
                        provider=self.PROVIDER,
                        model=self.model,
                    ) from e
                # Exponential backoff before next attempt
                delay = min(
                    retry_config.base_delay * (retry_config.exponential_base ** (attempt - 1)),
                    retry_config.max_delay,
                )
                logger.info(f"Retrying in {delay:.1f}s after error")
                await asyncio.sleep(delay)
                continue

            except AuthenticationError as e:
                logger.error("OpenAI API authentication error: %s", str(e))
                raise LLMError(
                    message=f"OpenAI API authentication failed: {e}",
                    category=ErrorCategory.NON_RETRYABLE,
                    provider=self.PROVIDER,
                    model=self.model,
                ) from e

            except BadRequestError as e:
                logger.error("OpenAI API bad request: %s", str(e))
                raise LLMError(
                    message=f"OpenAI API bad request: {e}",
                    category=ErrorCategory.NON_RETRYABLE,
                    provider=self.PROVIDER,
                    model=self.model,
                ) from e

            except APIStatusError as e:
                if e.status_code >= 500:
                    logger.warning(
                        "OpenAI API JSON server error: model=%s, attempt=%d/%d, status=%d",
                        self.model,
                        attempt,
                        retry_config.max_attempts,
                        e.status_code,
                    )
                    if attempt == retry_config.max_attempts:
                        msg = f"OpenAI server error after {retry_config.max_attempts} tries: {e}"
                        raise LLMError(
                            message=msg,
                            category=ErrorCategory.RETRYABLE,
                            provider=self.PROVIDER,
                            model=self.model,
                        ) from e
                    # Exponential backoff before next attempt
                    delay = min(
                        retry_config.base_delay * (retry_config.exponential_base ** (attempt - 1)),
                        retry_config.max_delay,
                    )
                    logger.info(f"Retrying in {delay:.1f}s after server error")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("OpenAI API error: status=%d, %s", e.status_code, str(e))
                    raise LLMError(
                        message=f"OpenAI API error: {e}",
                        category=ErrorCategory.NON_RETRYABLE,
                        provider=self.PROVIDER,
                        model=self.model,
                    ) from e

            except LLMValidationError:
                raise

        raise LLMError(
            message=f"OpenAI API JSON failed after {retry_config.max_attempts} attempts",
            category=ErrorCategory.RETRYABLE,
            provider=self.PROVIDER,
            model=self.model,
        )
