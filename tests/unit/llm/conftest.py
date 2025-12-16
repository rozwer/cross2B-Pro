"""LLMテスト用のフィクスチャ"""

import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_gemini_api_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """テスト用のGemini APIキーを設定"""
    api_key = "test-api-key-12345"
    monkeypatch.setenv("GEMINI_API_KEY", api_key)
    return api_key


@pytest.fixture
def mock_genai_response() -> MagicMock:
    """Gemini APIレスポンスのモック"""
    response = MagicMock()
    response.text = "Hello! I'm a helpful assistant."

    # candidates
    candidate = MagicMock()
    candidate.finish_reason = "STOP"
    candidate.grounding_metadata = None
    response.candidates = [candidate]

    # usage_metadata
    usage = MagicMock()
    usage.prompt_token_count = 10
    usage.candidates_token_count = 20
    response.usage_metadata = usage

    return response


@pytest.fixture
def mock_genai_json_response() -> MagicMock:
    """Gemini API JSONレスポンスのモック"""
    response = MagicMock()
    response.text = '{"name": "test", "value": 123}'

    candidate = MagicMock()
    candidate.finish_reason = "STOP"
    candidate.grounding_metadata = None
    response.candidates = [candidate]

    usage = MagicMock()
    usage.prompt_token_count = 15
    usage.candidates_token_count = 25
    response.usage_metadata = usage

    return response


@pytest.fixture
def mock_genai_grounding_response() -> MagicMock:
    """Grounding付きGemini APIレスポンスのモック"""
    response = MagicMock()
    response.text = "Based on my search, here is the information."

    # candidates with grounding
    candidate = MagicMock()
    candidate.finish_reason = "STOP"

    grounding = MagicMock()
    grounding.search_entry_point = "test search"

    chunk = MagicMock()
    chunk.web = MagicMock()
    chunk.web.uri = "https://example.com"
    chunk.web.title = "Example"
    grounding.grounding_chunks = [chunk]

    candidate.grounding_metadata = grounding
    response.candidates = [candidate]

    usage = MagicMock()
    usage.prompt_token_count = 10
    usage.candidates_token_count = 30
    response.usage_metadata = usage

    return response


@pytest.fixture
def mock_genai_client(mock_genai_response: MagicMock) -> MagicMock:
    """Geminiクライアントのモック"""
    client = MagicMock()
    client.models.generate_content = MagicMock(return_value=mock_genai_response)
    return client


@pytest.fixture
def mock_genai_module(mock_genai_client: MagicMock) -> Any:
    """google.genai モジュールのモック"""
    with patch.dict("sys.modules", {"google": MagicMock(), "google.genai": MagicMock()}):
        mock_genai = MagicMock()
        mock_genai.Client = MagicMock(return_value=mock_genai_client)
        mock_genai.types = MagicMock()
        mock_genai.types.Content = MagicMock()
        mock_genai.types.Part = MagicMock()
        mock_genai.types.GenerateContentConfig = MagicMock()
        mock_genai.types.Tool = MagicMock()
        mock_genai.types.GoogleSearch = MagicMock()
        yield mock_genai
