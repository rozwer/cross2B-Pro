"""
ツール関連のスキーマ定義

Evidence型: 取得結果の証拠（追跡可能性確保）
ToolResult型: ツール実行結果
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _utc_now() -> datetime:
    """UTC現在時刻を返す"""
    return datetime.now(UTC)


class Evidence(BaseModel):
    """
    取得結果の証拠

    全ての外部データ取得には証拠を付与し、追跡可能性を確保する。
    """

    model_config = ConfigDict(frozen=True)

    url: str = Field(..., description="取得元URL")
    fetched_at: datetime = Field(default_factory=_utc_now, description="取得日時(UTC)")
    excerpt: str = Field(..., description="抜粋（内容の一部）")
    content_hash: str = Field(..., description="コンテンツのSHA256ハッシュ")


class ToolResult(BaseModel):
    """
    ツール実行結果

    全ツールはこの型で結果を返却する。
    """

    success: bool = Field(..., description="実行成功フラグ")
    data: Any | None = Field(default=None, description="実行結果データ")
    error_category: str | None = Field(
        default=None, description="エラー分類（失敗時のみ）"
    )
    error_message: str | None = Field(
        default=None, description="エラーメッセージ（失敗時のみ）"
    )
    evidence: list[Evidence] | None = Field(
        default=None, description="取得結果の証拠リスト"
    )
    is_mock: bool = Field(default=False, description="モックデータかどうか")

    def is_retryable(self) -> bool:
        """リトライ可能なエラーかどうか"""
        return self.error_category == "retryable"

    def is_validation_error(self) -> bool:
        """検証エラーかどうか"""
        return self.error_category == "validation_fail"


class ToolRequest(BaseModel):
    """
    ツール実行リクエスト

    ツールを呼び出す際のパラメータを保持する。
    """

    tool_name: str = Field(..., description="ツール名")
    params: dict[str, Any] = Field(default_factory=dict, description="ツールパラメータ")
