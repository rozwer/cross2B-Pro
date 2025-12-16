"""LLM関連の例外定義."""

from .schemas import ErrorCategory


class LLMError(Exception):
    """LLM API呼び出しエラーの基底クラス."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        provider: str,
        model: str | None = None,
        original_error: Exception | None = None,
        attempt: int = 1,
    ) -> None:
        """初期化.

        Args:
            message: エラーメッセージ
            category: エラー分類（RETRYABLE/NON_RETRYABLE/VALIDATION_FAIL）
            provider: プロバイダー名（openai, gemini, anthropic）
            model: 使用したモデル名
            original_error: 元の例外
            attempt: 試行回数
        """
        super().__init__(message)
        self.message = message
        self.category = category
        self.provider = provider
        self.model = model
        self.original_error = original_error
        self.attempt = attempt

    def is_retryable(self) -> bool:
        """リトライ可能かどうか."""
        return self.category == ErrorCategory.RETRYABLE

    def __repr__(self) -> str:
        return (
            f"LLMError(message={self.message!r}, category={self.category.value}, "
            f"provider={self.provider!r}, model={self.model!r}, attempt={self.attempt})"
        )


class LLMValidationError(LLMError):
    """LLM出力の検証エラー."""

    def __init__(
        self,
        message: str,
        provider: str,
        model: str | None = None,
        original_error: Exception | None = None,
        attempt: int = 1,
        validation_details: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION_FAIL,
            provider=provider,
            model=model,
            original_error=original_error,
            attempt=attempt,
        )
        self.validation_details = validation_details or {}
