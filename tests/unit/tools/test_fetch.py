"""
取得ツールのテスト
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from apps.api.tools import ToolRegistry
from apps.api.tools.base import ErrorCategory


class TestPageFetchTool:
    """page_fetch ツールのテスト"""

    @pytest.mark.asyncio
    async def test_execute_with_empty_url(self):
        """空のURLでの実行"""
        tool = ToolRegistry.get("page_fetch")
        result = await tool.execute(url="")

        assert not result.success
        assert result.error_category == ErrorCategory.VALIDATION_FAIL.value
        assert "required" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_execute_with_invalid_url(self):
        """無効なURLでの実行"""
        tool = ToolRegistry.get("page_fetch")
        result = await tool.execute(url="not-a-valid-url")

        assert not result.success
        assert result.error_category == ErrorCategory.VALIDATION_FAIL.value
        assert "Invalid URL" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_success(self, mock_html_content):
        """正常な実行"""
        tool = ToolRegistry.get("page_fetch")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html_content
        mock_response.url = "https://example.com/test"
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await tool.execute(url="https://example.com/test")

            assert result.success
            assert result.data is not None
            assert result.data["title"] == "テストページ"
            assert result.data["h1"] == "メインタイトル"
            assert "SEO対策" in result.data["body_text"]
            assert result.evidence is not None
            assert len(result.evidence) == 1

    @pytest.mark.asyncio
    async def test_execute_with_links(self, mock_html_content):
        """リンク抽出付きの実行"""
        html_with_links = mock_html_content.replace(
            "</main>",
            '<a href="https://example.com/link1">Link 1</a>'
            '<a href="/relative-link">Link 2</a></main>',
        )

        tool = ToolRegistry.get("page_fetch")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html_with_links
        mock_response.url = "https://example.com/test"
        mock_response.headers = {"content-type": "text/html"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await tool.execute(
                url="https://example.com/test", extract_links=True
            )

            assert result.success
            assert "links" in result.data
            assert len(result.data["links"]) > 0

    @pytest.mark.asyncio
    async def test_execute_not_found(self):
        """404エラー"""
        tool = ToolRegistry.get("page_fetch")

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await tool.execute(url="https://example.com/notfound")

            assert not result.success
            assert result.error_category == ErrorCategory.NON_RETRYABLE.value

    @pytest.mark.asyncio
    async def test_execute_non_html_content(self):
        """非HTMLコンテンツ"""
        tool = ToolRegistry.get("page_fetch")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await tool.execute(url="https://example.com/api")

            assert not result.success
            assert result.error_category == ErrorCategory.VALIDATION_FAIL.value
            assert "Not HTML" in result.error_message


class TestPdfExtractTool:
    """pdf_extract ツールのテスト"""

    @pytest.mark.asyncio
    async def test_execute_without_path_or_url(self):
        """パスもURLも指定なし"""
        tool = ToolRegistry.get("pdf_extract")
        result = await tool.execute()

        assert not result.success
        assert result.error_category == ErrorCategory.VALIDATION_FAIL.value
        assert "required" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_execute_file_not_found(self):
        """ファイルが存在しない"""
        tool = ToolRegistry.get("pdf_extract")
        result = await tool.execute(pdf_path="/nonexistent/path/file.pdf")

        assert not result.success
        assert result.error_category == ErrorCategory.NON_RETRYABLE.value
        assert "not found" in result.error_message.lower()


class TestPrimaryCollectorTool:
    """primary_collector ツールのテスト"""

    @pytest.mark.asyncio
    async def test_execute_with_empty_query(self):
        """空のクエリ"""
        tool = ToolRegistry.get("primary_collector")
        result = await tool.execute(query="")

        assert not result.success
        assert result.error_category == ErrorCategory.VALIDATION_FAIL.value

    @pytest.mark.asyncio
    async def test_execute_serp_failure(self):
        """SERP取得失敗時"""
        tool = ToolRegistry.get("primary_collector")

        # serp_fetchをモック
        mock_serp_result = MagicMock()
        mock_serp_result.success = False
        mock_serp_result.error_category = ErrorCategory.NON_RETRYABLE.value
        mock_serp_result.error_message = "API key invalid"

        with patch.object(ToolRegistry, "get") as mock_get:
            mock_serp_tool = MagicMock()
            mock_serp_tool.execute = AsyncMock(return_value=mock_serp_result)
            mock_get.return_value = mock_serp_tool

            result = await tool.execute(query="test query")

            assert not result.success
            assert "SERP fetch failed" in result.error_message
