"""LLM関連の型定義

LLMレスポンス、トークン使用量などの共通スキーマを定義。
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TokenUsage(BaseModel):
    """トークン使用量"""

    model_config = ConfigDict(frozen=True)

    input: int = Field(..., ge=0, description="入力トークン数")
    output: int = Field(..., ge=0, description="出力トークン数")

    @property
    def total(self) -> int:
        """合計トークン数"""
        return self.input + self.output


class LLMResponse(BaseModel):
    """LLMレスポンス

    全プロバイダーで共通のレスポンス形式。
    """

    model_config = ConfigDict(frozen=True)

    content: str = Field(..., description="生成されたテキスト")
    token_usage: TokenUsage = Field(..., description="トークン使用量")
    model: str = Field(..., description="使用したモデルID")
    finish_reason: str | None = Field(
        default=None,
        description="終了理由（stop, length, content_filter等）",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="レスポンス生成日時",
    )
    provider: str = Field(..., description="プロバイダー名")
    latency_ms: float | None = Field(
        default=None,
        ge=0,
        description="レイテンシ（ミリ秒）",
    )
    grounding_metadata: dict[str, Any] | None = Field(
        default=None,
        description="Grounding情報（Gemini等）",
    )


class LLMMessage(BaseModel):
    """LLMメッセージ

    会話履歴の1メッセージを表す。
    """

    model_config = ConfigDict(frozen=True)

    role: str = Field(..., pattern="^(system|user|assistant)$", description="役割")
    content: str = Field(..., description="メッセージ内容")


class LLMRequestConfig(BaseModel):
    """LLMリクエスト設定

    generate/generate_json呼び出し時のオプション設定。
    """

    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="温度パラメータ（0.0〜2.0）",
    )
    max_tokens: int = Field(
        default=4096,
        ge=1,
        le=128000,
        description="最大出力トークン数",
    )
    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Top-pサンプリング（0.0〜1.0）",
    )
    top_k: int | None = Field(
        default=None,
        ge=1,
        description="Top-kサンプリング",
    )
    stop_sequences: list[str] | None = Field(
        default=None,
        description="停止シーケンス",
    )
    presence_penalty: float | None = Field(
        default=None,
        ge=-2.0,
        le=2.0,
        description="Presence penalty",
    )
    frequency_penalty: float | None = Field(
        default=None,
        ge=-2.0,
        le=2.0,
        description="Frequency penalty",
    )


class GeminiGroundingConfig(BaseModel):
    """Gemini Grounding設定"""

    enabled: bool = Field(default=False, description="Groundingを有効化")
    dynamic_retrieval_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Dynamic retrieval threshold（0.0〜1.0）",
    )


class GeminiConfig(BaseModel):
    """Gemini固有の設定"""

    grounding: GeminiGroundingConfig = Field(
        default_factory=GeminiGroundingConfig,
        description="Grounding設定",
    )
    safety_settings: dict[str, str] | None = Field(
        default=None,
        description="Safety settings",
    )


class RetryConfig(BaseModel):
    """リトライ設定"""

    max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="最大リトライ回数",
    )
    base_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=60.0,
        description="基本待機時間（秒）",
    )
    max_delay: float = Field(
        default=30.0,
        ge=1.0,
        le=300.0,
        description="最大待機時間（秒）",
    )
    exponential_base: float = Field(
        default=2.0,
        ge=1.0,
        le=10.0,
        description="指数バックオフの底",
    )


class LLMCallMetadata(BaseModel):
    """LLM呼び出しメタデータ

    ログ・追跡用の情報。
    """

    run_id: str | None = Field(default=None, description="実行ID")
    step_id: str | None = Field(default=None, description="工程ID")
    attempt: int = Field(default=1, ge=1, description="試行回数")
    tenant_id: str | None = Field(default=None, description="テナントID")
    correlation_id: str | None = Field(default=None, description="相関ID")
