"""LLM関連の例外定義

エラー分類:
- RETRYABLE: タイムアウト、レート制限等（リトライ可能）
- NON_RETRYABLE: 認証エラー、無効なリクエスト等（リトライ不可）
- VALIDATION_FAIL: スキーマ違反、JSON parse失敗等
"""

from enum import Enum
from typing import Any


class ErrorCategory(str, Enum):
    """エラー分類"""

    RETRYABLE = "retryable"
    NON_RETRYABLE = "non_retryable"
    VALIDATION_FAIL = "validation_fail"


class LLMError(Exception):
    """LLM関連エラーの基底クラス"""

    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        provider: str | None = None,
        model: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.category = category
        self.provider = provider
        self.model = model
        self.details = details or {}

    def is_retryable(self) -> bool:
        """リトライ可能かどうか"""
        return self.category == ErrorCategory.RETRYABLE

    def to_dict(self) -> dict[str, Any]:
        """エラー情報を辞書形式で返す"""
        return {
            "message": self.message,
            "category": self.category.value,
            "provider": self.provider,
            "model": self.model,
            "details": self.details,
        }


class LLMTimeoutError(LLMError):
    """タイムアウトエラー（リトライ可能）"""

    def __init__(
        self,
        message: str = "LLM request timed out",
        provider: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        super().__init__(
            message=message,
            category=ErrorCategory.RETRYABLE,
            provider=provider,
            model=model,
            details={"timeout_seconds": timeout_seconds} if timeout_seconds else {},
        )


class LLMRateLimitError(LLMError):
    """レート制限エラー（リトライ可能）"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        provider: str | None = None,
        model: str | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(
            message=message,
            category=ErrorCategory.RETRYABLE,
            provider=provider,
            model=model,
            details={"retry_after": retry_after} if retry_after else {},
        )


class LLMAuthenticationError(LLMError):
    """認証エラー（リトライ不可）"""

    def __init__(
        self,
        message: str = "Authentication failed",
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            category=ErrorCategory.NON_RETRYABLE,
            provider=provider,
            model=model,
        )


class LLMInvalidRequestError(LLMError):
    """無効なリクエストエラー（リトライ不可）"""

    def __init__(
        self,
        message: str = "Invalid request",
        provider: str | None = None,
        model: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            category=ErrorCategory.NON_RETRYABLE,
            provider=provider,
            model=model,
            details=details,
        )


class LLMContentFilterError(LLMError):
    """コンテンツフィルターエラー（リトライ不可）"""

    def __init__(
        self,
        message: str = "Content blocked by safety filter",
        provider: str | None = None,
        model: str | None = None,
        blocked_reason: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            category=ErrorCategory.NON_RETRYABLE,
            provider=provider,
            model=model,
            details={"blocked_reason": blocked_reason} if blocked_reason else {},
        )


class LLMValidationError(LLMError):
    """出力検証エラー（修正可能な場合あり）"""

    def __init__(
        self,
        message: str = "Output validation failed",
        provider: str | None = None,
        model: str | None = None,
        validation_errors: list[str] | None = None,
        raw_output: str | None = None,
    ) -> None:
        details: dict[str, list[str] | str] = {"validation_errors": validation_errors or []}
        if raw_output is not None:
            details["raw_output"] = raw_output
        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION_FAIL,
            provider=provider,
            model=model,
            details=details,
        )


class LLMJSONParseError(LLMError):
    """JSON parse エラー（修正可能な場合あり）"""

    def __init__(
        self,
        message: str = "Failed to parse JSON output",
        provider: str | None = None,
        model: str | None = None,
        raw_output: str | None = None,
        parse_error: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION_FAIL,
            provider=provider,
            model=model,
            details={
                "raw_output_length": len(raw_output) if raw_output else 0,
                "parse_error": parse_error,
            },
        )


class LLMServiceUnavailableError(LLMError):
    """サービス利用不可エラー（リトライ可能）"""

    def __init__(
        self,
        message: str = "LLM service is temporarily unavailable",
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            category=ErrorCategory.RETRYABLE,
            provider=provider,
            model=model,
        )


class LLMConfigurationError(LLMError):
    """設定エラー（リトライ不可）"""

    def __init__(
        self,
        message: str = "LLM configuration error",
        provider: str | None = None,
        model: str | None = None,
        missing_config: list[str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            category=ErrorCategory.NON_RETRYABLE,
            provider=provider,
            model=model,
            details={"missing_config": missing_config or []},
        )


# Anthropicクライアント互換用エイリアス
RetryableLLMError = LLMRateLimitError
NonRetryableLLMError = LLMAuthenticationError
ValidationLLMError = LLMValidationError
