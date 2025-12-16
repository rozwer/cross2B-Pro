"""
ツール関連の例外定義

統一されたエラーハンドリングのため、ツール固有の例外を定義する。
"""

from .base import ErrorCategory


class ToolError(Exception):
    """ツール関連エラーの基底クラス"""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.NON_RETRYABLE,
        tool_id: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.tool_id = tool_id

    def __repr__(self) -> str:
        cls_name = self.__class__.__name__
        return f"<{cls_name}(tool_id={self.tool_id}, cat={self.category}, msg={self.message})>"


class RetryableError(ToolError):
    """リトライ可能なエラー（ネットワーク一時障害等）"""

    def __init__(self, message: str, tool_id: str | None = None):
        super().__init__(message, ErrorCategory.RETRYABLE, tool_id)


class NonRetryableError(ToolError):
    """リトライ不可なエラー（認証エラー、リソース不存在等）"""

    def __init__(self, message: str, tool_id: str | None = None):
        super().__init__(message, ErrorCategory.NON_RETRYABLE, tool_id)


class ValidationError(ToolError):
    """検証失敗エラー（入力不正、出力形式異常等）"""

    def __init__(self, message: str, tool_id: str | None = None):
        super().__init__(message, ErrorCategory.VALIDATION_FAIL, tool_id)


class ToolNotFoundError(NonRetryableError):
    """ツールが見つからないエラー"""

    def __init__(self, tool_id: str):
        super().__init__(f"Unknown tool: {tool_id}", tool_id)


class RateLimitError(RetryableError):
    """レート制限エラー（リトライ可能）"""

    def __init__(self, message: str, tool_id: str | None = None, retry_after: int | None = None):
        super().__init__(message, tool_id)
        self.retry_after = retry_after


class TimeoutError(RetryableError):
    """タイムアウトエラー（リトライ可能）"""

    def __init__(self, message: str, tool_id: str | None = None):
        super().__init__(message, tool_id)


class ContentExtractionError(ValidationError):
    """コンテンツ抽出失敗エラー"""

    def __init__(self, message: str, tool_id: str | None = None, url: str | None = None):
        super().__init__(message, tool_id)
        self.url = url
