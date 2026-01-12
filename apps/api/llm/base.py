"""LLM共通インターフェース

全プロバイダーが実装すべき抽象基底クラス。
フォールバック禁止：別モデル/別プロバイダへの自動切替は行わない。
"""

import inspect
import json
import logging
from abc import ABC, abstractmethod
from types import TracebackType
from typing import Any

from .schemas import (
    LLMCallMetadata,
    LLMMessage,
    LLMRequestConfig,
    LLMResponse,
    RetryConfig,
)

logger = logging.getLogger(__name__)


class LLMInterface(ABC):
    """LLM共通インターフェース

    全プロバイダー（Gemini, OpenAI, Anthropic等）が実装する抽象基底クラス。

    重要な設計原則:
    - フォールバック禁止: 別モデル/別プロバイダへの自動切替は行わない
    - 同一条件リトライ: 上限3回、ログ必須
    - エラー分類統一: RETRYABLE / NON_RETRYABLE / VALIDATION_FAIL
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """プロバイダー名を返す"""
        ...

    @property
    @abstractmethod
    def default_model(self) -> str:
        """デフォルトモデルIDを返す"""
        ...

    @property
    @abstractmethod
    def available_models(self) -> list[str]:
        """利用可能なモデル一覧を返す"""
        ...

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, str]] | list[LLMMessage],
        system_prompt: str,
        config: LLMRequestConfig | None = None,
        metadata: LLMCallMetadata | None = None,
    ) -> LLMResponse:
        """テキスト生成

        Args:
            messages: 会話履歴（role/contentの辞書リスト、またはLLMMessage）
            system_prompt: システムプロンプト
            config: リクエスト設定（temperature, max_tokens等）
            metadata: 追跡用メタデータ（run_id, step_id等）

        Returns:
            LLMResponse: 生成結果

        Raises:
            LLMTimeoutError: タイムアウト（RETRYABLE）
            LLMRateLimitError: レート制限（RETRYABLE）
            LLMAuthenticationError: 認証エラー（NON_RETRYABLE）
            LLMInvalidRequestError: 無効なリクエスト（NON_RETRYABLE）
            LLMContentFilterError: コンテンツフィルター（NON_RETRYABLE）
            LLMServiceUnavailableError: サービス利用不可（RETRYABLE）
        """
        ...

    @abstractmethod
    async def generate_json(
        self,
        messages: list[dict[str, str]] | list[LLMMessage],
        system_prompt: str,
        schema: dict[str, Any],
        config: LLMRequestConfig | None = None,
        metadata: LLMCallMetadata | None = None,
    ) -> dict[str, Any]:
        """JSON出力を保証するテキスト生成

        Args:
            messages: 会話履歴（role/contentの辞書リスト、またはLLMMessage）
            system_prompt: システムプロンプト
            schema: 期待するJSONスキーマ（JSON Schema形式）
            config: リクエスト設定
            metadata: 追跡用メタデータ

        Returns:
            dict: パース済みのJSON

        Raises:
            LLMJSONParseError: JSONパースエラー（VALIDATION_FAIL）
            LLMValidationError: スキーマ検証エラー（VALIDATION_FAIL）
            その他generate()と同様の例外
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """ヘルスチェック

        APIへの接続が正常かどうかを確認。

        Returns:
            bool: 正常な場合True
        """
        ...

    async def close(self) -> None:
        """Close underlying resources (optional for providers)."""
        return None

    def _normalize_messages(self, messages: list[dict[str, str]] | list[LLMMessage]) -> list[dict[str, str]]:
        """メッセージを正規化

        LLMMessageリストを辞書リストに変換。
        """
        normalized = []
        for msg in messages:
            if isinstance(msg, LLMMessage):
                normalized.append({"role": msg.role, "content": msg.content})
            else:
                normalized.append(msg)
        return normalized

    def _get_retry_config(self) -> RetryConfig:
        """デフォルトのリトライ設定を返す"""
        return RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=30.0,
            exponential_base=2.0,
        )

    def _log_request(
        self,
        method: str,
        model: str,
        metadata: LLMCallMetadata | None,
    ) -> None:
        """リクエストログ"""
        logger.info(
            "LLM request",
            extra={
                "provider": self.provider_name,
                "method": method,
                "model": model,
                "run_id": metadata.run_id if metadata else None,
                "step_id": metadata.step_id if metadata else None,
                "attempt": metadata.attempt if metadata else 1,
            },
        )

    def _log_response(
        self,
        method: str,
        response: LLMResponse,
        metadata: LLMCallMetadata | None,
    ) -> None:
        """レスポンスログ"""
        logger.info(
            "LLM response",
            extra={
                "provider": self.provider_name,
                "method": method,
                "model": response.model,
                "input_tokens": response.token_usage.input,
                "output_tokens": response.token_usage.output,
                "latency_ms": response.latency_ms,
                "run_id": metadata.run_id if metadata else None,
                "step_id": metadata.step_id if metadata else None,
            },
        )

    def _log_error(
        self,
        method: str,
        error: Exception,
        metadata: LLMCallMetadata | None,
    ) -> None:
        """エラーログ"""
        from .exceptions import LLMError

        error_info = {}
        if isinstance(error, LLMError):
            error_info = error.to_dict()

        logger.error(
            "LLM error",
            extra={
                "provider": self.provider_name,
                "method": method,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "error_info": error_info,
                "run_id": metadata.run_id if metadata else None,
                "step_id": metadata.step_id if metadata else None,
                "attempt": metadata.attempt if metadata else 1,
            },
        )

    async def __aenter__(self) -> "LLMInterface":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()


def _serialize_cache_kwargs(kwargs: dict[str, Any]) -> str:
    """Serialize kwargs for cache key generation."""
    if not kwargs:
        return ""
    try:
        return json.dumps(kwargs, sort_keys=True, default=repr, ensure_ascii=True)
    except (TypeError, ValueError):
        return repr(sorted(kwargs.items(), key=lambda item: item[0]))


async def _maybe_close_client(client: Any) -> None:
    """Attempt to close a client if it exposes a close/aclose method."""
    close_fn = getattr(client, "aclose", None) or getattr(client, "close", None)
    if callable(close_fn):
        result = close_fn()
        if inspect.isawaitable(result):
            await result


# エイリアス（後方互換性のため）
LLMClient = LLMInterface

_LLM_CLIENT_CACHE: dict[str, LLMInterface] = {}


def get_llm_client(provider: str, **kwargs: Any) -> LLMInterface:
    """プロバイダ名からLLMクライアントを取得

    Args:
        provider: プロバイダ名 ("gemini", "openai", "anthropic")
        **kwargs: クライアント初期化引数

    Returns:
        LLMInterface: 対応するクライアントインスタンス

    Raises:
        ValueError: 不明なプロバイダ
    """
    provider = provider.lower()
    cache_key = f"{provider}:{_serialize_cache_kwargs(kwargs)}"
    cached = _LLM_CLIENT_CACHE.get(cache_key)
    if cached is not None:
        return cached

    if provider == "gemini":
        from .gemini import GeminiClient

        client: LLMInterface = GeminiClient(**kwargs)
    elif provider == "openai":
        from .openai import OpenAIClient

        client = OpenAIClient(**kwargs)
    elif provider == "anthropic":
        from .anthropic import AnthropicClient

        client = AnthropicClient(**kwargs)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

    _LLM_CLIENT_CACHE[cache_key] = client
    return client
