"""Step 1.5: Related Keyword Competitor Extraction Activity.

関連キーワードの上位サイト競合本文を抽出するオプション工程。
step0の結果(recommended_angles等)を参照して関連KW選定を最適化。

ヘルパー統合:
- CheckpointManager: 関連KW毎の取得の途中保存
- ContentMetrics: テキストメトリクス計算
- 個別ページリトライ: 最大2回のリトライ
- コンテンツ品質チェック: エラーページ検出
"""

import asyncio
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


class Step1_5RelatedKeywordExtraction(BaseActivity):
    """Activity for fetching related keyword competitor articles.

    この工程はオプションであり、related_keywordsが空の場合はスキップされる。

    ヘルパー統合:
    - CheckpointManager: 関連KW毎の中間チェックポイント
    - ContentMetrics: 取得したコンテンツのメトリクス計算
    - 個別ページリトライ: ページ取得失敗時に最大2回リトライ
    - コンテンツ品質チェック: エラーページ、短すぎるコンテンツの検出
    """

    PAGE_FETCH_MAX_RETRIES = 2
    PAGE_FETCH_TIMEOUT = 30
    MAX_CONTENT_CHARS = 15000
    MAX_COMPETITORS_PER_KEYWORD = 3  # 関連KWあたりの競合記事数
    MAX_RELATED_KEYWORDS = 5  # 処理する関連KWの上限

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.checkpoint = CheckpointManager(self.store)
        self.metrics = ContentMetrics()

    @property
    def step_id(self) -> str:
        return "step1_5"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute related keyword competitor extraction.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with related keyword competitor data, or skip info
        """
        from .base import load_step_data

        config = ctx.config
        related_keywords: list[str] = config.get("related_keywords", [])

        # Load step0 data to leverage recommended_angles for keyword selection
        step0_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step0") or {}
        recommended_angles = step0_data.get("recommended_angles", [])

        # If no related_keywords in config, try to derive from step0
        if not related_keywords and recommended_angles:
            logger.info("[STEP1.5] Attempting to derive keywords from step0 recommended_angles")
            # Extract keywords from recommended angles with strict type checking
            for angle in recommended_angles[: self.MAX_RELATED_KEYWORDS]:
                if isinstance(angle, dict):
                    # keyword field is required; skip if not present
                    angle_kw = angle.get("keyword")
                    if not angle_kw:
                        logger.warning(f"[STEP1.5] Skipping angle without keyword field: {angle}")
                        continue
                elif isinstance(angle, str):
                    angle_kw = angle
                else:
                    logger.warning(f"[STEP1.5] Skipping unexpected angle type: {type(angle)}")
                    continue

                # Validate and add keyword
                angle_kw_stripped = angle_kw.strip() if isinstance(angle_kw, str) else ""
                if angle_kw_stripped and angle_kw_stripped not in related_keywords:
                    related_keywords.append(angle_kw_stripped)

            if related_keywords:
                logger.info(f"[STEP1.5] Derived {len(related_keywords)} keywords from step0")
            else:
                logger.info("[STEP1.5] No valid keywords derived from step0")

        # スキップ条件: related_keywordsが空の場合
        if not related_keywords:
            logger.info("[STEP1.5] Skipped: No related keywords provided")
            return {
                "step": self.step_id,
                "related_keywords_analyzed": 0,
                "related_competitor_data": [],
                "metadata": {
                    "fetched_at": datetime.utcnow().isoformat(),
                    "source": "skipped",
                    "total_keywords_processed": 0,
                    "total_articles_fetched": 0,
                },
                "skipped": True,
                "skip_reason": "no_related_keywords",
            }

        # 処理するKWを上限に制限
        keywords_to_process = related_keywords[: self.MAX_RELATED_KEYWORDS]

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

        # === Checkpoint Check ===
        checkpoint_data = await self.checkpoint.load(ctx.tenant_id, ctx.run_id, self.step_id, "related_kw_progress")

        processed_keywords: set[str]
        all_competitor_data: list[dict[str, Any]]

        if checkpoint_data:
            processed_keywords = set(checkpoint_data.get("processed_keywords", []))
            all_competitor_data = checkpoint_data.get("competitor_data", [])
            logger.info(f"[STEP1.5] Loaded checkpoint: {len(processed_keywords)} keywords processed")
        else:
            processed_keywords = set()
            all_competitor_data = []

        # Process remaining keywords
        remaining_keywords = [kw for kw in keywords_to_process if kw not in processed_keywords]

        for keyword in remaining_keywords:
            logger.info(f"[STEP1.5] Processing related keyword: {keyword}")

            kw_data = await self._process_related_keyword(
                serp_tool=serp_tool,
                page_fetch_tool=page_fetch_tool,
                keyword=keyword,
            )

            all_competitor_data.append(kw_data)
            processed_keywords.add(keyword)

            # Save checkpoint after each keyword
            await self.checkpoint.save(
                ctx.tenant_id,
                ctx.run_id,
                self.step_id,
                "related_kw_progress",
                {
                    "processed_keywords": list(processed_keywords),
                    "competitor_data": all_competitor_data,
                },
            )
            activity.heartbeat(f"Processed {len(processed_keywords)}/{len(keywords_to_process)} keywords")

        # Calculate totals
        total_articles = sum(len(data.get("competitors", [])) for data in all_competitor_data)

        logger.info(f"[STEP1.5] Completed: {len(all_competitor_data)} keywords, {total_articles} articles")

        return {
            "step": self.step_id,
            "related_keywords_analyzed": len(all_competitor_data),
            "related_competitor_data": all_competitor_data,
            "metadata": {
                "fetched_at": datetime.utcnow().isoformat(),
                "source": "serp_fetch",
                "total_keywords_processed": len(all_competitor_data),
                "total_articles_fetched": total_articles,
            },
            "skipped": False,
            "skip_reason": None,
        }

    async def _process_related_keyword(
        self,
        serp_tool: Any,
        page_fetch_tool: Any,
        keyword: str,
    ) -> dict[str, Any]:
        """Process a single related keyword.

        Args:
            serp_tool: SERP fetch tool instance
            page_fetch_tool: Page fetch tool instance
            keyword: Related keyword to process

        Returns:
            dict with keyword competitor data
        """
        # Fetch SERP results for this keyword
        try:
            serp_result = await serp_tool.execute(
                query=keyword,
                num_results=self.MAX_COMPETITORS_PER_KEYWORD + 2,  # 少し多めに取得
            )

            if not serp_result.success:
                logger.warning(f"[STEP1.5] SERP fetch failed for {keyword}: {serp_result.error_message}")
                return {
                    "keyword": keyword,
                    "search_results_count": 0,
                    "competitors": [],
                    "fetch_success_count": 0,
                    "fetch_failed_count": 0,
                }

            # Handle both "results" and "urls" keys for compatibility
            results = serp_result.data.get("results", []) if serp_result.data else []
            urls = [r.get("url") for r in results if r.get("url")]
            if not urls:
                urls = serp_result.data.get("urls", []) if serp_result.data else []

        except Exception as e:
            logger.warning(f"[STEP1.5] SERP error for {keyword}: {e}")
            return {
                "keyword": keyword,
                "search_results_count": 0,
                "competitors": [],
                "fetch_success_count": 0,
                "fetch_failed_count": 0,
            }

        # Fetch pages
        competitors: list[dict[str, Any]] = []
        failed_count = 0

        for url in urls[: self.MAX_COMPETITORS_PER_KEYWORD]:
            page_data, error = await self._fetch_page_with_retry(page_fetch_tool, url)

            if page_data:
                page_data["related_keyword"] = keyword
                competitors.append(page_data)
            else:
                failed_count += 1
                logger.debug(f"[STEP1.5] Failed to fetch {url}: {error}")

        return {
            "keyword": keyword,
            "search_results_count": len(urls),
            "competitors": competitors,
            "fetch_success_count": len(competitors),
            "fetch_failed_count": failed_count,
        }

    async def _fetch_page_with_retry(
        self,
        page_fetch_tool: Any,
        url: str,
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Fetch a single page with retry logic.

        Args:
            page_fetch_tool: Page fetch tool instance
            url: URL to fetch

        Returns:
            Tuple of (page data, error message)
        """
        last_error: str | None = None

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
                        return self._extract_page_data(fetch_result.data, url), None

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

        # Create summary (first 500 chars for related KW)
        content_summary = content[:2000] if content else ""

        # Extract headings if available
        headings = fetch_data.get("headings", [])
        if not headings and "h2" in fetch_data:
            headings = fetch_data.get("h2", [])

        return {
            "url": url,
            "title": fetch_data.get("title", ""),
            "content_summary": content_summary,
            "word_count": text_metrics.word_count,
            "headings": headings,
            "fetched_at": datetime.utcnow().isoformat(),
        }


@activity.defn(name="step1_5_related_keyword_extraction")
async def step1_5_related_keyword_extraction(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 1.5."""
    step = Step1_5RelatedKeywordExtraction()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
