"""Step 3C: Competitor Analysis & Differentiation Activity.

Analyzes competitors to find differentiation opportunities.
Runs in parallel with step3a and step3b.
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


class Step3CCompetitorAnalysis(BaseActivity):
    """Activity for competitor analysis and differentiation."""

    @property
    def step_id(self) -> str:
        return "step3c"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute competitor analysis.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with competitor analysis and differentiation strategy
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

        # Prepare competitor analysis data
        competitor_analysis = []
        for comp in competitors:
            competitor_analysis.append({
                "url": comp.get("url", ""),
                "title": comp.get("title", ""),
                "content_length": len(comp.get("content", "")),
                "content_preview": comp.get("content", "")[:300],
            })

        # Render prompt
        try:
            prompt_template = prompt_pack.get_prompt("step3c")
            prompt = prompt_template.render(
                keyword=keyword,
                competitors=competitor_analysis,
            )
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client (Gemini for step3c)
        llm_provider = config.get("llm_provider", "gemini")
        llm_model = config.get("llm_model")
        llm = get_llm_client(llm_provider, model=llm_model)

        # Execute LLM call
        try:
            llm_config = LLMRequestConfig(
                max_tokens=config.get("max_tokens", 3000),
                temperature=config.get("temperature", 0.7),
            )
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are a competitor analysis expert.",
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
            "competitor_analysis": response.content,
            "competitor_count": len(competitors),
            "model": response.model,
            "usage": {
                "input_tokens": response.token_usage.input,
                "output_tokens": response.token_usage.output,
            },
        }


@activity.defn(name="step3c_competitor_analysis")
async def step3c_competitor_analysis(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 3C."""
    step = Step3CCompetitorAnalysis()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
