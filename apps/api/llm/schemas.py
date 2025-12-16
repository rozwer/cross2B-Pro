"""LLM関連の共通スキーマ定義."""

from enum import Enum

from pydantic import BaseModel, Field


class ErrorCategory(str, Enum):
    """エラー分類.

    - RETRYABLE: 一時的失敗（タイムアウト、レート制限等）→ 同一条件でリトライ可
    - NON_RETRYABLE: 永続的失敗（認証エラー、無効なリクエスト等）→ リトライ不可
    - VALIDATION_FAIL: 出力検証失敗 → 修正可能な場合のみリトライ
    """

    RETRYABLE = "RETRYABLE"
    NON_RETRYABLE = "NON_RETRYABLE"
    VALIDATION_FAIL = "VALIDATION_FAIL"


class TokenUsage(BaseModel):
    """トークン使用量."""

    input: int = Field(ge=0, description="入力トークン数")
    output: int = Field(ge=0, description="出力トークン数")

    @property
    def total(self) -> int:
        """合計トークン数."""
        return self.input + self.output


class LLMResponse(BaseModel):
    """LLM生成結果."""

    content: str = Field(description="生成されたテキスト")
    token_usage: TokenUsage = Field(description="トークン使用量")
    model: str = Field(description="使用したモデル名")
    finish_reason: str | None = Field(default=None, description="終了理由")
