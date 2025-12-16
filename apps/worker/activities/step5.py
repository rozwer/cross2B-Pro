"""Step 5: Primary Source Collection Activity.

Collects primary sources (academic papers, official documents, statistics)
to support article claims with credible evidence.
Uses Tools (Web search, PDF extraction) and Gemini.
"""

from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.llm.base import get_llm_client
from apps.api.prompts.loader import PromptPackLoader
from apps.api.tools.registry import ToolRegistry
from apps.api.tools.schemas import ToolRequest

from .base import ActivityError, BaseActivity


class Step5PrimaryCollection(BaseActivity):
    """Activity for primary source collection."""

    @property
    def step_id(self) -> str:
        return "step5"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute primary source collection.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with collected primary sources
        """
        config = ctx.config
        pack_id = config.get("pack_id")

        if not pack_id:
            raise ActivityError(
                "pack_id is required",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Load prompt pack
        loader = PromptPackLoader()
        prompt_pack = loader.load(pack_id)

        # Get inputs
        keyword = config.get("keyword")
        step4_data = config.get("step4_data", {})
        outline = step4_data.get("outline", "")

        if not keyword:
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Step 5.1: Generate search queries using LLM
        llm_provider = config.get("llm_provider", "gemini")
        llm_model = config.get("llm_model")
        llm = get_llm_client(llm_provider, model=llm_model)

        try:
            query_prompt = prompt_pack.get_prompt("step5_queries")
            query_request = query_prompt.render(
                keyword=keyword,
                outline=outline,
            )
            query_response = await llm.generate(
                prompt=query_request,
                max_tokens=1000,
                temperature=0.5,
            )
            # Parse search queries from response
            search_queries = self._parse_queries(query_response.content)
        except Exception as e:
            # Fall back to basic queries if parsing fails
            search_queries = [
                f"{keyword} research statistics",
                f"{keyword} official data",
                f"{keyword} academic study",
            ]

        # Step 5.2: Execute searches using primary_collector tool
        registry = ToolRegistry()
        primary_collector = registry.get_tool("primary_collector")

        collected_sources = []
        failed_queries = []

        if primary_collector:
            for query in search_queries[:5]:  # Limit to 5 queries
                try:
                    request = ToolRequest(
                        tool_id="primary_collector",
                        input_data={"query": query},
                    )
                    result = await primary_collector.execute(request)

                    if result.success:
                        sources = result.output_data.get("evidence_refs", [])
                        collected_sources.extend(sources)
                    else:
                        failed_queries.append({
                            "query": query,
                            "error": result.error,
                        })
                except Exception as e:
                    failed_queries.append({
                        "query": query,
                        "error": str(e),
                    })
        else:
            # If tool not available, note it as a warning
            failed_queries.append({
                "query": "all",
                "error": "primary_collector tool not available",
            })

        # Step 5.3: Verify URLs
        url_verify = registry.get_tool("url_verify")
        verified_sources = []
        invalid_sources = []

        if url_verify:
            for source in collected_sources:
                try:
                    verify_request = ToolRequest(
                        tool_id="url_verify",
                        input_data={"url": source.get("url", "")},
                    )
                    verify_result = await url_verify.execute(verify_request)

                    if verify_result.success and verify_result.output_data.get("status") == 200:
                        source["verified"] = True
                        verified_sources.append(source)
                    else:
                        source["verified"] = False
                        invalid_sources.append(source)
                except Exception:
                    source["verified"] = False
                    invalid_sources.append(source)
        else:
            # If no verification tool, mark all as unverified
            for source in collected_sources:
                source["verified"] = False
            verified_sources = collected_sources

        # Check if we have ANY valid sources
        if not verified_sources and not collected_sources:
            raise ActivityError(
                "Failed to collect any primary sources",
                category=ErrorCategory.NON_RETRYABLE,
                details={"failed_queries": failed_queries},
            )

        return {
            "step": self.step_id,
            "keyword": keyword,
            "sources": verified_sources,
            "invalid_sources": invalid_sources,
            "search_queries": search_queries,
            "failed_queries": failed_queries,
            "total_collected": len(collected_sources),
            "total_verified": len(verified_sources),
        }

    def _parse_queries(self, content: str) -> list[str]:
        """Parse search queries from LLM response."""
        queries = []
        for line in content.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                # Remove numbering like "1. " or "- "
                if line[0].isdigit():
                    line = line.split(".", 1)[-1].strip()
                elif line.startswith("-"):
                    line = line[1:].strip()
                if line:
                    queries.append(line)
        return queries[:5]  # Max 5 queries


@activity.defn(name="step5_primary_collection")
async def step5_primary_collection(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 5."""
    step = Step5PrimaryCollection()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
