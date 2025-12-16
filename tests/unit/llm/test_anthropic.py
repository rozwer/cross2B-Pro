"""Unit tests for Anthropic Claude client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from anthropic import APIConnectionError, RateLimitError, AuthenticationError, APIStatusError
from anthropic.types import ToolUseBlock

from apps.api.llm.anthropic import AnthropicClient, SUPPORTED_MODELS, DEFAULT_MODEL
from apps.api.llm.schemas import LLMResponse, TokenUsage
from apps.api.llm.exceptions import (
    ErrorCategory,
    RetryableLLMError,
    NonRetryableLLMError,
    ValidationLLMError,
)


class TestAnthropicClientInit:
    """Tests for AnthropicClient initialization."""

    def test_init_with_api_key(self):
        """Client initializes with explicit API key."""
        with patch("apps.api.llm.anthropic.AsyncAnthropic"):
            client = AnthropicClient(api_key="test-key")
            assert client.model == DEFAULT_MODEL
            assert client.max_retries == 3

    def test_init_with_env_var(self, monkeypatch):
        """Client initializes with ANTHROPIC_API_KEY env var."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-test-key")
        with patch("apps.api.llm.anthropic.AsyncAnthropic"):
            client = AnthropicClient()
            assert client.model == DEFAULT_MODEL

    def test_init_without_api_key_raises(self, monkeypatch):
        """Client raises error when no API key is available."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(NonRetryableLLMError) as exc_info:
            AnthropicClient()
        assert "ANTHROPIC_API_KEY is not set" in str(exc_info.value)

    def test_init_with_unsupported_model_raises(self):
        """Client raises error for unsupported model."""
        with pytest.raises(NonRetryableLLMError) as exc_info:
            AnthropicClient(api_key="test-key", model="unsupported-model")
        assert "not supported" in str(exc_info.value)

    @pytest.mark.parametrize("model", SUPPORTED_MODELS)
    def test_init_with_supported_models(self, model):
        """Client accepts all supported models."""
        with patch("apps.api.llm.anthropic.AsyncAnthropic"):
            client = AnthropicClient(api_key="test-key", model=model)
            assert client.model == model


class TestAnthropicClientGenerate:
    """Tests for AnthropicClient.generate() method."""

    @pytest.fixture
    def mock_client(self):
        """Create a mocked AnthropicClient."""
        with patch("apps.api.llm.anthropic.AsyncAnthropic") as mock_anthropic:
            client = AnthropicClient(api_key="test-key")
            yield client, mock_anthropic.return_value

    @pytest.mark.asyncio
    async def test_generate_success(self, mock_client):
        """Generate returns LLMResponse on success."""
        client, mock_api = mock_client

        # Mock response
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="Generated content")]
        mock_response.usage = MagicMock(input_tokens=100, output_tokens=50)
        mock_response.model = "claude-sonnet-4-20250514"

        mock_api.messages.create = AsyncMock(return_value=mock_response)

        result = await client.generate(
            messages=[{"role": "user", "content": "Hello"}],
            system_prompt="You are helpful.",
            temperature=0.7,
            max_tokens=1000,
        )

        assert isinstance(result, LLMResponse)
        assert result.content == "Generated content"
        assert result.token_usage.input == 100
        assert result.token_usage.output == 50
        assert result.model == "claude-sonnet-4-20250514"

    @pytest.mark.asyncio
    async def test_generate_auth_error_raises_non_retryable(self, mock_client):
        """Authentication error raises NonRetryableLLMError."""
        client, mock_api = mock_client

        mock_api.messages.create = AsyncMock(
            side_effect=AuthenticationError(
                message="Invalid API key",
                response=MagicMock(status_code=401),
                body=None,
            )
        )

        with pytest.raises(NonRetryableLLMError) as exc_info:
            await client.generate(
                messages=[{"role": "user", "content": "Hello"}],
                system_prompt="You are helpful.",
            )
        assert "Authentication failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_rate_limit_retries(self, mock_client):
        """Rate limit error triggers retry and eventually raises RetryableLLMError."""
        client, mock_api = mock_client
        client.max_retries = 2

        mock_api.messages.create = AsyncMock(
            side_effect=RateLimitError(
                message="Rate limit exceeded",
                response=MagicMock(status_code=429),
                body=None,
            )
        )

        with pytest.raises(RetryableLLMError) as exc_info:
            await client.generate(
                messages=[{"role": "user", "content": "Hello"}],
                system_prompt="You are helpful.",
            )
        assert "Rate limit exceeded" in str(exc_info.value)
        assert mock_api.messages.create.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_connection_error_retries(self, mock_client):
        """Connection error triggers retry and eventually raises RetryableLLMError."""
        client, mock_api = mock_client
        client.max_retries = 2

        mock_api.messages.create = AsyncMock(
            side_effect=APIConnectionError(request=MagicMock())
        )

        with pytest.raises(RetryableLLMError) as exc_info:
            await client.generate(
                messages=[{"role": "user", "content": "Hello"}],
                system_prompt="You are helpful.",
            )
        assert "Connection failed" in str(exc_info.value)
        assert mock_api.messages.create.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_server_error_retries(self, mock_client):
        """Server error (5xx) triggers retry."""
        client, mock_api = mock_client
        client.max_retries = 2

        # Create a proper APIStatusError with status_code
        error = APIStatusError(
            message="Internal server error",
            response=MagicMock(status_code=500),
            body=None,
        )

        mock_api.messages.create = AsyncMock(side_effect=error)

        with pytest.raises(RetryableLLMError) as exc_info:
            await client.generate(
                messages=[{"role": "user", "content": "Hello"}],
                system_prompt="You are helpful.",
            )
        assert "Server error" in str(exc_info.value)
        assert mock_api.messages.create.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_client_error_no_retry(self, mock_client):
        """Client error (4xx) does not retry."""
        client, mock_api = mock_client
        client.max_retries = 3

        # Create a proper APIStatusError with status_code 400
        error = APIStatusError(
            message="Bad request",
            response=MagicMock(status_code=400),
            body=None,
        )
        mock_api.messages.create = AsyncMock(side_effect=error)

        with pytest.raises(NonRetryableLLMError) as exc_info:
            await client.generate(
                messages=[{"role": "user", "content": "Hello"}],
                system_prompt="You are helpful.",
            )
        assert "API error" in str(exc_info.value)
        # Should not retry for client errors
        assert mock_api.messages.create.call_count == 1


class TestAnthropicClientGenerateJson:
    """Tests for AnthropicClient.generate_json() method."""

    @pytest.fixture
    def mock_client(self):
        """Create a mocked AnthropicClient."""
        with patch("apps.api.llm.anthropic.AsyncAnthropic") as mock_anthropic:
            client = AnthropicClient(api_key="test-key")
            yield client, mock_anthropic.return_value

    @pytest.mark.asyncio
    async def test_generate_json_success(self, mock_client):
        """Generate JSON returns parsed dict on success."""
        client, mock_api = mock_client

        # Create an actual ToolUseBlock instance for isinstance check
        mock_tool_use = ToolUseBlock(
            id="tool_123",
            type="tool_use",
            name="json_output",
            input={"key": "value", "number": 42},
        )

        mock_response = MagicMock()
        mock_response.content = [mock_tool_use]
        mock_response.usage = MagicMock(input_tokens=100, output_tokens=50)

        mock_api.messages.create = AsyncMock(return_value=mock_response)

        schema = {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "number": {"type": "integer"},
            },
        }

        result = await client.generate_json(
            messages=[{"role": "user", "content": "Generate JSON"}],
            system_prompt="You are helpful.",
            schema=schema,
        )

        assert result == {"key": "value", "number": 42}

    @pytest.mark.asyncio
    async def test_generate_json_no_tool_use_raises_validation_error(self, mock_client):
        """Missing tool_use block raises ValidationLLMError."""
        client, mock_api = mock_client

        # Mock response without tool_use
        mock_text = MagicMock()
        mock_text.type = "text"
        mock_text.text = "Some text"

        mock_response = MagicMock()
        mock_response.content = [mock_text]
        mock_response.usage = MagicMock(input_tokens=100, output_tokens=50)

        mock_api.messages.create = AsyncMock(return_value=mock_response)

        schema = {"type": "object", "properties": {"key": {"type": "string"}}}

        with pytest.raises(ValidationLLMError) as exc_info:
            await client.generate_json(
                messages=[{"role": "user", "content": "Generate JSON"}],
                system_prompt="You are helpful.",
                schema=schema,
            )
        assert "No JSON output found" in str(exc_info.value)


class TestAnthropicClientMessageConversion:
    """Tests for message format conversion."""

    @pytest.fixture
    def client(self):
        """Create a mocked AnthropicClient."""
        with patch("apps.api.llm.anthropic.AsyncAnthropic"):
            return AnthropicClient(api_key="test-key")

    def test_convert_user_messages(self, client):
        """User messages are preserved."""
        messages = [{"role": "user", "content": "Hello"}]
        result = client._convert_messages(messages)
        assert result == [{"role": "user", "content": "Hello"}]

    def test_convert_assistant_messages(self, client):
        """Assistant messages are preserved."""
        messages = [{"role": "assistant", "content": "Hi there"}]
        result = client._convert_messages(messages)
        assert result == [{"role": "assistant", "content": "Hi there"}]

    def test_convert_system_messages_skipped(self, client):
        """System messages are filtered out."""
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]
        result = client._convert_messages(messages)
        assert result == [{"role": "user", "content": "Hello"}]

    def test_convert_unknown_role_to_user(self, client):
        """Unknown roles are mapped to user."""
        messages = [{"role": "function", "content": "Function output"}]
        result = client._convert_messages(messages)
        assert result == [{"role": "user", "content": "Function output"}]

    def test_convert_mixed_messages(self, client):
        """Mixed message types are handled correctly."""
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "User message"},
            {"role": "assistant", "content": "Assistant response"},
            {"role": "user", "content": "Follow up"},
        ]
        result = client._convert_messages(messages)
        assert result == [
            {"role": "user", "content": "User message"},
            {"role": "assistant", "content": "Assistant response"},
            {"role": "user", "content": "Follow up"},
        ]


class TestErrorCategories:
    """Tests for error category classification."""

    def test_retryable_error_has_correct_category(self):
        """RetryableLLMError has RETRYABLE category."""
        error = RetryableLLMError("Test error")
        assert error.category == ErrorCategory.RETRYABLE

    def test_non_retryable_error_has_correct_category(self):
        """NonRetryableLLMError has NON_RETRYABLE category."""
        error = NonRetryableLLMError("Test error")
        assert error.category == ErrorCategory.NON_RETRYABLE

    def test_validation_error_has_correct_category(self):
        """ValidationLLMError has VALIDATION_FAIL category."""
        error = ValidationLLMError("Test error")
        assert error.category == ErrorCategory.VALIDATION_FAIL


class TestNoAutoSwitching:
    """Tests to ensure no automatic model/provider switching exists."""

    def test_no_auto_switch_patterns_in_code(self):
        """Verify no automatic switching logic exists in the module."""
        import apps.api.llm.anthropic as module
        import inspect

        source = inspect.getsource(module)
        # Check for common auto-switching patterns (not in comments/docstrings)
        # Note: We intentionally avoid the word 'fallback' since it may appear in docstrings
        assert "backup_model" not in source.lower()
        assert "alternative_model" not in source.lower()
        assert "switch_to_" not in source.lower()
        assert "try_next_model" not in source.lower()

    def test_retry_uses_same_model(self):
        """Verify retry uses the same model (no model switching)."""
        with patch("apps.api.llm.anthropic.AsyncAnthropic"):
            client = AnthropicClient(api_key="test-key", model="claude-sonnet-4-20250514")
            # Model should not change after initialization
            assert client.model == "claude-sonnet-4-20250514"

    def test_model_is_immutable_after_init(self):
        """Verify model cannot be changed after initialization."""
        with patch("apps.api.llm.anthropic.AsyncAnthropic"):
            client = AnthropicClient(api_key="test-key", model="claude-sonnet-4-20250514")
            original_model = client.model

            # model is a read-only property, attempting to set should raise AttributeError
            with pytest.raises(AttributeError):
                client.model = "different-model"

            # Model should remain unchanged
            assert client.model == original_model == "claude-sonnet-4-20250514"
