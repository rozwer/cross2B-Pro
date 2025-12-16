"""Geminiクライアントのテスト"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.llm import (
    ErrorCategory,
    GeminiClient,
    GeminiConfig,
    GeminiGroundingConfig,
    LLMAuthenticationError,
    LLMCallMetadata,
    LLMConfigurationError,
    LLMJSONParseError,
    LLMMessage,
    LLMRateLimitError,
    LLMRequestConfig,
    LLMResponse,
    LLMTimeoutError,
    TokenUsage,
)


class TestTokenUsage:
    """TokenUsageのテスト"""

    def test_total(self) -> None:
        """合計トークン数が正しく計算されること"""
        usage = TokenUsage(input=100, output=50)
        assert usage.total == 150

    def test_immutable(self) -> None:
        """TokenUsageが不変であること"""
        usage = TokenUsage(input=100, output=50)
        with pytest.raises(Exception):  # ValidationError
            usage.input = 200  # type: ignore


class TestLLMResponse:
    """LLMResponseのテスト"""

    def test_create(self) -> None:
        """LLMResponseが正しく作成されること"""
        response = LLMResponse(
            content="Hello, world!",
            token_usage=TokenUsage(input=10, output=5),
            model="gemini-2.0-flash",
            provider="gemini",
        )
        assert response.content == "Hello, world!"
        assert response.token_usage.total == 15
        assert response.model == "gemini-2.0-flash"
        assert response.provider == "gemini"

    def test_with_grounding_metadata(self) -> None:
        """Grounding情報付きレスポンスが正しく作成されること"""
        response = LLMResponse(
            content="Based on search results...",
            token_usage=TokenUsage(input=10, output=20),
            model="gemini-2.0-flash",
            provider="gemini",
            grounding_metadata={
                "search_entry_point": "test query",
                "grounding_chunks": [{"web": {"uri": "https://example.com"}}],
            },
        )
        assert response.grounding_metadata is not None
        assert response.grounding_metadata["search_entry_point"] == "test query"


class TestLLMRequestConfig:
    """LLMRequestConfigのテスト"""

    def test_defaults(self) -> None:
        """デフォルト値が正しいこと"""
        config = LLMRequestConfig()
        assert config.temperature == 0.7
        assert config.max_tokens == 4096

    def test_custom_values(self) -> None:
        """カスタム値が設定できること"""
        config = LLMRequestConfig(temperature=0.5, max_tokens=2048, top_p=0.9)
        assert config.temperature == 0.5
        assert config.max_tokens == 2048
        assert config.top_p == 0.9


class TestGeminiConfig:
    """GeminiConfigのテスト"""

    def test_defaults(self) -> None:
        """デフォルト値が正しいこと"""
        config = GeminiConfig()
        assert config.grounding.enabled is False
        assert config.grounding.dynamic_retrieval_threshold is None

    def test_grounding_enabled(self) -> None:
        """Grounding有効化が設定できること"""
        config = GeminiConfig(
            grounding=GeminiGroundingConfig(enabled=True, dynamic_retrieval_threshold=0.5)
        )
        assert config.grounding.enabled is True
        assert config.grounding.dynamic_retrieval_threshold == 0.5


class TestGeminiClientInitialization:
    """GeminiClient初期化のテスト"""

    def test_missing_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """APIキーがない場合にエラーになること"""
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        with patch("apps.api.llm.gemini.GENAI_AVAILABLE", True):
            with pytest.raises(LLMConfigurationError) as exc_info:
                GeminiClient()

            assert "GEMINI_API_KEY" in str(exc_info.value)

    def test_missing_package(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """google-genaiパッケージがない場合にエラーになること"""
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")

        with patch("apps.api.llm.gemini.GENAI_AVAILABLE", False):
            with pytest.raises(LLMConfigurationError) as exc_info:
                GeminiClient()

            assert "google-genai" in str(exc_info.value)

    def test_successful_initialization(
        self, mock_gemini_api_key: str, mock_genai_module: MagicMock
    ) -> None:
        """正常に初期化できること"""
        with patch("apps.api.llm.gemini.GENAI_AVAILABLE", True):
            with patch("apps.api.llm.gemini.genai", mock_genai_module):
                client = GeminiClient(api_key=mock_gemini_api_key)
                assert client.provider_name == "gemini"
                assert client.model == "gemini-2.5-flash"

    def test_custom_model(
        self, mock_gemini_api_key: str, mock_genai_module: MagicMock
    ) -> None:
        """カスタムモデルを指定できること"""
        with patch("apps.api.llm.gemini.GENAI_AVAILABLE", True):
            with patch("apps.api.llm.gemini.genai", mock_genai_module):
                client = GeminiClient(
                    api_key=mock_gemini_api_key,
                    model="gemini-2.5-pro",
                )
                assert client.model == "gemini-2.5-pro"


class TestGeminiClientProperties:
    """GeminiClientプロパティのテスト"""

    def test_provider_name(
        self, mock_gemini_api_key: str, mock_genai_module: MagicMock
    ) -> None:
        """provider_nameが正しいこと"""
        with patch("apps.api.llm.gemini.GENAI_AVAILABLE", True):
            with patch("apps.api.llm.gemini.genai", mock_genai_module):
                client = GeminiClient(api_key=mock_gemini_api_key)
                assert client.provider_name == "gemini"

    def test_default_model(
        self, mock_gemini_api_key: str, mock_genai_module: MagicMock
    ) -> None:
        """default_modelが正しいこと"""
        with patch("apps.api.llm.gemini.GENAI_AVAILABLE", True):
            with patch("apps.api.llm.gemini.genai", mock_genai_module):
                client = GeminiClient(api_key=mock_gemini_api_key)
                assert client.default_model == "gemini-2.5-flash"

    def test_available_models(
        self, mock_gemini_api_key: str, mock_genai_module: MagicMock
    ) -> None:
        """available_modelsが正しいこと"""
        with patch("apps.api.llm.gemini.GENAI_AVAILABLE", True):
            with patch("apps.api.llm.gemini.genai", mock_genai_module):
                client = GeminiClient(api_key=mock_gemini_api_key)
                models = client.available_models
                assert "gemini-2.5-flash" in models
                assert "gemini-2.5-pro" in models


class TestGeminiClientGrounding:
    """GeminiClient Groundingのテスト"""

    def test_grounding_disabled_by_default(
        self, mock_gemini_api_key: str, mock_genai_module: MagicMock
    ) -> None:
        """デフォルトでGroundingが無効であること"""
        with patch("apps.api.llm.gemini.GENAI_AVAILABLE", True):
            with patch("apps.api.llm.gemini.genai", mock_genai_module):
                client = GeminiClient(api_key=mock_gemini_api_key)
                assert client.grounding_enabled is False

    def test_enable_grounding(
        self, mock_gemini_api_key: str, mock_genai_module: MagicMock
    ) -> None:
        """Groundingを有効化できること"""
        with patch("apps.api.llm.gemini.GENAI_AVAILABLE", True):
            with patch("apps.api.llm.gemini.genai", mock_genai_module):
                client = GeminiClient(api_key=mock_gemini_api_key)
                client.enable_grounding(True, dynamic_retrieval_threshold=0.5)
                assert client.grounding_enabled is True

    def test_grounding_with_config(
        self, mock_gemini_api_key: str, mock_genai_module: MagicMock
    ) -> None:
        """GeminiConfigでGroundingを有効化できること"""
        config = GeminiConfig(grounding=GeminiGroundingConfig(enabled=True))

        with patch("apps.api.llm.gemini.GENAI_AVAILABLE", True):
            with patch("apps.api.llm.gemini.genai", mock_genai_module):
                client = GeminiClient(
                    api_key=mock_gemini_api_key,
                    gemini_config=config,
                )
                assert client.grounding_enabled is True


class TestGeminiClientGenerate:
    """GeminiClient.generateのテスト"""

    @pytest.mark.asyncio
    async def test_generate_success(
        self,
        mock_gemini_api_key: str,
        mock_genai_module: MagicMock,
        mock_genai_response: MagicMock,
    ) -> None:
        """正常に生成できること"""
        with patch("apps.api.llm.gemini.GENAI_AVAILABLE", True):
            with patch("apps.api.llm.gemini.genai", mock_genai_module):
                with patch("apps.api.llm.gemini.types", mock_genai_module.types):
                    mock_genai_module.Client.return_value.models.generate_content = (
                        MagicMock(return_value=mock_genai_response)
                    )

                    client = GeminiClient(api_key=mock_gemini_api_key)

                    # asyncio.to_threadをモック
                    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
                        mock_thread.return_value = mock_genai_response

                        response = await client.generate(
                            messages=[{"role": "user", "content": "Hello"}],
                            system_prompt="You are helpful.",
                        )

                        assert isinstance(response, LLMResponse)
                        assert response.content == "Hello! I'm a helpful assistant."
                        assert response.provider == "gemini"

    @pytest.mark.asyncio
    async def test_generate_with_llm_message(
        self,
        mock_gemini_api_key: str,
        mock_genai_module: MagicMock,
        mock_genai_response: MagicMock,
    ) -> None:
        """LLMMessageでも生成できること"""
        with patch("apps.api.llm.gemini.GENAI_AVAILABLE", True):
            with patch("apps.api.llm.gemini.genai", mock_genai_module):
                with patch("apps.api.llm.gemini.types", mock_genai_module.types):
                    client = GeminiClient(api_key=mock_gemini_api_key)

                    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
                        mock_thread.return_value = mock_genai_response

                        messages = [LLMMessage(role="user", content="Hello")]
                        response = await client.generate(
                            messages=messages,
                            system_prompt="You are helpful.",
                        )

                        assert isinstance(response, LLMResponse)

    @pytest.mark.asyncio
    async def test_generate_with_metadata(
        self,
        mock_gemini_api_key: str,
        mock_genai_module: MagicMock,
        mock_genai_response: MagicMock,
    ) -> None:
        """メタデータ付きで生成できること"""
        with patch("apps.api.llm.gemini.GENAI_AVAILABLE", True):
            with patch("apps.api.llm.gemini.genai", mock_genai_module):
                with patch("apps.api.llm.gemini.types", mock_genai_module.types):
                    client = GeminiClient(api_key=mock_gemini_api_key)

                    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
                        mock_thread.return_value = mock_genai_response

                        metadata = LLMCallMetadata(
                            run_id="run-123",
                            step_id="step-1",
                            tenant_id="tenant-abc",
                        )
                        response = await client.generate(
                            messages=[{"role": "user", "content": "Hello"}],
                            system_prompt="You are helpful.",
                            metadata=metadata,
                        )

                        assert isinstance(response, LLMResponse)


class TestGeminiClientGenerateJSON:
    """GeminiClient.generate_jsonのテスト"""

    @pytest.mark.asyncio
    async def test_generate_json_success(
        self,
        mock_gemini_api_key: str,
        mock_genai_module: MagicMock,
        mock_genai_json_response: MagicMock,
    ) -> None:
        """正常にJSON生成できること"""
        with patch("apps.api.llm.gemini.GENAI_AVAILABLE", True):
            with patch("apps.api.llm.gemini.genai", mock_genai_module):
                with patch("apps.api.llm.gemini.types", mock_genai_module.types):
                    client = GeminiClient(api_key=mock_gemini_api_key)

                    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
                        mock_thread.return_value = mock_genai_json_response

                        schema = {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "value": {"type": "integer"},
                            },
                        }
                        result = await client.generate_json(
                            messages=[{"role": "user", "content": "Give me data"}],
                            system_prompt="Return JSON data.",
                            schema=schema,
                        )

                        assert isinstance(result, dict)
                        assert result["name"] == "test"
                        assert result["value"] == 123

    @pytest.mark.asyncio
    async def test_generate_json_parse_error(
        self,
        mock_gemini_api_key: str,
        mock_genai_module: MagicMock,
    ) -> None:
        """不正なJSONでエラーになること"""
        invalid_response = MagicMock()
        invalid_response.text = "not valid json {"

        candidate = MagicMock()
        candidate.finish_reason = "STOP"
        candidate.grounding_metadata = None
        invalid_response.candidates = [candidate]

        usage = MagicMock()
        usage.prompt_token_count = 10
        usage.candidates_token_count = 10
        invalid_response.usage_metadata = usage

        with patch("apps.api.llm.gemini.GENAI_AVAILABLE", True):
            with patch("apps.api.llm.gemini.genai", mock_genai_module):
                with patch("apps.api.llm.gemini.types", mock_genai_module.types):
                    client = GeminiClient(api_key=mock_gemini_api_key)

                    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
                        mock_thread.return_value = invalid_response

                        schema = {"type": "object"}
                        with pytest.raises(LLMJSONParseError):
                            await client.generate_json(
                                messages=[{"role": "user", "content": "Give me data"}],
                                system_prompt="Return JSON.",
                                schema=schema,
                            )


class TestGeminiClientHealthCheck:
    """GeminiClient.health_checkのテスト"""

    @pytest.mark.asyncio
    async def test_health_check_success(
        self,
        mock_gemini_api_key: str,
        mock_genai_module: MagicMock,
        mock_genai_response: MagicMock,
    ) -> None:
        """ヘルスチェックが成功すること"""
        with patch("apps.api.llm.gemini.GENAI_AVAILABLE", True):
            with patch("apps.api.llm.gemini.genai", mock_genai_module):
                with patch("apps.api.llm.gemini.types", mock_genai_module.types):
                    mock_genai_module.Client.return_value.models.generate_content = (
                        MagicMock(return_value=mock_genai_response)
                    )

                    client = GeminiClient(api_key=mock_gemini_api_key)

                    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
                        mock_thread.return_value = mock_genai_response

                        result = await client.health_check()
                        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(
        self,
        mock_gemini_api_key: str,
        mock_genai_module: MagicMock,
    ) -> None:
        """ヘルスチェックが失敗すること"""
        with patch("apps.api.llm.gemini.GENAI_AVAILABLE", True):
            with patch("apps.api.llm.gemini.genai", mock_genai_module):
                with patch("apps.api.llm.gemini.types", mock_genai_module.types):
                    client = GeminiClient(api_key=mock_gemini_api_key)

                    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
                        mock_thread.side_effect = Exception("Connection error")

                        result = await client.health_check()
                        assert result is False


class TestGeminiClientErrorHandling:
    """GeminiClientエラーハンドリングのテスト"""

    @pytest.mark.asyncio
    async def test_authentication_error(
        self,
        mock_gemini_api_key: str,
        mock_genai_module: MagicMock,
    ) -> None:
        """認証エラーが正しく変換されること"""
        with patch("apps.api.llm.gemini.GENAI_AVAILABLE", True):
            with patch("apps.api.llm.gemini.genai", mock_genai_module):
                with patch("apps.api.llm.gemini.types", mock_genai_module.types):
                    client = GeminiClient(api_key=mock_gemini_api_key)

                    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
                        mock_thread.side_effect = Exception("401 authentication failed")

                        with pytest.raises(LLMAuthenticationError) as exc_info:
                            await client.generate(
                                messages=[{"role": "user", "content": "Hello"}],
                                system_prompt="Test",
                            )

                        assert exc_info.value.category == ErrorCategory.NON_RETRYABLE
                        assert not exc_info.value.is_retryable()

    @pytest.mark.asyncio
    async def test_rate_limit_error(
        self,
        mock_gemini_api_key: str,
        mock_genai_module: MagicMock,
    ) -> None:
        """レート制限エラーが正しく変換されること"""
        with patch("apps.api.llm.gemini.GENAI_AVAILABLE", True):
            with patch("apps.api.llm.gemini.genai", mock_genai_module):
                with patch("apps.api.llm.gemini.types", mock_genai_module.types):
                    client = GeminiClient(api_key=mock_gemini_api_key)

                    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
                        # 3回ともレート制限エラー
                        mock_thread.side_effect = Exception("429 rate limit exceeded")

                        with pytest.raises(LLMRateLimitError) as exc_info:
                            await client.generate(
                                messages=[{"role": "user", "content": "Hello"}],
                                system_prompt="Test",
                            )

                        assert exc_info.value.category == ErrorCategory.RETRYABLE
                        assert exc_info.value.is_retryable()


class TestErrorCategory:
    """ErrorCategoryのテスト"""

    def test_retryable(self) -> None:
        """RETRYABLEカテゴリが正しいこと"""
        assert ErrorCategory.RETRYABLE == "retryable"

    def test_non_retryable(self) -> None:
        """NON_RETRYABLEカテゴリが正しいこと"""
        assert ErrorCategory.NON_RETRYABLE == "non_retryable"

    def test_validation_fail(self) -> None:
        """VALIDATION_FAILカテゴリが正しいこと"""
        assert ErrorCategory.VALIDATION_FAIL == "validation_fail"


class TestNoFallback:
    """フォールバック禁止のテスト

    重要: モデル自動切替や別プロバイダへのフォールバックが存在しないことを確認
    """

    def test_no_fallback_model_in_code(self) -> None:
        """コードに'fallback'モデルの記述がないこと"""
        import apps.api.llm.gemini as gemini_module

        source = open(gemini_module.__file__, "r").read()

        # フォールバック関連のパターンをチェック
        assert "fallback_model" not in source.lower()
        assert "fallback_provider" not in source.lower()
        assert "auto_switch" not in source.lower()

    def test_single_provider(
        self, mock_gemini_api_key: str, mock_genai_module: MagicMock
    ) -> None:
        """単一プロバイダーのみ使用していること"""
        with patch("apps.api.llm.gemini.GENAI_AVAILABLE", True):
            with patch("apps.api.llm.gemini.genai", mock_genai_module):
                client = GeminiClient(api_key=mock_gemini_api_key)
                assert client.provider_name == "gemini"
                # 他のプロバイダーへのアクセス手段がないことを確認
                assert not hasattr(client, "fallback_client")
                assert not hasattr(client, "secondary_provider")
