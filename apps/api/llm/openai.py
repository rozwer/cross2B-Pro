"""OpenAI API クライアント実装.

フォールバック禁止: 別モデル/別プロバイダへの自動切替は行わない。
同一条件でのリトライのみ許容（上限3回、ログ必須）。
"""

import json
import logging
import os
from typing import Any

from openai import (
    APIConnectionError,
    APIStatusError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
)

from .base import LLMInterface
from .exceptions import ErrorCategory, LLMError, LLMValidationError
from .schemas import (
    LLMCallMetadata,
    LLMMessage,
    LLMRequestConfig,
    LLMResponse,
    TokenUsage,
)

logger = logging.getLogger(__name__)


class OpenAIClient(LLMInterface):
    """OpenAI API クライアント.

    対応モデル: gpt-4o, gpt-4-turbo, o3 等
    """

    PROVIDER = "openai"
    DEFAULT_MODEL = "gpt-4o"
    MAX_RETRIES = 3

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_retries: int | None = None,
    ) -> None:
        """初期化.

        Args:
            api_key: OpenAI APIキー（省略時は環境変数から取得）
            model: 使用するモデル名
            max_retries: 最大リトライ回数
        """
        resolved_api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not resolved_api_key:
            raise LLMError(
                message="OPENAI_API_KEY is not set",
                category=ErrorCategory.NON_RETRYABLE,
                provider=self.PROVIDER,
            )

        self.client = AsyncOpenAI(api_key=resolved_api_key)
        self.model = model or self.DEFAULT_MODEL
        self.max_retries = max_retries or self.MAX_RETRIES

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
        return ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo", "o3"]

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

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    "OpenAI API call: model=%s, attempt=%d/%d",
                    self.model,
                    attempt,
                    self.max_retries,
                )

                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=full_messages,  # type: ignore[arg-type]
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
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
                    self.max_retries,
                    str(e),
                )
                if attempt == self.max_retries:
                    raise LLMError(
                        message=f"OpenAI API failed after {self.max_retries} attempts: {e}",
                        category=ErrorCategory.RETRYABLE,
                        provider=self.PROVIDER,
                        model=self.model,
                    ) from e
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
                        self.max_retries,
                        e.status_code,
                    )
                    if attempt == self.max_retries:
                        msg = f"OpenAI server error after {self.max_retries} tries: {e}"
                        raise LLMError(
                            message=msg,
                            category=ErrorCategory.RETRYABLE,
                            provider=self.PROVIDER,
                            model=self.model,
                        ) from e
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
            message=f"OpenAI API failed after {self.max_retries} attempts",
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

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    "OpenAI API JSON call: model=%s, attempt=%d/%d",
                    self.model,
                    attempt,
                    self.max_retries,
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
                    logger.error(
                        "OpenAI API JSON parse error: model=%s, attempt=%d/%d, error=%s",
                        self.model,
                        attempt,
                        self.max_retries,
                        str(e),
                    )
                    raise LLMValidationError(
                        message=f"Failed to parse JSON response: {e}",
                        provider=self.PROVIDER,
                        model=self.model,
                        validation_errors=[content[:500]],
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
                    self.max_retries,
                    str(e),
                )
                if attempt == self.max_retries:
                    raise LLMError(
                        message=f"OpenAI API JSON failed after {self.max_retries} attempts: {e}",
                        category=ErrorCategory.RETRYABLE,
                        provider=self.PROVIDER,
                        model=self.model,
                    ) from e
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
                        self.max_retries,
                        e.status_code,
                    )
                    if attempt == self.max_retries:
                        msg = f"OpenAI server error after {self.max_retries} tries: {e}"
                        raise LLMError(
                            message=msg,
                            category=ErrorCategory.RETRYABLE,
                            provider=self.PROVIDER,
                            model=self.model,
                        ) from e
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
            message=f"OpenAI API JSON failed after {self.max_retries} attempts",
            category=ErrorCategory.RETRYABLE,
            provider=self.PROVIDER,
            model=self.model,
        )
