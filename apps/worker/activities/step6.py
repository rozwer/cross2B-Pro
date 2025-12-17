"""Step 6: Enhanced Outline Activity.

Enhances the strategic outline with primary sources and detailed structure.
Uses Claude for comprehensive outline enhancement.
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


class Step6EnhancedOutline(BaseActivity):
    """Activity for enhanced outline generation."""

    @property
    def step_id(self) -> str:
        return "step6"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute enhanced outline generation.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with enhanced outline
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
        step4_data = await load_step_data(
            self.store, ctx.tenant_id, ctx.run_id, "step4"
        ) or {}
        step5_data = await load_step_data(
            self.store, ctx.tenant_id, ctx.run_id, "step5"
        ) or {}

        if not keyword:
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Prepare source summaries
        sources = step5_data.get("sources", [])
        source_summaries = [
            {
                "url": s.get("url", ""),
                "title": s.get("title", ""),
                "excerpt": s.get("excerpt", "")[:200],
            }
            for s in sources[:10]  # Top 10 sources
        ]

        # Render prompt
        try:
            prompt_template = prompt_pack.get_prompt("step6")
            prompt = prompt_template.render(
                keyword=keyword,
                outline=step4_data.get("outline", ""),
                sources=source_summaries,
            )
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client (Claude for step6)
        model_config = config.get("model_config", {})
        llm_provider = model_config.get("platform", config.get("llm_provider", "anthropic"))
        llm_model = model_config.get("model", config.get("llm_model"))
        llm = get_llm_client(llm_provider, model=llm_model)

        # Execute LLM call
        try:
            llm_config = LLMRequestConfig(
                max_tokens=config.get("max_tokens", 5000),
                temperature=config.get("temperature", 0.6),
            )
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an SEO content outline specialist.",
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
            "enhanced_outline": response.content,
            "sources_used": len(source_summaries),
            "model": response.model,
            "usage": {
                "input_tokens": response.token_usage.input,
                "output_tokens": response.token_usage.output,
            },
        }


@activity.defn(name="step6_enhanced_outline")
async def step6_enhanced_outline(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 6."""
    step = Step6EnhancedOutline()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
