"""Step 3B: Co-occurrence & Related Keywords Extraction Activity.

This is the HEART of the SEO analysis - extracts co-occurrence patterns
and related keywords from competitor content.
Runs in parallel with step3a and step3c.
Uses Gemini for analysis.
"""

from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.llm.base import get_llm_client
from apps.api.llm.schemas import LLMRequestConfig
from apps.api.prompts.loader import PromptPackLoader

from .base import ActivityError, BaseActivity, load_step_data


class Step3BCooccurrenceExtraction(BaseActivity):
    """Activity for co-occurrence and keyword extraction.

    This is the critical "heart" step of the workflow.
    """

    @property
    def step_id(self) -> str:
        return "step3b"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute co-occurrence extraction.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with extracted keywords and patterns
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

        # Load step data from storage (not from config to avoid gRPC size limits)
        step1_data = await load_step_data(
            self.store, ctx.tenant_id, ctx.run_id, "step1"
        ) or {}
        competitors = step1_data.get("competitors", [])

        if not keyword:
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        if not competitors:
            raise ActivityError(
                "competitor data is required - run step1 first",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Prepare competitor content summary for prompt
        competitor_summaries = []
        for comp in competitors[:5]:  # Limit to top 5 for token efficiency
            competitor_summaries.append({
                "title": comp.get("title", ""),
                "content_preview": comp.get("content", "")[:500],  # First 500 chars
            })

        # Render prompt
        try:
            prompt_template = prompt_pack.get_prompt("step3b")
            prompt = prompt_template.render(
                keyword=keyword,
                competitor_summaries=competitor_summaries,
            )
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client (Gemini for step3b - grounding enabled)
        llm_provider = config.get("llm_provider", "gemini")
        llm_model = config.get("llm_model")
        llm = get_llm_client(llm_provider, model=llm_model)

        # Execute LLM call with grounding for search data
        try:
            llm_config = LLMRequestConfig(
                max_tokens=config.get("max_tokens", 4000),
                temperature=config.get("temperature", 0.5),  # Lower for consistent extraction
            )
            # Note: Grounding is Gemini-specific, handled by the client
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are a co-occurrence keyword analysis expert.",
                config=llm_config,
            )
        except Exception as e:
            raise ActivityError(
                f"LLM call failed: {e}",
                category=ErrorCategory.RETRYABLE,
            ) from e

        return {
            "step": self.step_id,
            "keyword": keyword,
            "cooccurrence_analysis": response.content,
            "competitor_count": len(competitors),
            "model": response.model,
            "usage": {
                "input_tokens": response.token_usage.input,
                "output_tokens": response.token_usage.output,
            },
        }


@activity.defn(name="step3b_cooccurrence_extraction")
async def step3b_cooccurrence_extraction(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 3B."""
    step = Step3BCooccurrenceExtraction()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
