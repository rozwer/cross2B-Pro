"""OpenAI クライアントのユニットテスト."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import (
    APIConnectionError,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
)

from apps.api.llm import ErrorCategory, LLMError, LLMValidationError, OpenAIClient


class TestOpenAIClientInit:
    """初期化のテスト."""

    def test_init_with_env_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """環境変数からAPIキーを取得できる."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        client = OpenAIClient()
        assert client.model == "gpt-4o"
        assert client.max_retries == 3

    def test_init_with_explicit_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """明示的にAPIキーを指定できる."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        client = OpenAIClient(api_key="explicit-key")
        assert client.model == "gpt-4o"

    def test_init_with_custom_model(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """カスタムモデルを指定できる."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        client = OpenAIClient(model="gpt-4-turbo")
        assert client.model == "gpt-4-turbo"

    def test_init_without_key_raises_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """APIキーが未設定の場合はエラー."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(LLMError) as exc_info:
            OpenAIClient()
        assert exc_info.value.category == ErrorCategory.NON_RETRYABLE
        assert "OPENAI_API_KEY is not set" in exc_info.value.message


class TestOpenAIClientGenerate:
    """generate メソッドのテスト."""

    @pytest.fixture
    def client(self, monkeypatch: pytest.MonkeyPatch) -> OpenAIClient:
        """テスト用クライアント."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        return OpenAIClient()

    @pytest.fixture
    def mock_response(self) -> MagicMock:
        """モックレスポンス."""
        response = MagicMock()
        response.choices = [
            MagicMock(
                message=MagicMock(content="Generated content"),
                finish_reason="stop",
            )
        ]
        response.usage = MagicMock(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
        )
        response.model = "gpt-4o"
        return response

    @pytest.mark.asyncio
    async def test_generate_success(
        self, client: OpenAIClient, mock_response: MagicMock
    ) -> None:
        """正常に生成できる."""
        with patch.object(
            client.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_response

            result = await client.generate(
                messages=[{"role": "user", "content": "Hello"}],
                system_prompt="You are helpful.",
            )

            assert result.content == "Generated content"
            assert result.token_usage.input == 10
            assert result.token_usage.output == 20
            assert result.model == "gpt-4o"
            assert result.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_generate_rate_limit_retry(
        self, client: OpenAIClient, mock_response: MagicMock
    ) -> None:
        """レート制限エラーでリトライする."""
        with patch.object(
            client.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = [
                RateLimitError(
                    message="Rate limit exceeded",
                    response=MagicMock(status_code=429),
                    body=None,
                ),
                mock_response,
            ]

            result = await client.generate(
                messages=[{"role": "user", "content": "Hello"}],
                system_prompt="You are helpful.",
            )

            assert result.content == "Generated content"
            assert mock_create.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_rate_limit_max_retries(
        self, client: OpenAIClient
    ) -> None:
        """リトライ上限に達したらエラー."""
        with patch.object(
            client.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = RateLimitError(
                message="Rate limit exceeded",
                response=MagicMock(status_code=429),
                body=None,
            )

            with pytest.raises(LLMError) as exc_info:
                await client.generate(
                    messages=[{"role": "user", "content": "Hello"}],
                    system_prompt="You are helpful.",
                )

            assert exc_info.value.category == ErrorCategory.RETRYABLE
            assert mock_create.call_count == 3

    @pytest.mark.asyncio
    async def test_generate_auth_error_no_retry(
        self, client: OpenAIClient
    ) -> None:
        """認証エラーはリトライしない."""
        with patch.object(
            client.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = AuthenticationError(
                message="Invalid API key",
                response=MagicMock(status_code=401),
                body=None,
            )

            with pytest.raises(LLMError) as exc_info:
                await client.generate(
                    messages=[{"role": "user", "content": "Hello"}],
                    system_prompt="You are helpful.",
                )

            assert exc_info.value.category == ErrorCategory.NON_RETRYABLE
            assert mock_create.call_count == 1

    @pytest.mark.asyncio
    async def test_generate_bad_request_no_retry(
        self, client: OpenAIClient
    ) -> None:
        """不正リクエストはリトライしない."""
        with patch.object(
            client.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = BadRequestError(
                message="Invalid request",
                response=MagicMock(status_code=400),
                body=None,
            )

            with pytest.raises(LLMError) as exc_info:
                await client.generate(
                    messages=[{"role": "user", "content": "Hello"}],
                    system_prompt="You are helpful.",
                )

            assert exc_info.value.category == ErrorCategory.NON_RETRYABLE
            assert mock_create.call_count == 1

    @pytest.mark.asyncio
    async def test_generate_connection_error_retry(
        self, client: OpenAIClient, mock_response: MagicMock
    ) -> None:
        """接続エラーでリトライする."""
        with patch.object(
            client.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = [
                APIConnectionError(request=MagicMock()),
                mock_response,
            ]

            result = await client.generate(
                messages=[{"role": "user", "content": "Hello"}],
                system_prompt="You are helpful.",
            )

            assert result.content == "Generated content"
            assert mock_create.call_count == 2


class TestOpenAIClientGenerateJson:
    """generate_json メソッドのテスト."""

    @pytest.fixture
    def client(self, monkeypatch: pytest.MonkeyPatch) -> OpenAIClient:
        """テスト用クライアント."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        return OpenAIClient()

    @pytest.fixture
    def mock_json_response(self) -> MagicMock:
        """モックJSONレスポンス."""
        response = MagicMock()
        response.choices = [
            MagicMock(
                message=MagicMock(content='{"key": "value", "number": 42}'),
                finish_reason="stop",
            )
        ]
        response.usage = MagicMock(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
        )
        response.model = "gpt-4o"
        return response

    @pytest.mark.asyncio
    async def test_generate_json_success(
        self, client: OpenAIClient, mock_json_response: MagicMock
    ) -> None:
        """正常にJSON生成できる."""
        with patch.object(
            client.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = mock_json_response

            result = await client.generate_json(
                messages=[{"role": "user", "content": "Give me JSON"}],
                system_prompt="You are helpful.",
                schema={"type": "object"},
            )

            assert result == {"key": "value", "number": 42}

            call_args = mock_create.call_args
            assert call_args.kwargs["response_format"] == {"type": "json_object"}

    @pytest.mark.asyncio
    async def test_generate_json_invalid_json(
        self, client: OpenAIClient
    ) -> None:
        """無効なJSONの場合はValidationError."""
        response = MagicMock()
        response.choices = [
            MagicMock(
                message=MagicMock(content="not valid json"),
                finish_reason="stop",
            )
        ]
        response.usage = MagicMock(total_tokens=30)

        with patch.object(
            client.client.chat.completions, "create", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = response

            with pytest.raises(LLMValidationError) as exc_info:
                await client.generate_json(
                    messages=[{"role": "user", "content": "Give me JSON"}],
                    system_prompt="You are helpful.",
                    schema={"type": "object"},
                )

            assert exc_info.value.category == ErrorCategory.VALIDATION_FAIL


class TestErrorClassification:
    """エラー分類のテスト."""

    def test_llm_error_is_retryable(self) -> None:
        """RETRYABLEエラーの判定."""
        error = LLMError(
            message="test",
            category=ErrorCategory.RETRYABLE,
            provider="openai",
        )
        assert error.is_retryable() is True

    def test_llm_error_not_retryable(self) -> None:
        """NON_RETRYABLEエラーの判定."""
        error = LLMError(
            message="test",
            category=ErrorCategory.NON_RETRYABLE,
            provider="openai",
        )
        assert error.is_retryable() is False

    def test_validation_error_not_retryable(self) -> None:
        """VALIDATION_FAILエラーの判定."""
        error = LLMValidationError(
            message="test",
            provider="openai",
        )
        assert error.is_retryable() is False
        assert error.category == ErrorCategory.VALIDATION_FAIL


class TestNoFallback:
    """フォールバック禁止の検証テスト."""

    def test_no_fallback_model_in_code(self) -> None:
        """コードに fallback model の記述がないことを確認."""
        import inspect
        from apps.api.llm import openai

        source = inspect.getsource(openai)
        assert "fallback" not in source.lower(), "Fallback logic detected in code"

    def test_no_alternative_provider_in_code(self) -> None:
        """別プロバイダへの切替コードがないことを確認."""
        import inspect
        from apps.api.llm import openai

        source = inspect.getsource(openai)
        forbidden = ["gemini", "anthropic", "claude"]
        for word in forbidden:
            assert word not in source.lower(), f"Alternative provider '{word}' detected"
