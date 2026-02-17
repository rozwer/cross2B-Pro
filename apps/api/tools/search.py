"""
検索関連ツール

- serp_fetch: SERP取得（上位N件URL）
- search_volume: 検索ボリューム取得（Google Ads Keyword Planner / モック）
- related_keywords: 関連キーワード取得（Google Ads Keyword Planner / モック）
"""

import asyncio
import hashlib
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from .base import ErrorCategory, ToolInterface
from .registry import ToolRegistry
from .schemas import Evidence, ToolResult

logger = logging.getLogger(__name__)

# モックデータのパス
MOCK_DATA_DIR = Path(__file__).parent / "mocks"

# リトライ設定
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 1


def _compute_hash(content: str) -> str:
    """コンテンツのSHA256ハッシュを計算"""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _load_mock_data(filename: str) -> dict[str, Any]:
    """モックデータをロード"""
    filepath = MOCK_DATA_DIR / filename
    if filepath.exists():
        with open(filepath, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
            return data
    return {}


def _handle_google_ads_error(exc: Any) -> ToolResult:
    """Map Google Ads API errors to ToolResult with proper ErrorCategory."""
    error = exc.failure.errors[0] if exc.failure.errors else None
    error_code = str(error.error_code) if error else "UNKNOWN"
    message = error.message if error else str(exc)

    auth_errors = {"AUTHENTICATION_ERROR", "AUTHORIZATION_ERROR", "USER_PERMISSION_DENIED"}
    rate_errors = {"RATE_EXCEEDED", "RESOURCE_EXHAUSTED"}

    if any(e in error_code for e in auth_errors):
        category = ErrorCategory.NON_RETRYABLE.value
    elif any(e in error_code for e in rate_errors):
        category = ErrorCategory.RETRYABLE.value
    elif "QUOTA" in error_code:
        category = ErrorCategory.NON_RETRYABLE.value
    elif "INTERNAL" in error_code:
        category = ErrorCategory.RETRYABLE.value
    elif "REQUEST_ERROR" in error_code:
        category = ErrorCategory.VALIDATION_FAIL.value
    else:
        category = ErrorCategory.NON_RETRYABLE.value

    logger.error(f"Google Ads API error [{error_code}]: {message}")

    return ToolResult(
        success=False,
        error_category=category,
        error_message=f"Google Ads API error: {message}",
    )


def _build_keyword_ideas_request(client: Any, customer_id: str, keyword: str) -> Any:
    """Build a GenerateKeywordIdeasRequest for Keyword Planner API."""
    request = client.get_type("GenerateKeywordIdeasRequest")
    request.customer_id = customer_id
    request.language = "languageConstants/1005"  # Japanese
    request.geo_target_constants.append("geoTargetConstants/2392")  # Japan
    request.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
    request.keyword_seed.keywords.append(keyword)
    return request


@ToolRegistry.register(
    tool_id="serp_fetch",
    description="SERP（検索結果ページ）から上位N件のURLを取得",
    required_env=["SERP_API_KEY"],
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "検索クエリ"},
            "num_results": {
                "type": "integer",
                "default": 10,
                "description": "取得件数",
            },
            "language": {"type": "string", "default": "ja", "description": "言語コード"},
            "country": {"type": "string", "default": "jp", "description": "国コード"},
        },
        "required": ["query"],
    },
    output_description="URLリストと各ページのメタ情報",
)
class SerpFetchTool(ToolInterface):
    """
    SERP取得ツール

    検索クエリに対するGoogleの検索結果から上位N件のURLを取得する。
    実際のSERP APIを使用する。
    """

    tool_id = "serp_fetch"

    def __init__(self) -> None:
        self.api_key = os.getenv("SERP_API_KEY")
        # SerpApi のエンドポイント
        self.base_url = "https://serpapi.com/search"

    async def execute(  # type: ignore[override]
        self,
        query: str,
        num_results: int = 10,
        language: str = "ja",
        country: str = "jp",
    ) -> ToolResult:
        """SERP取得を実行"""
        if not query or not query.strip():
            return ToolResult(
                success=False,
                error_category=ErrorCategory.VALIDATION_FAIL.value,
                error_message="Query is required",
            )

        if not self.api_key:
            return ToolResult(
                success=False,
                error_category=ErrorCategory.NON_RETRYABLE.value,
                error_message="SERP_API_KEY environment variable is not set",
            )

        params = {
            "q": query,
            "api_key": self.api_key,
            "engine": "google",
            "num": num_results,
            "hl": language,
            "gl": country,
        }

        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        self.base_url,
                        params=params,  # type: ignore[arg-type]
                    )

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_response(data, query)
                elif response.status_code == 429:
                    logger.warning(f"serp_fetch: Rate limited (attempt {attempt + 1}/{MAX_RETRIES})")
                    if attempt < MAX_RETRIES - 1:
                        import asyncio

                        await asyncio.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                        continue
                    return ToolResult(
                        success=False,
                        error_category=ErrorCategory.RETRYABLE.value,
                        error_message="Rate limit exceeded after retries",
                    )
                elif response.status_code == 401:
                    return ToolResult(
                        success=False,
                        error_category=ErrorCategory.NON_RETRYABLE.value,
                        error_message="Invalid API key",
                    )
                else:
                    logger.error(f"serp_fetch: Unexpected status {response.status_code}")
                    return ToolResult(
                        success=False,
                        error_category=ErrorCategory.NON_RETRYABLE.value,
                        error_message=f"API returned status {response.status_code}",
                    )

            except httpx.TimeoutException as e:
                logger.warning(f"serp_fetch: Timeout (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    import asyncio

                    await asyncio.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                    continue
                return ToolResult(
                    success=False,
                    error_category=ErrorCategory.RETRYABLE.value,
                    error_message="Request timed out after retries",
                )
            except httpx.RequestError as e:
                logger.warning(f"serp_fetch: Network error (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                if attempt < MAX_RETRIES - 1:
                    import asyncio

                    await asyncio.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
                    continue
                return ToolResult(
                    success=False,
                    error_category=ErrorCategory.RETRYABLE.value,
                    error_message=f"Network error: {e}",
                )

        return ToolResult(
            success=False,
            error_category=ErrorCategory.RETRYABLE.value,
            error_message="Max retries exceeded",
        )

    def _parse_response(self, data: dict[str, Any], query: str) -> ToolResult:
        """SerpApi レスポンスをパース"""
        organic_results = data.get("organic_results", [])

        if not organic_results:
            return ToolResult(
                success=True,
                data={"query": query, "results": [], "total": 0},
                evidence=[],
            )

        results = []
        evidences = []

        for item in organic_results:
            url = item.get("link", "")
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            position = item.get("position", 0)

            if url:
                results.append(
                    {
                        "url": url,
                        "title": title,
                        "snippet": snippet,
                        "position": position,
                    }
                )

                # Evidence を作成
                content_for_hash = f"{url}|{title}|{snippet}"
                evidences.append(
                    Evidence(
                        url=url,
                        fetched_at=datetime.now(UTC),
                        excerpt=snippet[:200] if snippet else title[:200],
                        content_hash=_compute_hash(content_for_hash),
                    )
                )

        logger.info(f"serp_fetch: Retrieved {len(results)} results for '{query}'")

        return ToolResult(
            success=True,
            data={"query": query, "results": results, "total": len(results)},
            evidence=evidences,
        )


@ToolRegistry.register(
    tool_id="search_volume",
    description="キーワードの検索ボリュームを取得（Google Ads Keyword Planner API）",
    required_env=["USE_MOCK_GOOGLE_ADS"],
    input_schema={
        "type": "object",
        "properties": {
            "keyword": {"type": "string", "description": "検索キーワード"},
        },
        "required": ["keyword"],
    },
    output_description="検索ボリューム数値",
)
class SearchVolumeTool(ToolInterface):
    """
    検索ボリューム取得ツール

    USE_MOCK_GOOGLE_ADS=true でモックデータ、false で実 Google Ads Keyword Planner API を使用。
    """

    tool_id = "search_volume"

    def __init__(self) -> None:
        self.use_mock = os.getenv("USE_MOCK_GOOGLE_ADS", "true").lower() == "true"
        if self.use_mock:
            logger.warning("SearchVolumeTool: Running in MOCK mode. Set USE_MOCK_GOOGLE_ADS=false when Google Ads API is available.")

    async def execute(self, keyword: str) -> ToolResult:  # type: ignore[override]
        """検索ボリュームを取得"""
        if not keyword or not keyword.strip():
            return ToolResult(
                success=False,
                error_category=ErrorCategory.VALIDATION_FAIL.value,
                error_message="Keyword is required",
            )

        if self.use_mock:
            return await self._execute_mock(keyword)
        else:
            return await self._execute_real(keyword)

    async def _execute_mock(self, keyword: str) -> ToolResult:
        """モック実行: 静的データまたは推定値を返す"""
        mock_data = _load_mock_data("search_volume_data.json")

        # キーワードが事前定義されていれば使用、なければ推定値を生成
        if keyword in mock_data:
            volume = mock_data[keyword]
        else:
            # 簡易的な推定（キーワード長に基づく擬似値）
            volume = max(100, 10000 - len(keyword) * 500)

        logger.info(f"SearchVolume (MOCK): {keyword} -> {volume}")

        return ToolResult(
            success=True,
            data={"keyword": keyword, "volume": volume, "source": "mock"},
            is_mock=True,
        )

    async def _execute_real(self, keyword: str) -> ToolResult:
        """実API実行: Google Ads Keyword Planner API で検索ボリュームを取得"""
        try:
            from google.ads.googleads.errors import GoogleAdsException

            from apps.api.services.google_ads_client import GoogleAdsConfigError, get_google_ads_client

            client, customer_id = get_google_ads_client()
            service = client.get_service("KeywordPlanIdeaService")
            request = _build_keyword_ideas_request(client, customer_id, keyword)

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                service.generate_keyword_ideas,
                request,
            )

            # Find exact keyword match or take the first result
            volume = 0
            for idea in response.results:
                if idea.text.lower() == keyword.lower():
                    volume = idea.keyword_idea_metrics.avg_monthly_searches
                    break
            else:
                if response.results:
                    volume = response.results[0].keyword_idea_metrics.avg_monthly_searches

            logger.info(f"SearchVolume (REAL): {keyword} -> {volume}")

            return ToolResult(
                success=True,
                data={"keyword": keyword, "volume": volume, "source": "google_ads"},
                is_mock=False,
            )

        except GoogleAdsConfigError as e:
            logger.error(f"SearchVolume config error: {e}")
            return ToolResult(
                success=False,
                error_category=ErrorCategory.NON_RETRYABLE.value,
                error_message=f"Google Ads configuration error: {e}",
            )
        except GoogleAdsException as e:
            return _handle_google_ads_error(e)
        except Exception as e:
            logger.exception(f"SearchVolume unexpected error: {e}")
            return ToolResult(
                success=False,
                error_category=ErrorCategory.RETRYABLE.value,
                error_message=f"Unexpected error calling Google Ads API: {e}",
            )


@ToolRegistry.register(
    tool_id="related_keywords",
    description="関連キーワードを取得（Google Ads Keyword Planner API）",
    required_env=["USE_MOCK_GOOGLE_ADS"],
    input_schema={
        "type": "object",
        "properties": {
            "keyword": {"type": "string", "description": "検索キーワード"},
            "limit": {
                "type": "integer",
                "default": 10,
                "description": "取得件数上限",
            },
        },
        "required": ["keyword"],
    },
    output_description="関連キーワードのリスト",
)
class RelatedKeywordsTool(ToolInterface):
    """
    関連キーワード取得ツール

    USE_MOCK_GOOGLE_ADS=true でモックデータ、false で実 Google Ads Keyword Planner API を使用。
    """

    tool_id = "related_keywords"

    def __init__(self) -> None:
        self.use_mock = os.getenv("USE_MOCK_GOOGLE_ADS", "true").lower() == "true"
        if self.use_mock:
            logger.warning("RelatedKeywordsTool: Running in MOCK mode. Set USE_MOCK_GOOGLE_ADS=false when Google Ads API is available.")

    async def execute(  # type: ignore[override]
        self, keyword: str, limit: int = 10
    ) -> ToolResult:
        """関連キーワードを取得"""
        if not keyword or not keyword.strip():
            return ToolResult(
                success=False,
                error_category=ErrorCategory.VALIDATION_FAIL.value,
                error_message="Keyword is required",
            )

        if self.use_mock:
            return await self._execute_mock(keyword, limit)
        else:
            return await self._execute_real(keyword, limit)

    async def _execute_mock(self, keyword: str, limit: int) -> ToolResult:
        """モック実行: 静的データまたはパターン生成"""
        mock_data = _load_mock_data("related_keywords_data.json")

        if keyword in mock_data:
            keywords = mock_data[keyword][:limit]
        else:
            # パターンベースの擬似関連キーワード生成
            keywords = [
                f"{keyword} とは",
                f"{keyword} 方法",
                f"{keyword} おすすめ",
                f"{keyword} 比較",
                f"{keyword} 選び方",
                f"{keyword} メリット",
                f"{keyword} デメリット",
                f"{keyword} 費用",
                f"{keyword} 口コミ",
                f"{keyword} ランキング",
            ][:limit]

        logger.info(f"RelatedKeywords (MOCK): {keyword} -> {len(keywords)} keywords")

        return ToolResult(
            success=True,
            data={"keyword": keyword, "related": keywords, "source": "mock"},
            is_mock=True,
        )

    async def _execute_real(self, keyword: str, limit: int) -> ToolResult:
        """実API実行: Google Ads Keyword Planner API で関連キーワードを取得"""
        try:
            from google.ads.googleads.errors import GoogleAdsException

            from apps.api.services.google_ads_client import GoogleAdsConfigError, get_google_ads_client

            client, customer_id = get_google_ads_client()
            service = client.get_service("KeywordPlanIdeaService")
            request = _build_keyword_ideas_request(client, customer_id, keyword)

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                service.generate_keyword_ideas,
                request,
            )

            # Collect related keywords (excluding the exact seed keyword)
            related: list[str] = []
            for idea in response.results:
                if idea.text.lower() != keyword.lower():
                    related.append(idea.text)
                if len(related) >= limit:
                    break

            logger.info(f"RelatedKeywords (REAL): {keyword} -> {len(related)} keywords")

            return ToolResult(
                success=True,
                data={"keyword": keyword, "related": related, "source": "google_ads"},
                is_mock=False,
            )

        except GoogleAdsConfigError as e:
            logger.error(f"RelatedKeywords config error: {e}")
            return ToolResult(
                success=False,
                error_category=ErrorCategory.NON_RETRYABLE.value,
                error_message=f"Google Ads configuration error: {e}",
            )
        except GoogleAdsException as e:
            return _handle_google_ads_error(e)
        except Exception as e:
            logger.exception(f"RelatedKeywords unexpected error: {e}")
            return ToolResult(
                success=False,
                error_category=ErrorCategory.RETRYABLE.value,
                error_message=f"Unexpected error calling Google Ads API: {e}",
            )
