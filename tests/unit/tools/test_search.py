"""
検索ツールのテスト
"""

import os
import sys
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


# ---------------------------------------------------------------------------
# Real mode tests (Google Ads API mocked at client level)
# ---------------------------------------------------------------------------


def _make_keyword_idea(text: str, avg_monthly_searches: int):
    """Helper: Create a mock KeywordPlanIdeaService result item."""
    idea = MagicMock()
    idea.text = text
    idea.keyword_idea_metrics = MagicMock()
    idea.keyword_idea_metrics.avg_monthly_searches = avg_monthly_searches
    return idea


def _make_keyword_response(ideas: list):
    """Helper: Create a mock GenerateKeywordIdeas response."""
    response = MagicMock()
    response.results = ideas
    return response


class TestSearchVolumeToolRealMode:
    """search_volume ツールのリアルモードテスト（Google Ads クライアントをモック）"""

    @pytest.mark.asyncio
    async def test_execute_real_mode_exact_match(self):
        """リアルモード - 完全一致キーワード"""
        tool = ToolRegistry.get("search_volume")
        tool.use_mock = False

        ideas = [
            _make_keyword_idea("SEO対策", 12000),
            _make_keyword_idea("SEO対策 方法", 3000),
        ]
        mock_response = _make_keyword_response(ideas)

        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_service.generate_keyword_ideas.return_value = mock_response
        mock_client.get_service.return_value = mock_service
        mock_client.get_type.return_value = MagicMock()
        mock_client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH = 2

        with patch("apps.api.services.google_ads_client.get_google_ads_client", return_value=(mock_client, "1234567890")):
            # Ensure import inside _execute_real works
            with patch.dict("sys.modules", {"google.ads.googleads.errors": MagicMock()}):
                result = await tool.execute(keyword="SEO対策")

        assert result.success
        assert result.is_mock is False
        assert result.data["keyword"] == "SEO対策"
        assert result.data["volume"] == 12000
        assert result.data["source"] == "google_ads"

    @pytest.mark.asyncio
    async def test_execute_real_mode_no_exact_match(self):
        """リアルモード - 完全一致なし（最初の結果を使用）"""
        tool = ToolRegistry.get("search_volume")
        tool.use_mock = False

        ideas = [_make_keyword_idea("SEO対策 方法", 5000)]
        mock_response = _make_keyword_response(ideas)

        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_service.generate_keyword_ideas.return_value = mock_response
        mock_client.get_service.return_value = mock_service
        mock_client.get_type.return_value = MagicMock()
        mock_client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH = 2

        with patch("apps.api.services.google_ads_client.get_google_ads_client", return_value=(mock_client, "1234567890")):
            with patch.dict("sys.modules", {"google.ads.googleads.errors": MagicMock()}):
                result = await tool.execute(keyword="SEO対策")

        assert result.success
        assert result.data["volume"] == 5000

    @pytest.mark.asyncio
    async def test_execute_real_mode_empty_results(self):
        """リアルモード - 結果なし（volume=0）"""
        tool = ToolRegistry.get("search_volume")
        tool.use_mock = False

        mock_response = _make_keyword_response([])

        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_service.generate_keyword_ideas.return_value = mock_response
        mock_client.get_service.return_value = mock_service
        mock_client.get_type.return_value = MagicMock()
        mock_client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH = 2

        with patch("apps.api.services.google_ads_client.get_google_ads_client", return_value=(mock_client, "1234567890")):
            with patch.dict("sys.modules", {"google.ads.googleads.errors": MagicMock()}):
                result = await tool.execute(keyword="超ニッチキーワード")

        assert result.success
        assert result.data["volume"] == 0

    @pytest.mark.asyncio
    async def test_execute_real_mode_config_error(self):
        """リアルモード - 設定エラー"""
        tool = ToolRegistry.get("search_volume")
        tool.use_mock = False

        from apps.api.services.google_ads_client import GoogleAdsConfigError

        with patch(
            "apps.api.services.google_ads_client.get_google_ads_client",
            side_effect=GoogleAdsConfigError("Missing GOOGLE_ADS_DEVELOPER_TOKEN"),
        ):
            with patch.dict("sys.modules", {"google.ads.googleads.errors": MagicMock()}):
                result = await tool.execute(keyword="SEO対策")

        assert not result.success
        assert result.error_category == ErrorCategory.NON_RETRYABLE.value
        assert "configuration error" in result.error_message.lower()


class TestRelatedKeywordsToolRealMode:
    """related_keywords ツールのリアルモードテスト"""

    @pytest.mark.asyncio
    async def test_execute_real_mode_success(self):
        """リアルモード - 関連キーワード取得成功"""
        tool = ToolRegistry.get("related_keywords")
        tool.use_mock = False

        ideas = [
            _make_keyword_idea("SEO対策", 12000),  # seed keyword (excluded)
            _make_keyword_idea("SEO対策 方法", 3000),
            _make_keyword_idea("SEO対策 費用", 2000),
            _make_keyword_idea("SEO 基本", 1500),
        ]
        mock_response = _make_keyword_response(ideas)

        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_service.generate_keyword_ideas.return_value = mock_response
        mock_client.get_service.return_value = mock_service
        mock_client.get_type.return_value = MagicMock()
        mock_client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH = 2

        with patch("apps.api.services.google_ads_client.get_google_ads_client", return_value=(mock_client, "1234567890")):
            with patch.dict("sys.modules", {"google.ads.googleads.errors": MagicMock()}):
                result = await tool.execute(keyword="SEO対策", limit=5)

        assert result.success
        assert result.is_mock is False
        assert result.data["keyword"] == "SEO対策"
        assert result.data["source"] == "google_ads"
        # Seed keyword should be excluded
        assert "SEO対策" not in result.data["related"]
        assert "SEO対策 方法" in result.data["related"]
        assert len(result.data["related"]) == 3

    @pytest.mark.asyncio
    async def test_execute_real_mode_respects_limit(self):
        """リアルモード - limit パラメータが反映される"""
        tool = ToolRegistry.get("related_keywords")
        tool.use_mock = False

        ideas = [
            _make_keyword_idea("SEO対策 方法", 3000),
            _make_keyword_idea("SEO対策 費用", 2000),
            _make_keyword_idea("SEO 基本", 1500),
            _make_keyword_idea("SEO ツール", 1000),
        ]
        mock_response = _make_keyword_response(ideas)

        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_service.generate_keyword_ideas.return_value = mock_response
        mock_client.get_service.return_value = mock_service
        mock_client.get_type.return_value = MagicMock()
        mock_client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH = 2

        with patch("apps.api.services.google_ads_client.get_google_ads_client", return_value=(mock_client, "1234567890")):
            with patch.dict("sys.modules", {"google.ads.googleads.errors": MagicMock()}):
                result = await tool.execute(keyword="テスト", limit=2)

        assert result.success
        assert len(result.data["related"]) == 2

    @pytest.mark.asyncio
    async def test_execute_real_mode_config_error(self):
        """リアルモード - 設定エラー"""
        tool = ToolRegistry.get("related_keywords")
        tool.use_mock = False

        from apps.api.services.google_ads_client import GoogleAdsConfigError

        with patch(
            "apps.api.services.google_ads_client.get_google_ads_client",
            side_effect=GoogleAdsConfigError("Missing credentials"),
        ):
            with patch.dict("sys.modules", {"google.ads.googleads.errors": MagicMock()}):
                result = await tool.execute(keyword="SEO対策")

        assert not result.success
        assert result.error_category == ErrorCategory.NON_RETRYABLE.value
