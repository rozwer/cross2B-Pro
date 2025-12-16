"""
検索ツールのテスト
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from apps.api.tools import ToolRegistry, ToolResult
from apps.api.tools.base import ErrorCategory


class TestSerpFetchTool:
    """serp_fetch ツールのテスト"""

    @pytest.mark.asyncio
    async def test_execute_without_api_key(self):
        """APIキーなしでの実行"""
        with patch.dict(os.environ, {"SERP_API_KEY": ""}, clear=False):
            # ツールを再取得（環境変数を反映）
            tool = ToolRegistry.get("serp_fetch")
            tool.api_key = ""  # 明示的に空にする

            result = await tool.execute(query="SEO対策")

            assert not result.success
            assert result.error_category == ErrorCategory.NON_RETRYABLE.value
            assert "SERP_API_KEY" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_with_empty_query(self):
        """空のクエリでの実行"""
        tool = ToolRegistry.get("serp_fetch")
        result = await tool.execute(query="")

        assert not result.success
        assert result.error_category == ErrorCategory.VALIDATION_FAIL.value
        assert "required" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_serp_response):
        """正常な実行"""
        tool = ToolRegistry.get("serp_fetch")
        tool.api_key = "test_api_key"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_serp_response

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await tool.execute(query="SEO対策", num_results=10)

            assert result.success
            assert result.data is not None
            assert "results" in result.data
            assert len(result.data["results"]) == 3
            assert result.evidence is not None
            assert len(result.evidence) == 3

    @pytest.mark.asyncio
    async def test_execute_rate_limited(self):
        """レート制限時の動作"""
        tool = ToolRegistry.get("serp_fetch")
        tool.api_key = "test_api_key"

        mock_response = MagicMock()
        mock_response.status_code = 429

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await tool.execute(query="SEO対策")

            assert not result.success
            assert result.error_category == ErrorCategory.RETRYABLE.value


class TestSearchVolumeTool:
    """search_volume ツールのテスト（モック）"""

    @pytest.mark.asyncio
    async def test_execute_mock_mode_known_keyword(self):
        """モックモード - 既知のキーワード"""
        with patch.dict(os.environ, {"USE_MOCK_GOOGLE_ADS": "true"}):
            tool = ToolRegistry.get("search_volume")
            tool.use_mock = True

            result = await tool.execute(keyword="SEO対策")

            assert result.success
            assert result.is_mock is True
            assert result.data is not None
            assert result.data["keyword"] == "SEO対策"
            assert result.data["volume"] == 12000  # モックデータの値
            assert result.data["source"] == "mock"

    @pytest.mark.asyncio
    async def test_execute_mock_mode_unknown_keyword(self):
        """モックモード - 未知のキーワード（推定値）"""
        with patch.dict(os.environ, {"USE_MOCK_GOOGLE_ADS": "true"}):
            tool = ToolRegistry.get("search_volume")
            tool.use_mock = True

            result = await tool.execute(keyword="未知のキーワード")

            assert result.success
            assert result.is_mock is True
            assert result.data["volume"] > 0  # 推定値が返される

    @pytest.mark.asyncio
    async def test_execute_empty_keyword(self):
        """空のキーワード"""
        tool = ToolRegistry.get("search_volume")
        result = await tool.execute(keyword="")

        assert not result.success
        assert result.error_category == ErrorCategory.VALIDATION_FAIL.value


class TestRelatedKeywordsTool:
    """related_keywords ツールのテスト（モック）"""

    @pytest.mark.asyncio
    async def test_execute_mock_mode_known_keyword(self):
        """モックモード - 既知のキーワード"""
        with patch.dict(os.environ, {"USE_MOCK_GOOGLE_ADS": "true"}):
            tool = ToolRegistry.get("related_keywords")
            tool.use_mock = True

            result = await tool.execute(keyword="SEO対策", limit=5)

            assert result.success
            assert result.is_mock is True
            assert result.data is not None
            assert result.data["keyword"] == "SEO対策"
            assert "related" in result.data
            assert len(result.data["related"]) == 5
            assert result.data["source"] == "mock"

    @pytest.mark.asyncio
    async def test_execute_mock_mode_unknown_keyword(self):
        """モックモード - 未知のキーワード（パターン生成）"""
        with patch.dict(os.environ, {"USE_MOCK_GOOGLE_ADS": "true"}):
            tool = ToolRegistry.get("related_keywords")
            tool.use_mock = True

            result = await tool.execute(keyword="未知のトピック")

            assert result.success
            assert result.is_mock is True
            assert "related" in result.data
            # パターン生成されたキーワードを確認
            assert any("とは" in kw for kw in result.data["related"])

    @pytest.mark.asyncio
    async def test_execute_empty_keyword(self):
        """空のキーワード"""
        tool = ToolRegistry.get("related_keywords")
        result = await tool.execute(keyword="")

        assert not result.success
        assert result.error_category == ErrorCategory.VALIDATION_FAIL.value
