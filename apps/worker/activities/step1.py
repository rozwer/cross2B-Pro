"""Step 1: Competitor Article Fetch Activity.

Fetches competitor articles from SERP results for analysis.
Uses Tools (SERP + Page Fetch) for data collection.

ヘルパー統合:
- CheckpointManager: SERP結果・ページ取得の途中保存
- ContentMetrics: テキストメトリクス計算
- 個別ページリトライ: 最大2回のリトライ
- コンテンツ品質チェック: エラーページ検出
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.tools.registry import ToolRegistry
from apps.worker.helpers import CheckpointManager, ContentMetrics

from .base import ActivityError, BaseActivity

logger = logging.getLogger(__name__)


class Step1CompetitorFetch(BaseActivity):
    """Activity for fetching competitor articles.

    ヘルパー統合:
    - CheckpointManager: SERP結果・ページ取得の中間チェックポイント
    - ContentMetrics: 取得したコンテンツのメトリクス計算
    - 個別ページリトライ: ページ取得失敗時に最大2回リトライ
    - コンテンツ品質チェック: エラーページ、短すぎるコンテンツの検出
    """

    MIN_SUCCESSFUL_FETCHES = 3
    PAGE_FETCH_MAX_RETRIES = 2
    PAGE_FETCH_TIMEOUT = 30
    MAX_CONTENT_CHARS = 15000  # ~15KB per article
    PAGE_CACHE_TTL_SECONDS = 60 * 60 * 24
    PAGE_CACHE_RUN_ID = "_cache"
    PAGE_CACHE_STEP_ID = "page_fetch"

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.checkpoint = CheckpointManager(self.store)
        self.metrics = ContentMetrics()

    @property
    def step_id(self) -> str:
        return "step1"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute competitor article fetching.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with fetched competitor data
        """
        config = ctx.config
        keyword = config.get("keyword")

        if not keyword:
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Get tool registry
        registry = ToolRegistry()

        # Get tools
        try:
            serp_tool = registry.get("serp_fetch")
            page_fetch_tool = registry.get("page_fetch")
        except Exception as e:
            raise ActivityError(
                f"Required tool not found in registry: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # === SERP Checkpoint ===
        serp_checkpoint = await self.checkpoint.load(ctx.tenant_id, ctx.run_id, self.step_id, "serp_completed")

        if serp_checkpoint:
            urls = serp_checkpoint.get("urls", [])
            serp_data = serp_checkpoint.get("serp_data", {})
            logger.info(f"[STEP1] Loaded SERP checkpoint: {len(urls)} URLs")
        else:
            # Fetch SERP results
            try:
                serp_result = await serp_tool.execute(
                    query=keyword,
                    num_results=config.get("num_competitors", 10),
                )

                if not serp_result.success:
                    raise ActivityError(
                        f"SERP fetch failed: {serp_result.error_message}",
                        category=ErrorCategory.RETRYABLE,
                    )

                results = serp_result.data.get("results", []) if serp_result.data else []
                urls = [r.get("url") for r in results if r.get("url")]
                serp_data = {"results": results, "query": keyword}

            except ActivityError:
                raise
            except Exception as e:
                raise ActivityError(
                    f"SERP fetch error: {e}",
                    category=ErrorCategory.RETRYABLE,
                ) from e

            # Check for empty results
            if not urls:
                raise ActivityError(
                    "SERP returned 0 results - cannot proceed without competitor data",
                    category=ErrorCategory.NON_RETRYABLE,
                )

            # Save SERP checkpoint
            await self.checkpoint.save(ctx.tenant_id, ctx.run_id, self.step_id, "serp_completed", {"urls": urls, "serp_data": serp_data})
            logger.info(f"[STEP1] Saved SERP checkpoint: {len(urls)} URLs")

        # === Pages Checkpoint ===
        pages_checkpoint = await self.checkpoint.load(ctx.tenant_id, ctx.run_id, self.step_id, "pages_partial")

        already_fetched: set[str]
        partial_results: list[dict[str, Any]]
        failed_urls: list[dict[str, Any]]

        if pages_checkpoint:
            already_fetched = set(pages_checkpoint.get("fetched_urls", []))
            partial_results = pages_checkpoint.get("results", [])
            failed_urls = pages_checkpoint.get("failed_urls", [])
            logger.info(f"[STEP1] Loaded pages checkpoint: {len(partial_results)} fetched, {len(already_fetched)} processed")
        else:
            already_fetched = set()
            partial_results = []
            failed_urls = []

        # Fetch remaining URLs
        remaining_urls = [u for u in urls if u not in already_fetched]

        if remaining_urls:
            new_results, new_failures = await self._fetch_pages_with_retry(page_fetch_tool, remaining_urls, ctx.tenant_id)

            partial_results.extend(new_results)
            failed_urls.extend(new_failures)

            # Update checkpoint
            await self.checkpoint.save(
                ctx.tenant_id,
                ctx.run_id,
                self.step_id,
                "pages_partial",
                {
                    "fetched_urls": list(already_fetched | set(remaining_urls)),
                    "results": partial_results,
                    "failed_urls": failed_urls,
                },
            )
            activity.heartbeat(f"Fetched {len(partial_results)}/{len(urls)} pages")

        # Check minimum successful fetches
        success_count = len(partial_results)

        if success_count < self.MIN_SUCCESSFUL_FETCHES:
            raise ActivityError(
                f"Insufficient data: only {success_count} pages fetched (minimum: {self.MIN_SUCCESSFUL_FETCHES})",
                category=ErrorCategory.RETRYABLE,
            )

        # Calculate fetch stats
        fetch_stats = {
            "total_urls": len(urls),
            "successful": success_count,
            "failed": len(failed_urls),
            "success_rate": success_count / len(urls) if urls else 0,
        }

        logger.info(f"[STEP1] Completed: {success_count} competitors, {len(failed_urls)} failed URLs")

        return {
            "step": self.step_id,
            "keyword": keyword,
            "serp_query": keyword,
            "competitors": partial_results,
            "failed_urls": failed_urls,
            "fetch_stats": fetch_stats,
        }

    async def _fetch_pages_with_retry(
        self,
        page_fetch_tool: Any,
        urls: list[str],
        tenant_id: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Fetch pages with individual retry logic.

        Args:
            page_fetch_tool: Page fetch tool instance
            urls: List of URLs to fetch
            tenant_id: Tenant identifier for cache isolation

        Returns:
            Tuple of (successful results, failed results)
        """
        results: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []

        for url in urls:
            page_data, error = await self._fetch_page_with_retry(page_fetch_tool, url, tenant_id)

            if page_data:
                results.append(page_data)
            else:
                failures.append({"url": url, "error": error})

        return results, failures

    async def _fetch_page_with_retry(
        self,
        page_fetch_tool: Any,
        url: str,
        tenant_id: str,
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Fetch a single page with retry logic.

        Args:
            page_fetch_tool: Page fetch tool instance
            url: URL to fetch
            tenant_id: Tenant identifier for cache isolation

        Returns:
            Tuple of (page data, error message)
        """
        last_error: str | None = None

        cached = await self._load_cached_page(tenant_id, url)
        if cached:
            return cached, None

        for attempt in range(self.PAGE_FETCH_MAX_RETRIES):
            try:
                fetch_result = await asyncio.wait_for(
                    page_fetch_tool.execute(url=url),
                    timeout=self.PAGE_FETCH_TIMEOUT,
                )

                if fetch_result.success and fetch_result.data:
                    content = fetch_result.data.get("body_text", fetch_result.data.get("content", ""))

                    # Content quality check
                    if self._is_valid_content(content):
                        page_data = self._extract_page_data(fetch_result.data, url)
                        await self._store_cached_page(tenant_id, url, page_data)
                        return page_data, None

                    last_error = "invalid_content"
                else:
                    last_error = fetch_result.error_message or "fetch_failed"

            except TimeoutError:
                last_error = f"timeout_{self.PAGE_FETCH_TIMEOUT}s"
            except Exception as e:
                last_error = str(e)

            # Exponential backoff between retries
            if attempt < self.PAGE_FETCH_MAX_RETRIES - 1:
                await asyncio.sleep(1 * (attempt + 1))

        return None, last_error

    async def _load_cached_page(self, tenant_id: str, url: str) -> dict[str, Any] | None:
        cache_key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        filename = f"{cache_key}.json"
        try:
            cached_bytes = await self.store.get_by_path(
                tenant_id=tenant_id,
                run_id=self.PAGE_CACHE_RUN_ID,
                step=self.PAGE_CACHE_STEP_ID,
                filename=filename,
            )
        except Exception as e:
            logger.warning(f"[STEP1] Cache read failed for {url}: {e}")
            return None

        if not cached_bytes:
            return None

        try:
            cached = json.loads(cached_bytes.decode("utf-8"))
            cached_at = datetime.fromisoformat(cached.get("cached_at", ""))
        except (ValueError, json.JSONDecodeError, TypeError):
            return None

        if (datetime.utcnow() - cached_at).total_seconds() > self.PAGE_CACHE_TTL_SECONDS:
            return None

        data = cached.get("data")
        return data if isinstance(data, dict) else None

    async def _store_cached_page(self, tenant_id: str, url: str, page_data: dict[str, Any]) -> None:
        cache_key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        filename = f"{cache_key}.json"
        cache_payload = {
            "url": url,
            "cached_at": datetime.utcnow().isoformat(),
            "data": page_data,
        }
        try:
            await self.store.put(
                content=json.dumps(cache_payload, ensure_ascii=False).encode("utf-8"),
                path=self.store.build_path(
                    tenant_id=tenant_id,
                    run_id=self.PAGE_CACHE_RUN_ID,
                    step=self.PAGE_CACHE_STEP_ID,
                    filename=filename,
                ),
                content_type="application/json",
            )
        except Exception as e:
            logger.warning(f"[STEP1] Cache write failed for {url}: {e}")

    def _is_valid_content(self, content: str) -> bool:
        """Check if content is valid (not an error page).

        Args:
            content: Page content

        Returns:
            True if content is valid
        """
        if not content or len(content) < 100:
            return False

        # Error page detection
        error_indicators = [
            "404",
            "403",
            "access denied",
            "not found",
            "cloudflare",
            "captcha",
            "robot check",
            "please enable javascript",
            "browser not supported",
        ]
        content_lower = content.lower()

        for indicator in error_indicators:
            if indicator in content_lower and len(content) < 500:
                return False

        return True

    def _extract_page_data(
        self,
        fetch_data: dict[str, Any],
        url: str,
    ) -> dict[str, Any]:
        """Extract and structure page data.

        Args:
            fetch_data: Raw fetch result data
            url: Page URL

        Returns:
            Structured page data
        """
        content = fetch_data.get("body_text", fetch_data.get("content", ""))

        # Truncate if too large
        if len(content) > self.MAX_CONTENT_CHARS:
            content = content[: self.MAX_CONTENT_CHARS] + "... [truncated]"

        # Calculate metrics
        text_metrics = self.metrics.text_metrics(content, lang="ja")

        # Extract headings if available
        headings = fetch_data.get("headings", [])
        if not headings and "h2" in fetch_data:
            headings = fetch_data.get("h2", [])

        return {
            "url": url,
            "title": fetch_data.get("title", ""),
            "content": content,
            "word_count": text_metrics.word_count,
            "headings": headings,
            "fetched_at": datetime.utcnow().isoformat(),
            # blog.System 対応フィールド（取得可能な場合のみ、なければ None）
            "meta_description": fetch_data.get("meta_description"),
            "structured_data": fetch_data.get("structured_data"),
            "publish_date": fetch_data.get("publish_date"),
        }


@activity.defn(name="step1_competitor_fetch")
async def step1_competitor_fetch(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 1."""
    step = Step1CompetitorFetch()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
