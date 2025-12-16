"""
検証ツールのテスト
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from apps.api.tools import ToolRegistry
from apps.api.tools.base import ErrorCategory


class TestUrlVerifyTool:
    """url_verify ツールのテスト"""

    @pytest.mark.asyncio
    async def test_execute_with_empty_url(self):
        """空のURLでの実行"""
        tool = ToolRegistry.get("url_verify")
        result = await tool.execute(url="")

        assert not result.success
        assert result.error_category == ErrorCategory.VALIDATION_FAIL.value
        assert "required" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_execute_with_invalid_url_format(self):
        """無効なURL形式"""
        tool = ToolRegistry.get("url_verify")
        result = await tool.execute(url="not-a-url")

        assert not result.success
        assert result.error_category == ErrorCategory.VALIDATION_FAIL.value
        assert "Invalid URL" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_with_unsupported_scheme(self):
        """サポートされていないスキーム"""
        tool = ToolRegistry.get("url_verify")
        result = await tool.execute(url="ftp://example.com/file")

        assert not result.success
        assert result.error_category == ErrorCategory.VALIDATION_FAIL.value
        assert "Unsupported scheme" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_success_200(self):
        """正常なURL（200 OK）"""
        tool = ToolRegistry.get("url_verify")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = "https://example.com/page"
        mock_response.request.method = "HEAD"
        mock_response.headers = {
            "content-type": "text/html",
            "content-length": "12345",
            "server": "nginx",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.head = AsyncMock(
                return_value=mock_response
            )

            result = await tool.execute(url="https://example.com/page")

            assert result.success
            assert result.data["status_code"] == 200
            assert result.data["is_accessible"] is True
            assert result.data["is_redirect"] is False
            assert result.evidence is not None
            assert len(result.evidence) == 1

    @pytest.mark.asyncio
    async def test_execute_with_redirect(self):
        """リダイレクトあり"""
        tool = ToolRegistry.get("url_verify")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = "https://www.example.com/new-page"  # リダイレクト後
        mock_response.request.method = "HEAD"
        mock_response.headers = {"content-type": "text/html"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.head = AsyncMock(
                return_value=mock_response
            )

            result = await tool.execute(url="https://example.com/old-page")

            assert result.success
            assert result.data["url"] == "https://example.com/old-page"
            assert result.data["final_url"] == "https://www.example.com/new-page"
            assert result.data["is_redirect"] is True

    @pytest.mark.asyncio
    async def test_execute_with_permanent_redirect(self):
        """301永続リダイレクト"""
        tool = ToolRegistry.get("url_verify")

        mock_response = MagicMock()
        mock_response.status_code = 301
        mock_response.url = "https://example.com/page"
        mock_response.request.method = "HEAD"
        mock_response.headers = {}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.head = AsyncMock(
                return_value=mock_response
            )

            result = await tool.execute(
                url="https://example.com/page", follow_redirects=False
            )

            assert result.success
            assert result.data["status_code"] == 301
            assert result.data["is_permanent_redirect"] is True
            assert result.data["is_temporary_redirect"] is False

    @pytest.mark.asyncio
    async def test_execute_404_not_found(self):
        """404エラー"""
        tool = ToolRegistry.get("url_verify")

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.url = "https://example.com/notfound"
        mock_response.request.method = "HEAD"
        mock_response.headers = {}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.head = AsyncMock(
                return_value=mock_response
            )

            result = await tool.execute(url="https://example.com/notfound")

            assert result.success  # 確認自体は成功
            assert result.data["status_code"] == 404
            assert result.data["is_accessible"] is False

    @pytest.mark.asyncio
    async def test_execute_with_meta_extraction(self):
        """メタ情報抽出（GETリクエスト時）"""
        tool = ToolRegistry.get("url_verify")

        html_content = """
        <html>
        <head>
            <title>テストページ</title>
            <link rel="canonical" href="https://example.com/canonical-url">
        </head>
        <body></body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = "https://example.com/page"
        mock_response.request.method = "GET"
        mock_response.text = html_content
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}

        import httpx

        with patch("httpx.AsyncClient") as mock_client:
            # HEADリクエストが失敗してGETにフォールバック
            mock_client.return_value.__aenter__.return_value.head = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Method not allowed", request=MagicMock(), response=MagicMock()
                )
            )
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await tool.execute(url="https://example.com/page")

            assert result.success
            assert result.data["meta"]["title"] == "テストページ"
            assert (
                result.data["meta"]["canonical"] == "https://example.com/canonical-url"
            )

    @pytest.mark.asyncio
    async def test_execute_timeout(self):
        """タイムアウト"""
        tool = ToolRegistry.get("url_verify")

        import httpx

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.head = AsyncMock(
                side_effect=httpx.TimeoutException("Connection timed out")
            )

            result = await tool.execute(url="https://example.com/slow")

            assert not result.success
            assert result.error_category == ErrorCategory.RETRYABLE.value
            assert "timed out" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_execute_connection_error(self):
        """接続エラー"""
        tool = ToolRegistry.get("url_verify")

        import httpx

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.head = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )

            result = await tool.execute(url="https://example.com/unreachable")

            assert not result.success
            assert result.error_category == ErrorCategory.NON_RETRYABLE.value
            assert "Connection failed" in result.error_message
