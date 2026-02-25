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
    thinking: int = Field(default=0, ge=0, description="思考/推論トークン数")

    @property
    def total(self) -> int:
        """合計トークン数"""
        return self.input + self.output + self.thinking


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
    """Gemini Grounding設定（Google Search）"""

    enabled: bool = Field(default=False, description="Groundingを有効化")
    dynamic_retrieval_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Dynamic retrieval threshold（0.0〜1.0）",
    )


class GeminiUrlContextConfig(BaseModel):
    """Gemini URL Context設定

    URLからコンテンツを取得してコンテキストとして使用。
    最大20 URL、単一URL最大34MB。
    """

    enabled: bool = Field(default=False, description="URL Contextを有効化")


class GeminiCodeExecutionConfig(BaseModel):
    """Gemini Code Execution設定

    Pythonコードを生成・実行して計算や問題解決を行う。
    """

    enabled: bool = Field(default=False, description="Code Executionを有効化")


class GeminiThinkingConfig(BaseModel):
    """Gemini Thinking設定

    Gemini 2.5/3モデルの推論（thinking）機能を制御。

    - thinking_budget: トークン数で制御（0-24576）。0=無効、大きいほど深い推論。
    - thinking_level: "low" または "high"。Gemini 3向け推奨。
    - 両方同時に指定するとエラーになるため、いずれか一方のみ設定すること。
    """

    enabled: bool = Field(default=True, description="Thinkingを有効化（デフォルト有効）")
    thinking_budget: int | None = Field(
        default=None,
        ge=0,
        le=24576,
        description="Thinking budget（トークン数、0-24576）",
    )
    thinking_level: str | None = Field(
        default=None,
        pattern="^(low|high)$",
        description="Thinking level（Gemini 3向け: 'low' or 'high'）",
    )


class GeminiConfig(BaseModel):
    """Gemini固有の設定

    利用可能なツール:
    - grounding (google_search): Google検索でGrounding
    - url_context: URLからコンテンツを取得
    - code_execution: Pythonコード実行

    推論設定:
    - thinking: Adaptive thinking（Gemini 2.5/3）
    """

    grounding: GeminiGroundingConfig = Field(
        default_factory=GeminiGroundingConfig,
        description="Grounding設定（Google Search）",
    )
    url_context: GeminiUrlContextConfig = Field(
        default_factory=GeminiUrlContextConfig,
        description="URL Context設定",
    )
    code_execution: GeminiCodeExecutionConfig = Field(
        default_factory=GeminiCodeExecutionConfig,
        description="Code Execution設定",
    )
    thinking: GeminiThinkingConfig = Field(
        default_factory=GeminiThinkingConfig,
        description="Thinking設定（Gemini 2.5/3）",
    )
    safety_settings: dict[str, str] | None = Field(
        default=None,
        description="Safety settings",
    )


class OpenAIReasoningConfig(BaseModel):
    """OpenAI Reasoning設定（GPT-5系向け）

    reasoning_effort: 推論の深さを制御
    - none: 推論なし（低レイテンシ）
    - low: 軽い推論
    - medium: 中程度の推論
    - high: 深い推論
    - xhigh: 最も深い推論（GPT-5.2+）
    """

    effort: str | None = Field(
        default=None,
        pattern="^(none|low|medium|high|xhigh)$",
        description="Reasoning effort level",
    )


class OpenAIWebSearchConfig(BaseModel):
    """OpenAI Web Search設定

    GPT-5系でWeb検索を有効化。
    """

    enabled: bool = Field(default=False, description="Web Searchを有効化")


class OpenAIConfig(BaseModel):
    """OpenAI固有の設定

    利用可能なオプション:
    - reasoning: 推論の深さを制御（GPT-5系）
    - web_search: Web検索機能
    - verbosity: 出力の詳細度（concise/detailed）
    """

    reasoning: OpenAIReasoningConfig = Field(
        default_factory=OpenAIReasoningConfig,
        description="Reasoning設定",
    )
    web_search: OpenAIWebSearchConfig = Field(
        default_factory=OpenAIWebSearchConfig,
        description="Web Search設定",
    )
    verbosity: str | None = Field(
        default=None,
        pattern="^(concise|detailed)$",
        description="出力の詳細度",
    )


class AnthropicExtendedThinkingConfig(BaseModel):
    """Anthropic Extended Thinking設定

    Claude 4系のExtended Thinking機能。
    - budget_tokens: Thinking用のトークン予算（最小1024）
    """

    enabled: bool = Field(default=False, description="Extended Thinkingを有効化")
    budget_tokens: int | None = Field(
        default=None,
        ge=1024,
        description="Thinking budget（最小1024トークン）",
    )


class AnthropicConfig(BaseModel):
    """Anthropic固有の設定

    利用可能なオプション:
    - extended_thinking: Extended Thinking（Claude 4系）
    - effort: 推論の深さ（Claude Opus 4.5向け、low/medium/high）
    """

    extended_thinking: AnthropicExtendedThinkingConfig = Field(
        default_factory=AnthropicExtendedThinkingConfig,
        description="Extended Thinking設定",
    )
    effort: str | None = Field(
        default=None,
        pattern="^(low|medium|high)$",
        description="Effort level（Claude Opus 4.5向け）",
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


class JSONWithUsage(BaseModel):
    """JSON生成結果とトークン使用量

    generate_json_with_usage()の戻り値型。
    """

    model_config = ConfigDict(frozen=True)

    data: dict[str, Any] = Field(..., description="パース済みのJSON")
    token_usage: TokenUsage = Field(..., description="トークン使用量")
    model: str = Field(..., description="使用したモデルID")
    latency_ms: float | None = Field(default=None, description="レイテンシ（ミリ秒）")


class LLMCallMetadata(BaseModel):
    """LLM呼び出しメタデータ

    ログ・追跡用の情報。
    """

    run_id: str | None = Field(default=None, description="実行ID")
    step_id: str | None = Field(default=None, description="工程ID")
    attempt: int = Field(default=1, ge=1, description="試行回数")
    tenant_id: str | None = Field(default=None, description="テナントID")
    correlation_id: str | None = Field(default=None, description="相関ID")
