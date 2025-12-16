"""
検索関連ツール

- serp_fetch: SERP取得（上位N件URL）
- search_volume: 検索ボリューム取得（モック）
- related_keywords: 関連キーワード取得（モック）
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from .base import ErrorCategory, ToolInterface
from .exceptions import (
    NonRetryableError,
    RateLimitError,
    RetryableError,
    ValidationError,
)
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

    def __init__(self):
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
                        self.base_url, params=params  # type: ignore[arg-type]
                    )

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_response(data, query)
                elif response.status_code == 429:
                    logger.warning(
                        f"serp_fetch: Rate limited (attempt {attempt + 1}/{MAX_RETRIES})"
                    )
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
                    logger.error(
                        f"serp_fetch: Unexpected status {response.status_code}"
                    )
                    return ToolResult(
                        success=False,
                        error_category=ErrorCategory.NON_RETRYABLE.value,
                        error_message=f"API returned status {response.status_code}",
                    )

            except httpx.TimeoutException as e:
                logger.warning(
                    f"serp_fetch: Timeout (attempt {attempt + 1}/{MAX_RETRIES}): {e}"
                )
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
                logger.warning(
                    f"serp_fetch: Network error (attempt {attempt + 1}/{MAX_RETRIES}): {e}"
                )
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
                        fetched_at=datetime.now(timezone.utc),
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
    description="キーワードの検索ボリュームを取得（Google Ads API未取得のためモック）",
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

    注意: Google Ads API が未取得のため、現在はモック実装
    将来的に実API実装に切り替える際は USE_MOCK_GOOGLE_ADS=false を設定
    """

    tool_id = "search_volume"

    def __init__(self):
        self.use_mock = os.getenv("USE_MOCK_GOOGLE_ADS", "true").lower() == "true"
        if self.use_mock:
            logger.warning(
                "SearchVolumeTool: Running in MOCK mode. "
                "Set USE_MOCK_GOOGLE_ADS=false when Google Ads API is available."
            )

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
        """実API実行: Google Ads API を使用"""
        # TODO: Google Ads API 取得後に実装
        raise NotImplementedError(
            "Real Google Ads API not implemented. "
            "Set USE_MOCK_GOOGLE_ADS=true or implement _execute_real()"
        )


@ToolRegistry.register(
    tool_id="related_keywords",
    description="関連キーワードを取得（Google Ads API未取得のためモック）",
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

    注意: Google Ads API が未取得のため、現在はモック実装
    将来的に実API実装に切り替える際は USE_MOCK_GOOGLE_ADS=false を設定
    """

    tool_id = "related_keywords"

    def __init__(self):
        self.use_mock = os.getenv("USE_MOCK_GOOGLE_ADS", "true").lower() == "true"
        if self.use_mock:
            logger.warning(
                "RelatedKeywordsTool: Running in MOCK mode. "
                "Set USE_MOCK_GOOGLE_ADS=false when Google Ads API is available."
            )

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
        """実API実行: Google Ads API を使用"""
        # TODO: Google Ads API 取得後に実装
        raise NotImplementedError(
            "Real Google Ads API not implemented. "
            "Set USE_MOCK_GOOGLE_ADS=true or implement _execute_real()"
        )
