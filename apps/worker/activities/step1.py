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
from apps.api.tools.schemas import ToolRequest

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
        serp_tool = registry.get_tool("serp_fetch")
        if not serp_tool:
            raise ActivityError(
                "serp_fetch tool not found in registry",
                category=ErrorCategory.NON_RETRYABLE,
            )

        try:
            serp_request = ToolRequest(
                tool_id="serp_fetch",
                input_data={"query": keyword, "num_results": config.get("num_competitors", 10)},
            )
            serp_result = await serp_tool.execute(serp_request)

            if not serp_result.success:
                raise ActivityError(
                    f"SERP fetch failed: {serp_result.error}",
                    category=ErrorCategory.RETRYABLE,
                )

            urls = serp_result.output_data.get("urls", [])

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
        page_fetch_tool = registry.get_tool("page_fetch")
        if not page_fetch_tool:
            raise ActivityError(
                "page_fetch tool not found in registry",
                category=ErrorCategory.NON_RETRYABLE,
            )

        competitors = []
        failed_urls = []

        for url in urls:
            try:
                fetch_request = ToolRequest(
                    tool_id="page_fetch",
                    input_data={"url": url},
                )
                fetch_result = await page_fetch_tool.execute(fetch_request)

                if fetch_result.success:
                    competitors.append({
                        "url": url,
                        "title": fetch_result.output_data.get("title", ""),
                        "content": fetch_result.output_data.get("content", ""),
                        "fetched_at": fetch_result.output_data.get("fetched_at"),
                    })
                else:
                    failed_urls.append({"url": url, "error": fetch_result.error})

            except Exception as e:
                failed_urls.append({"url": url, "error": str(e)})

        # Return structured output
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
