"""Gemini API クライアント

Google Gemini API (google-genai SDK) を使用したLLMクライアント。
grounding オプション対応。

フォールバック禁止:
- 別モデルへの自動切替禁止
- 同一条件リトライのみ許可（上限3回、ログ必須）
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Any

from .base import LLMInterface
from .exceptions import (
    ErrorCategory,
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMContentFilterError,
    LLMError,
    LLMInvalidRequestError,
    LLMJSONParseError,
    LLMRateLimitError,
    LLMServiceUnavailableError,
    LLMTimeoutError,
    LLMValidationError,
)
from .schemas import (
    GeminiConfig,
    JSONWithUsage,
    LLMCallMetadata,
    LLMMessage,
    LLMRequestConfig,
    LLMResponse,
    TokenUsage,
)

logger = logging.getLogger(__name__)


# Gemini SDK import（遅延ロード）
try:
    from google import genai
    from google.genai import types

    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None  # type: ignore
    types = None  # type: ignore


class GeminiClient(LLMInterface):
    """Gemini API クライアント

    対応モデル:
    - gemini-2.0-flash
    - gemini-2.5-pro
    - gemini-2.5-flash
    等

    特徴:
    - grounding オプション対応
    - 統一エラーハンドリング
    - リトライ（同一条件のみ、上限3回）
    """

    PROVIDER_NAME = "gemini"

    AVAILABLE_MODELS = [
        "gemini-3-pro-preview",
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash",
    ]

    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        gemini_config: GeminiConfig | None = None,
        timeout: float = 420.0,
    ) -> None:
        """初期化

        Args:
            api_key: Gemini API キー（省略時は環境変数 GEMINI_API_KEY を使用）
            model: 使用するモデルID
            gemini_config: Gemini固有の設定（grounding等）
            timeout: タイムアウト（秒）

        Raises:
            LLMConfigurationError: 設定エラー
        """
        if not GENAI_AVAILABLE:
            raise LLMConfigurationError(
                message="google-genai package is not installed. Run: pip install google-genai",
                provider=self.PROVIDER_NAME,
                missing_config=["google-genai package"],
            )

        self._api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self._api_key:
            raise LLMConfigurationError(
                message=("Gemini API key is required. Set GEMINI_API_KEY env var or pass api_key parameter."),
                provider=self.PROVIDER_NAME,
                missing_config=["GEMINI_API_KEY"],
            )

        self._model = model or self.DEFAULT_MODEL
        if self._model not in self.AVAILABLE_MODELS:
            logger.warning(f"Model {self._model} is not in the known models list. Available: {self.AVAILABLE_MODELS}")

        self._gemini_config = gemini_config or GeminiConfig()
        self._timeout = timeout

        # クライアント初期化
        self._client = genai.Client(api_key=self._api_key)

    @property
    def provider_name(self) -> str:
        return self.PROVIDER_NAME

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    @property
    def available_models(self) -> list[str]:
        return self.AVAILABLE_MODELS.copy()

    @property
    def model(self) -> str:
        """現在設定されているモデル"""
        return self._model

    @model.setter
    def model(self, value: str) -> None:
        """モデルを変更"""
        self._model = value

    @property
    def grounding_enabled(self) -> bool:
        """Groundingが有効かどうか"""
        return self._gemini_config.grounding.enabled

    @property
    def url_context_enabled(self) -> bool:
        """URL Contextが有効かどうか"""
        return self._gemini_config.url_context.enabled

    @property
    def code_execution_enabled(self) -> bool:
        """Code Executionが有効かどうか"""
        return self._gemini_config.code_execution.enabled

    def enable_grounding(
        self,
        enabled: bool = True,
        dynamic_retrieval_threshold: float | None = None,
    ) -> None:
        """Groundingの有効/無効を切り替え

        Args:
            enabled: Groundingを有効にするかどうか
            dynamic_retrieval_threshold: Dynamic retrieval threshold (0.0-1.0)
        """
        self._gemini_config.grounding.enabled = enabled
        if dynamic_retrieval_threshold is not None:
            self._gemini_config.grounding.dynamic_retrieval_threshold = dynamic_retrieval_threshold
        logger.info(
            f"Grounding {'enabled' if enabled else 'disabled'}",
            extra={
                "provider": self.PROVIDER_NAME,
                "threshold": dynamic_retrieval_threshold,
            },
        )

    def enable_url_context(self, enabled: bool = True) -> None:
        """URL Contextの有効/無効を切り替え

        URLからコンテンツを取得してコンテキストとして使用。
        最大20 URL、単一URL最大34MB。

        Args:
            enabled: URL Contextを有効にするかどうか
        """
        self._gemini_config.url_context.enabled = enabled
        logger.info(
            f"URL Context {'enabled' if enabled else 'disabled'}",
            extra={"provider": self.PROVIDER_NAME},
        )

    def enable_code_execution(self, enabled: bool = True) -> None:
        """Code Executionの有効/無効を切り替え

        Pythonコードを生成・実行して計算や問題解決を行う。

        Args:
            enabled: Code Executionを有効にするかどうか
        """
        self._gemini_config.code_execution.enabled = enabled
        logger.info(
            f"Code Execution {'enabled' if enabled else 'disabled'}",
            extra={"provider": self.PROVIDER_NAME},
        )

    def configure_thinking(
        self,
        enabled: bool = True,
        thinking_budget: int | None = None,
        thinking_level: str | None = None,
    ) -> None:
        """Thinking（推論）設定を変更

        Gemini 2.5/3モデルのAdaptive Thinking機能を制御。

        Args:
            enabled: Thinkingを有効にするかどうか
            thinking_budget: トークン数（0-24576）。Gemini 2.5向け。
            thinking_level: 'low' or 'high'。Gemini 3向け推奨。

        Note:
            thinking_budget と thinking_level を同時に指定するとAPIエラーになります。
        """
        if thinking_budget is not None and thinking_level is not None:
            raise LLMConfigurationError(
                message="Cannot specify both thinking_budget and thinking_level",
                provider=self.PROVIDER_NAME,
                missing_config=[],
            )

        self._gemini_config.thinking.enabled = enabled
        if thinking_budget is not None:
            self._gemini_config.thinking.thinking_budget = thinking_budget
            self._gemini_config.thinking.thinking_level = None
        if thinking_level is not None:
            self._gemini_config.thinking.thinking_level = thinking_level
            self._gemini_config.thinking.thinking_budget = None

        logger.info(
            f"Thinking {'enabled' if enabled else 'disabled'}",
            extra={
                "provider": self.PROVIDER_NAME,
                "thinking_budget": thinking_budget,
                "thinking_level": thinking_level,
            },
        )

    async def generate(
        self,
        messages: list[dict[str, str]] | list[LLMMessage],
        system_prompt: str,
        config: LLMRequestConfig | None = None,
        metadata: LLMCallMetadata | None = None,
    ) -> LLMResponse:
        """テキスト生成

        Args:
            messages: 会話履歴
            system_prompt: システムプロンプト
            config: リクエスト設定
            metadata: 追跡用メタデータ

        Returns:
            LLMResponse: 生成結果
        """
        config = config or LLMRequestConfig()
        metadata = metadata or LLMCallMetadata()

        self._log_request("generate", self._model, metadata)
        start_time = time.time()

        try:
            # メッセージを正規化
            normalized_messages = self._normalize_messages(messages)

            # Gemini用のコンテンツを構築
            contents = self._build_contents(normalized_messages)

            # システムプロンプト設定
            system_instruction = system_prompt if system_prompt else None

            # grounding設定
            tools = self._build_tools() if self._gemini_config.grounding.enabled else None

            # 生成設定を構築（system_instruction と tools を含める）
            generation_config = self._build_generation_config(
                config,
                system_instruction=system_instruction,
                tools=tools,
            )

            # API呼び出し（リトライ付き）
            response = await self._call_with_retry(
                contents=contents,
                generation_config=generation_config,
                metadata=metadata,
            )

            latency_ms = (time.time() - start_time) * 1000

            # レスポンスをパース
            llm_response = self._parse_response(response, latency_ms)

            self._log_response("generate", llm_response, metadata)
            return llm_response

        except LLMError:
            raise
        except Exception as e:
            self._log_error("generate", e, metadata)
            raise self._convert_exception(e)

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
            messages: 会話履歴
            system_prompt: システムプロンプト
            schema: 期待するJSONスキーマ
            config: リクエスト設定
            metadata: 追跡用メタデータ

        Returns:
            dict: パース済みのJSON
        """
        config = config or LLMRequestConfig()
        metadata = metadata or LLMCallMetadata()

        self._log_request("generate_json", self._model, metadata)
        start_time = time.time()

        try:
            # メッセージを正規化
            normalized_messages = self._normalize_messages(messages)

            # Gemini用のコンテンツを構築
            contents = self._build_contents(normalized_messages)

            # システムプロンプトにJSON出力指示を追加
            json_system_prompt = f"""{system_prompt}

出力形式: JSON
以下のスキーマに従ってJSONを出力してください:
{json.dumps(schema, ensure_ascii=False, indent=2)}"""

            # JSON出力用の生成設定（system_instruction を含む、tools は無効化）
            generation_config = self._build_generation_config(
                config,
                response_mime_type="application/json",
                response_schema=schema,
                system_instruction=json_system_prompt,
                tools=None,  # JSON出力時はgroundingを無効化
            )

            # API呼び出し（リトライ付き）
            response = await self._call_with_retry(
                contents=contents,
                generation_config=generation_config,
                metadata=metadata,
            )

            latency_ms = (time.time() - start_time) * 1000

            # レスポンスをパース
            llm_response = self._parse_response(response, latency_ms)
            self._log_response("generate_json", llm_response, metadata)

            # JSONをパース
            try:
                result: dict[str, Any] = json.loads(llm_response.content)
            except json.JSONDecodeError as e:
                raise LLMJSONParseError(
                    message=f"Failed to parse JSON output: {e}",
                    provider=self.PROVIDER_NAME,
                    model=self._model,
                    raw_output=llm_response.content,
                    parse_error=str(e),
                )

            # resultが辞書でない場合はエラー
            if not isinstance(result, dict):
                raise LLMValidationError(
                    message=f"Expected JSON object, got {type(result).__name__}",
                    provider=self.PROVIDER_NAME,
                    model=self._model,
                    validation_errors=[f"Expected dict, got {type(result).__name__}"],
                )

            return result

        except LLMError:
            raise
        except Exception as e:
            self._log_error("generate_json", e, metadata)
            raise self._convert_exception(e)

    async def generate_json_with_usage(
        self,
        messages: list[dict[str, str]] | list[LLMMessage],
        system_prompt: str,
        schema: dict[str, Any],
        config: LLMRequestConfig | None = None,
        metadata: LLMCallMetadata | None = None,
    ) -> "JSONWithUsage":
        """JSON出力とトークン使用量を返すテキスト生成

        generate_json()と同じだが、トークン使用量も返す。

        Args:
            messages: 会話履歴
            system_prompt: システムプロンプト
            schema: 期待するJSONスキーマ
            config: リクエスト設定
            metadata: 追跡用メタデータ

        Returns:
            JSONWithUsage: パース済みのJSONとトークン使用量
        """
        config = config or LLMRequestConfig()
        metadata = metadata or LLMCallMetadata()

        self._log_request("generate_json_with_usage", self._model, metadata)
        start_time = time.time()

        try:
            # メッセージを正規化
            normalized_messages = self._normalize_messages(messages)

            # Gemini用のコンテンツを構築
            contents = self._build_contents(normalized_messages)

            # システムプロンプトにJSON出力指示を追加
            json_system_prompt = f"""{system_prompt}

出力形式: JSON
以下のスキーマに従ってJSONを出力してください:
{json.dumps(schema, ensure_ascii=False, indent=2)}"""

            # JSON出力用の生成設定
            generation_config = self._build_generation_config(
                config,
                response_mime_type="application/json",
                response_schema=schema,
                system_instruction=json_system_prompt,
                tools=None,
            )

            # API呼び出し
            response = await self._call_with_retry(
                contents=contents,
                generation_config=generation_config,
                metadata=metadata,
            )

            latency_ms = (time.time() - start_time) * 1000

            # レスポンスをパース
            llm_response = self._parse_response(response, latency_ms)
            self._log_response("generate_json_with_usage", llm_response, metadata)

            # JSONをパース
            try:
                result: dict[str, Any] = json.loads(llm_response.content)
            except json.JSONDecodeError as e:
                raise LLMJSONParseError(
                    message=f"Failed to parse JSON output: {e}",
                    provider=self.PROVIDER_NAME,
                    model=self._model,
                    raw_output=llm_response.content,
                    parse_error=str(e),
                )

            if not isinstance(result, dict):
                raise LLMValidationError(
                    message=f"Expected JSON object, got {type(result).__name__}",
                    provider=self.PROVIDER_NAME,
                    model=self._model,
                    validation_errors=[f"Expected dict, got {type(result).__name__}"],
                )

            return JSONWithUsage(
                data=result,
                token_usage=llm_response.token_usage,
                model=llm_response.model,
                latency_ms=latency_ms,
            )

        except LLMError:
            raise
        except Exception as e:
            self._log_error("generate_json_with_usage", e, metadata)
            raise self._convert_exception(e)

    async def health_check(self) -> bool:
        """ヘルスチェック"""
        try:
            # 簡単なリクエストでAPIの疎通確認
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._client.models.generate_content,
                    model=self._model,
                    contents="Hello",
                    config=types.GenerateContentConfig(
                        max_output_tokens=10,
                    ),
                ),
                timeout=10.0,
            )
            return response is not None and response.text is not None
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False

    def _build_contents(self, messages: list[dict[str, str]]) -> list[types.Content]:
        """Gemini用のコンテンツを構築"""
        contents = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            # Geminiのroleマッピング
            if role == "system":
                # systemはcontentsには含めず、system_instructionで処理
                continue
            elif role == "assistant":
                gemini_role = "model"
            else:
                gemini_role = "user"

            contents.append(
                types.Content(
                    role=gemini_role,
                    parts=[types.Part(text=content)],
                )
            )

        return contents

    def _build_generation_config(
        self,
        config: LLMRequestConfig,
        response_mime_type: str | None = None,
        response_schema: dict[str, Any] | None = None,
        system_instruction: str | None = None,
        tools: list[Any] | None = None,
    ) -> types.GenerateContentConfig:
        """生成設定を構築"""
        kwargs: dict[str, Any] = {
            "temperature": config.temperature,
            "max_output_tokens": config.max_tokens,
        }

        if config.top_p is not None:
            kwargs["top_p"] = config.top_p
        if config.top_k is not None:
            kwargs["top_k"] = config.top_k
        if config.stop_sequences:
            kwargs["stop_sequences"] = config.stop_sequences

        if response_mime_type:
            kwargs["response_mime_type"] = response_mime_type
        if response_schema:
            kwargs["response_schema"] = response_schema

        # system_instruction は GenerateContentConfig の中に含める
        if system_instruction:
            kwargs["system_instruction"] = system_instruction

        # tools も GenerateContentConfig の中に含める
        if tools:
            kwargs["tools"] = tools

        # Thinking設定（Gemini 2.5/3向け）
        thinking_cfg = self._gemini_config.thinking
        if thinking_cfg.enabled:
            # thinking_level と thinking_budget は排他的
            if thinking_cfg.thinking_level is not None:
                # thinking_level を enum に変換
                level_map = {
                    "low": types.ThinkingLevel.LOW,
                    "high": types.ThinkingLevel.HIGH,
                }
                thinking_level_enum = level_map.get(
                    thinking_cfg.thinking_level.lower(),
                    types.ThinkingLevel.HIGH,
                )
                kwargs["thinking_config"] = types.ThinkingConfig(
                    thinking_level=thinking_level_enum,
                )
            elif thinking_cfg.thinking_budget is not None:
                kwargs["thinking_config"] = types.ThinkingConfig(
                    thinking_budget=thinking_cfg.thinking_budget,
                )
            # enabled=True だがbudget/levelともにNoneなら、デフォルト動作（モデル任せ）
        else:
            # Thinking無効化：budget=0で無効化
            kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_budget=0,
            )

        return types.GenerateContentConfig(**kwargs)

    def _build_tools(self) -> list[Any] | None:
        """全ツールを構築（google_search, url_context, code_execution）"""
        tools: list[Any] = []

        # Google Search (Grounding)
        if self._gemini_config.grounding.enabled:
            tools.append(
                types.Tool(
                    google_search=types.GoogleSearch(),
                )
            )

        # URL Context
        if self._gemini_config.url_context.enabled:
            tools.append({"url_context": {}})

        # Code Execution
        if self._gemini_config.code_execution.enabled:
            tools.append({"code_execution": {}})

        return tools if tools else None

    async def _call_with_retry(
        self,
        contents: list[types.Content],
        generation_config: types.GenerateContentConfig,
        metadata: LLMCallMetadata,
    ) -> Any:
        """リトライ付きでAPI呼び出し

        同一条件でのリトライのみ許可（フォールバック禁止）
        """
        retry_config = self._get_retry_config()
        last_error: Exception | None = None

        for attempt in range(1, retry_config.max_attempts + 1):
            try:
                # メタデータのattemptを更新
                metadata.attempt = attempt

                logger.debug(
                    f"API call attempt {attempt}/{retry_config.max_attempts}",
                    extra={
                        "provider": self.PROVIDER_NAME,
                        "model": self._model,
                        "attempt": attempt,
                    },
                )

                # API呼び出し（タイムアウト付き）
                # system_instruction と tools は generation_config に含まれている
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._client.models.generate_content,
                        model=self._model,
                        contents=contents,
                        config=generation_config,
                    ),
                    timeout=self._timeout,
                )

                return response

            except TimeoutError:
                last_error = LLMTimeoutError(
                    message=f"Request timed out after {self._timeout}s",
                    provider=self.PROVIDER_NAME,
                    model=self._model,
                    timeout_seconds=self._timeout,
                )
                logger.warning(
                    f"Timeout on attempt {attempt}",
                    extra={"provider": self.PROVIDER_NAME, "attempt": attempt},
                )

            except Exception as e:
                converted = self._convert_exception(e)
                last_error = converted

                # NON_RETRYABLEならすぐに終了
                if isinstance(converted, LLMError) and not converted.is_retryable():
                    raise converted

                logger.warning(
                    f"Error on attempt {attempt}: {e}",
                    extra={"provider": self.PROVIDER_NAME, "attempt": attempt},
                )

            # リトライ前の待機（指数バックオフ）
            if attempt < retry_config.max_attempts:
                delay = min(
                    retry_config.base_delay * (retry_config.exponential_base ** (attempt - 1)),
                    retry_config.max_delay,
                )
                logger.info(
                    f"Retrying in {delay:.1f}s",
                    extra={"provider": self.PROVIDER_NAME, "delay": delay},
                )
                await asyncio.sleep(delay)

        # 全リトライ失敗
        if last_error:
            raise last_error
        raise LLMServiceUnavailableError(
            message="All retry attempts failed",
            provider=self.PROVIDER_NAME,
            model=self._model,
        )

    def _parse_response(self, response: Any, latency_ms: float) -> LLMResponse:
        """レスポンスをパース"""
        # テキストを取得
        text = response.text or ""

        # finish_reasonを取得
        finish_reason = None
        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if hasattr(candidate, "finish_reason"):
                finish_reason = str(candidate.finish_reason)

        # トークン使用量を取得
        usage_metadata = getattr(response, "usage_metadata", None)
        if usage_metadata:
            input_tokens = getattr(usage_metadata, "prompt_token_count", 0) or 0
            output_tokens = getattr(usage_metadata, "candidates_token_count", 0) or 0
        else:
            # 推定（実際にはAPIから取得すべき）
            input_tokens = 0
            output_tokens = 0

        # Grounding情報を取得
        grounding_metadata = None
        if response.candidates and len(response.candidates) > 0:
            candidate = response.candidates[0]
            if hasattr(candidate, "grounding_metadata") and candidate.grounding_metadata:
                grounding_metadata = {
                    "search_entry_point": getattr(candidate.grounding_metadata, "search_entry_point", None),
                    "grounding_chunks": [
                        {
                            "web": {
                                "uri": getattr(chunk.web, "uri", None),
                                "title": getattr(chunk.web, "title", None),
                            }
                        }
                        for chunk in (getattr(candidate.grounding_metadata, "grounding_chunks", []) or [])
                        if hasattr(chunk, "web")
                    ],
                }

        return LLMResponse(
            content=text,
            token_usage=TokenUsage(input=input_tokens, output=output_tokens),
            model=self._model,
            finish_reason=finish_reason,
            created_at=datetime.now(),
            provider=self.PROVIDER_NAME,
            latency_ms=latency_ms,
            grounding_metadata=grounding_metadata,
        )

    def _convert_exception(self, e: Exception) -> LLMError:
        """例外を統一フォーマットに変換"""
        error_msg = str(e)
        error_type = type(e).__name__

        # エラーメッセージに基づいて分類
        if "401" in error_msg or "authentication" in error_msg.lower():
            return LLMAuthenticationError(
                message=f"Authentication failed: {error_msg}",
                provider=self.PROVIDER_NAME,
                model=self._model,
            )

        if "429" in error_msg or "rate limit" in error_msg.lower():
            return LLMRateLimitError(
                message=f"Rate limit exceeded: {error_msg}",
                provider=self.PROVIDER_NAME,
                model=self._model,
            )

        if "400" in error_msg or "invalid" in error_msg.lower():
            return LLMInvalidRequestError(
                message=f"Invalid request: {error_msg}",
                provider=self.PROVIDER_NAME,
                model=self._model,
                details={"original_error": error_type},
            )

        if "safety" in error_msg.lower() or "blocked" in error_msg.lower():
            return LLMContentFilterError(
                message=f"Content blocked: {error_msg}",
                provider=self.PROVIDER_NAME,
                model=self._model,
            )

        if "503" in error_msg or "unavailable" in error_msg.lower():
            return LLMServiceUnavailableError(
                message=f"Service unavailable: {error_msg}",
                provider=self.PROVIDER_NAME,
                model=self._model,
            )

        if "timeout" in error_msg.lower():
            return LLMTimeoutError(
                message=f"Timeout: {error_msg}",
                provider=self.PROVIDER_NAME,
                model=self._model,
            )

        # デフォルトはリトライ可能なエラーとして扱う
        return LLMError(
            message=f"Unknown error: {error_msg}",
            category=ErrorCategory.RETRYABLE,
            provider=self.PROVIDER_NAME,
            model=self._model,
            details={"original_error": error_type},
        )
