"""Step 1: Competitor Article Fetch Activity.

Fetches competitor articles from SERP results for analysis.
Uses Tools (SERP + Page Fetch) for data collection.
"""

from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.tools.registry import ToolRegistry

from .base import ActivityError, BaseActivity


class Step1CompetitorFetch(BaseActivity):
    """Activity for fetching competitor articles."""

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

        # Step 1.1: SERP fetch to get competitor URLs
        try:
            serp_tool = registry.get("serp_fetch")
        except Exception as e:
            raise ActivityError(
                f"serp_fetch tool not found in registry: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

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

            # SerpFetchTool returns {"results": [{url, title, ...}, ...]}
            results = serp_result.data.get("results", []) if serp_result.data else []
            urls = [r.get("url") for r in results if r.get("url")]

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

        # Step 1.2: Fetch each competitor page
        try:
            page_fetch_tool = registry.get("page_fetch")
        except Exception as e:
            raise ActivityError(
                f"page_fetch tool not found in registry: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        competitors = []
        failed_urls = []

        # Limit content size to avoid gRPC message size limits (4MB)
        MAX_CONTENT_CHARS = 10000  # ~10KB per article, reasonable for analysis

        for url in urls:
            try:
                fetch_result = await page_fetch_tool.execute(url=url)

                if fetch_result.success and fetch_result.data:
                    # Get content and truncate if too large
                    content = fetch_result.data.get("body_text", fetch_result.data.get("content", ""))
                    if len(content) > MAX_CONTENT_CHARS:
                        content = content[:MAX_CONTENT_CHARS] + "... [truncated]"

                    competitors.append({
                        "url": url,
                        "title": fetch_result.data.get("title", ""),
                        "content": content,
                        "fetched_at": fetch_result.data.get("fetched_at"),
                    })
                else:
                    failed_urls.append({"url": url, "error": fetch_result.error_message})

            except Exception as e:
                failed_urls.append({"url": url, "error": str(e)})

        # Return structured output
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[STEP1] Returning: {len(competitors)} competitors, {len(failed_urls)} failed URLs")

        return {
            "step": self.step_id,
            "keyword": keyword,
            "competitors": competitors,
            "failed_urls": failed_urls,
            "total_found": len(urls),
            "total_fetched": len(competitors),
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
