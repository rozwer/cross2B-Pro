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

        # Extract related_keywords from user input (correct path)
        # For article_hearing_v1 format: config["input"]["data"]["keyword"]["related_keywords"]
        input_data = config.get("input", {})
        input_format = input_data.get("format", "unknown")
        logger.info(f"[STEP1.5] Input format: {input_format}, input_data keys: {list(input_data.keys()) if input_data else 'empty'}")

        user_related_keywords: list[dict[str, Any] | str] = []

        if input_format == "article_hearing_v1":
            keyword_data = input_data.get("data", {}).get("keyword", {})
            user_related_keywords = keyword_data.get("related_keywords", []) or []
            logger.info(f"[STEP1.5] Found {len(user_related_keywords)} related keywords in article_hearing_v1 format")
            if user_related_keywords:
                logger.info(f"[STEP1.5] Related keywords raw data: {user_related_keywords}")

        # Convert RelatedKeyword objects (dict with "keyword" field) to string list
        related_keywords: list[str] = []
        for rk in user_related_keywords:
            if isinstance(rk, dict):
                kw = rk.get("keyword", "")
                if kw and isinstance(kw, str):
                    related_keywords.append(kw.strip())
            elif isinstance(rk, str) and rk.strip():
                related_keywords.append(rk.strip())

        if related_keywords:
            logger.info(f"[STEP1.5] Using {len(related_keywords)} user-provided related keywords: {related_keywords}")

        # Load step1 data to exclude duplicate URLs
        step1_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step1") or {}
        step1_urls: set[str] = set()
        for comp in step1_data.get("competitors", []):
            url = comp.get("url", "")
            if url:
                step1_urls.add(url)
        if step1_urls:
            logger.info(f"[STEP1.5] Loaded {len(step1_urls)} URLs from step1 for deduplication")

        # Load step0 data to leverage recommended_angles for keyword selection
        step0_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step0") or {}
        recommended_angles = step0_data.get("recommended_angles", [])

        # === Google Ads Related Keywords Enrichment ===
        # Use multiple seed keywords for better coverage:
        # 1. Main keyword as-is
        # 2. Shortened main keyword (first 2 words for broader results)
        # 3. Up to 3 recommended_angles from step0
        main_keyword = config.get("keyword", "")
        google_ads_related: list[str] = []
        if main_keyword:
            seed_keywords: list[str] = [main_keyword]

            # Add shortened version (long-tail KWs return few results)
            parts = main_keyword.split()
            if len(parts) > 2:
                seed_keywords.append(" ".join(parts[:2]))

            # Add shortened recommended_angles as additional seeds
            # Google Ads Keyword Planner works best with 1-3 word queries,
            # so we extract the first 2 words from each angle
            for angle in recommended_angles[:5]:
                angle_str = angle.get("keyword", "") if isinstance(angle, dict) else str(angle) if isinstance(angle, str) else ""
                angle_str = angle_str.strip()
                if not angle_str:
                    continue
                # Shorten to first 2 words for broader results
                angle_parts = angle_str.split()
                shortened = " ".join(angle_parts[:2]) if len(angle_parts) > 2 else angle_str
                if shortened not in seed_keywords:
                    seed_keywords.append(shortened)

            try:
                ads_registry = ToolRegistry()
                related_kw_tool = ads_registry.get("related_keywords")
                seen: set[str] = set()

                for seed in seed_keywords:
                    ads_result = await related_kw_tool.execute(keyword=seed, limit=30)
                    if ads_result.success and ads_result.data:
                        for kw in ads_result.data.get("related", []):
                            if kw not in seen:
                                seen.add(kw)
                                google_ads_related.append(kw)
                        logger.info(
                            f"[STEP1.5] Google Ads '{seed}': "
                            f"{len(ads_result.data.get('related', []))} keywords "
                            f"(source: {ads_result.data.get('source', 'unknown')})"
                        )
                    else:
                        logger.warning(f"[STEP1.5] Google Ads '{seed}' failed: {ads_result.error_message}")

                logger.info(f"[STEP1.5] Google Ads total unique related keywords: {len(google_ads_related)}")
            except Exception as e:
                logger.warning(f"[STEP1.5] Google Ads related_keywords tool error (non-fatal): {e}")
        else:
            logger.info("[STEP1.5] No main keyword for Google Ads enrichment")

        # If no user-provided related_keywords, try to derive from step0 as fallback
        if not related_keywords and recommended_angles:
            logger.info("[STEP1.5] No user-provided keywords, deriving from step0 recommended_angles as fallback")
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
        # Note: Google Ads data is still included even when SERP processing is skipped
        if not related_keywords:
            logger.info("[STEP1.5] Skipped SERP processing: No related keywords provided")
            output_data = {
                "step": self.step_id,
                "related_keywords_analyzed": 0,
                "related_competitor_data": [],
                "google_ads_related_keywords": google_ads_related,
                "metadata": {
                    "fetched_at": datetime.utcnow().isoformat(),
                    "source": "skipped" if not google_ads_related else "google_ads_only",
                    "total_keywords_processed": 0,
                    "total_articles_fetched": 0,
                    "google_ads_keyword_count": len(google_ads_related),
                },
                "skipped": True,
                "skip_reason": "no_related_keywords",
            }
            output_data["output_path"] = self.store.build_path(ctx.tenant_id, ctx.run_id, self.step_id)
            output_data["output_digest"] = hashlib.sha256(
                json.dumps(output_data, ensure_ascii=False, indent=2).encode("utf-8")
            ).hexdigest()[:16]
            return output_data

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
                exclude_urls=step1_urls,
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

        output_data = {
            "step": self.step_id,
            "related_keywords_analyzed": len(all_competitor_data),
            "related_competitor_data": all_competitor_data,
            "google_ads_related_keywords": google_ads_related,
            "metadata": {
                "fetched_at": datetime.utcnow().isoformat(),
                "source": "serp_fetch",
                "total_keywords_processed": len(all_competitor_data),
                "total_articles_fetched": total_articles,
                "google_ads_keyword_count": len(google_ads_related),
            },
            "skipped": False,
            "skip_reason": None,
        }
        output_data["output_path"] = self.store.build_path(ctx.tenant_id, ctx.run_id, self.step_id)
        output_data["output_digest"] = hashlib.sha256(json.dumps(output_data, ensure_ascii=False, indent=2).encode("utf-8")).hexdigest()[
            :16
        ]
        return output_data

    async def _process_related_keyword(
        self,
        serp_tool: Any,
        page_fetch_tool: Any,
        keyword: str,
        exclude_urls: set[str] | None = None,
    ) -> dict[str, Any]:
        """Process a single related keyword.

        Args:
            serp_tool: SERP fetch tool instance
            page_fetch_tool: Page fetch tool instance
            keyword: Related keyword to process
            exclude_urls: URLs to exclude (e.g., from step1)

        Returns:
            dict with keyword competitor data
        """
        exclude_urls = exclude_urls or set()

        # Fetch SERP results for this keyword
        try:
            serp_result = await serp_tool.execute(
                query=keyword,
                num_results=self.MAX_COMPETITORS_PER_KEYWORD + 5,  # 除外分を考慮して多めに取得
            )

            if not serp_result.success:
                logger.warning(f"[STEP1.5] SERP fetch failed for {keyword}: {serp_result.error_message}")
                return {
                    "keyword": keyword,
                    "search_results_count": 0,
                    "competitors": [],
                    "fetch_success_count": 0,
                    "fetch_failed_count": 0,
                    "skipped_duplicate_count": 0,
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
                "skipped_duplicate_count": 0,
            }

        # Filter out URLs already in step1
        original_url_count = len(urls)
        filtered_urls = [u for u in urls if u not in exclude_urls]
        skipped_count = original_url_count - len(filtered_urls)

        if skipped_count > 0:
            logger.info(f"[STEP1.5] Excluded {skipped_count} duplicate URLs from step1 for keyword '{keyword}'")

        # Fetch pages
        competitors: list[dict[str, Any]] = []
        failed_count = 0

        for url in filtered_urls[: self.MAX_COMPETITORS_PER_KEYWORD]:
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
            "skipped_duplicate_count": skipped_count,
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
