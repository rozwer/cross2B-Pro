"""Nano Banana (Gemini Image Generation) クライアント

Gemini API の画像生成機能を使用。
- Nano Banana: gemini-2.5-flash-image
- Nano Banana Pro: gemini-3-pro-image-preview

フォールバック禁止：別モデルへの自動切替は行わない。
"""

import base64
import logging
import os

from google import genai
from google.genai import types

from .exceptions import (
    ErrorCategory,
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMContentFilterError,
    LLMError,
    LLMRateLimitError,
    LLMServiceUnavailableError,
    LLMTimeoutError,
)
from .schemas import LLMCallMetadata, TokenUsage

logger = logging.getLogger(__name__)


class ImageGenerationConfig:
    """画像生成設定"""

    def __init__(
        self,
        aspect_ratio: str = "1:1",
        number_of_images: int = 1,
    ):
        """初期化

        Args:
            aspect_ratio: アスペクト比 ("1:1", "16:9", "9:16", "4:3", "3:4")
            number_of_images: 生成する画像数（1-4）
        """
        self.aspect_ratio = aspect_ratio
        self.number_of_images = min(max(number_of_images, 1), 4)


class ImageGenerationResult:
    """画像生成結果"""

    def __init__(
        self,
        images: list[bytes],
        text: str | None = None,
        model: str = "",
        provider: str = "nanobanana",
        token_usage: TokenUsage | None = None,
    ):
        self.images = images
        self.text = text
        self.model = model
        self.provider = provider
        self.token_usage = token_usage or TokenUsage(input=0, output=0)

    @property
    def image_count(self) -> int:
        return len(self.images)

    def get_base64_images(self) -> list[str]:
        """Base64エンコードされた画像リスト"""
        return [base64.b64encode(img).decode("utf-8") for img in self.images]


class NanoBananaClient:
    """Nano Banana（Gemini画像生成）クライアント

    Gemini API の画像生成機能を提供。
    - Nano Banana: gemini-2.5-flash-image（高速）
    - Nano Banana Pro: gemini-3-pro-image-preview（高品質）
    """

    PROVIDER_NAME = "nanobanana"

    AVAILABLE_MODELS = [
        "gemini-2.5-flash-image",  # Nano Banana（高速）
        "gemini-3-pro-image-preview",  # Nano Banana Pro（高品質）
    ]

    DEFAULT_MODEL = "gemini-2.5-flash-image"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        """初期化

        Args:
            api_key: Gemini APIキー（省略時は環境変数 GEMINI_API_KEY または NANO_BANANA_API_KEY）
            model: 使用するモデル名
            timeout: タイムアウト（秒）
        """
        resolved_key = (
            api_key
            or os.getenv("NANO_BANANA_API_KEY")
            or os.getenv("GEMINI_API_KEY")
        )
        if not resolved_key:
            raise LLMConfigurationError(
                message="NANO_BANANA_API_KEY or GEMINI_API_KEY is not set",
                provider=self.PROVIDER_NAME,
                missing_config=["api_key"],
            )

        self._model = model or self.DEFAULT_MODEL
        if self._model not in self.AVAILABLE_MODELS:
            raise LLMConfigurationError(
                message=f"Model '{self._model}' is not supported. "
                f"Available: {self.AVAILABLE_MODELS}",
                provider=self.PROVIDER_NAME,
                missing_config=[],
            )

        self._client = genai.Client(api_key=resolved_key)
        self._timeout = timeout

        logger.info(
            f"NanoBananaClient initialized with model={self._model}",
            extra={"provider": self.PROVIDER_NAME},
        )

    @property
    def provider_name(self) -> str:
        """プロバイダー名"""
        return self.PROVIDER_NAME

    @property
    def model(self) -> str:
        """現在のモデル"""
        return self._model

    @property
    def available_models(self) -> list[str]:
        """利用可能なモデル一覧"""
        return self.AVAILABLE_MODELS.copy()

    async def generate_image(
        self,
        prompt: str,
        config: ImageGenerationConfig | None = None,
        metadata: LLMCallMetadata | None = None,
    ) -> ImageGenerationResult:
        """画像生成

        Args:
            prompt: 画像生成プロンプト
            config: 画像生成設定
            metadata: 追跡用メタデータ

        Returns:
            ImageGenerationResult: 生成結果

        Raises:
            LLMError: API呼び出しエラー
        """
        config = config or ImageGenerationConfig()

        self._log_request("generate_image", metadata)

        try:
            generation_config = types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            )

            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=prompt,
                config=generation_config,
            )

            images: list[bytes] = []
            text_parts: list[str] = []

            if (
                response.candidates
                and response.candidates[0].content
                and response.candidates[0].content.parts
            ):
                for part in response.candidates[0].content.parts:
                    if part.text:
                        text_parts.append(part.text)
                    elif part.inline_data and part.inline_data.data:
                        images.append(part.inline_data.data)

            usage_metadata = response.usage_metadata
            input_tokens = (
                usage_metadata.prompt_token_count if usage_metadata else 0
            ) or 0
            output_tokens = (
                usage_metadata.candidates_token_count if usage_metadata else 0
            ) or 0
            token_usage = TokenUsage(input=input_tokens, output=output_tokens)

            result = ImageGenerationResult(
                images=images,
                text="\n".join(text_parts) if text_parts else None,
                model=self._model,
                provider=self.PROVIDER_NAME,
                token_usage=token_usage,
            )

            logger.info(
                f"Image generation succeeded: {result.image_count} images",
                extra={
                    "provider": self.PROVIDER_NAME,
                    "model": self._model,
                    "image_count": result.image_count,
                },
            )

            return result

        except Exception as e:
            error = self._convert_error(e)
            logger.error(
                f"Image generation failed: {error}",
                extra={
                    "provider": self.PROVIDER_NAME,
                    "model": self._model,
                    "error_type": type(e).__name__,
                },
            )
            raise error from e

    async def health_check(self) -> bool:
        """ヘルスチェック"""
        try:
            # モデル情報取得で疎通確認
            await self._client.aio.models.get(model=self._model)
            return True
        except Exception:
            return False

    def _log_request(
        self,
        method: str,
        metadata: LLMCallMetadata | None,
    ) -> None:
        """リクエストログ"""
        logger.info(
            "NanoBanana request",
            extra={
                "provider": self.PROVIDER_NAME,
                "method": method,
                "model": self._model,
                "run_id": metadata.run_id if metadata else None,
                "step_id": metadata.step_id if metadata else None,
            },
        )

    def _convert_error(self, error: Exception) -> LLMError:
        """エラー変換"""
        error_msg = str(error).lower()
        error_type = type(error).__name__

        if "authentication" in error_msg or "api key" in error_msg:
            return LLMAuthenticationError(
                message=f"Authentication failed: {error}",
                provider=self.PROVIDER_NAME,
                model=self._model,
            )
        elif "rate" in error_msg and "limit" in error_msg:
            return LLMRateLimitError(
                message=f"Rate limit exceeded: {error}",
                provider=self.PROVIDER_NAME,
                model=self._model,
                retry_after=60.0,
            )
        elif "timeout" in error_msg:
            return LLMTimeoutError(
                message=f"Request timeout: {error}",
                provider=self.PROVIDER_NAME,
                model=self._model,
                timeout_seconds=self._timeout,
            )
        elif "safety" in error_msg or "blocked" in error_msg:
            return LLMContentFilterError(
                message=f"Content blocked by safety filter: {error}",
                provider=self.PROVIDER_NAME,
                model=self._model,
                blocked_reason="safety_filter",
            )
        elif "unavailable" in error_msg or "503" in error_msg:
            return LLMServiceUnavailableError(
                message=f"Service unavailable: {error}",
                provider=self.PROVIDER_NAME,
                model=self._model,
            )

        return LLMError(
            message=f"Image generation error: {error}",
            category=ErrorCategory.RETRYABLE,
            provider=self.PROVIDER_NAME,
            model=self._model,
            details={"original_error": error_type},
        )
