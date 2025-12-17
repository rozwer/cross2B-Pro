"""Step 4: Strategic Outline Activity.

Creates the strategic article outline based on analysis from steps 0-3.
Uses Claude for structured outline generation.
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


class Step4StrategicOutline(BaseActivity):
    """Activity for strategic outline generation."""

    @property
    def step_id(self) -> str:
        return "step4"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute strategic outline generation.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with strategic outline
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

        # Get inputs from previous steps
        keyword = config.get("keyword")

        # Load step data from storage (not from config to avoid gRPC size limits)
        step3a_data = await load_step_data(
            self.store, ctx.tenant_id, ctx.run_id, "step3a"
        ) or {}
        step3b_data = await load_step_data(
            self.store, ctx.tenant_id, ctx.run_id, "step3b"
        ) or {}
        step3c_data = await load_step_data(
            self.store, ctx.tenant_id, ctx.run_id, "step3c"
        ) or {}

        if not keyword:
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Render prompt with all analysis inputs
        try:
            prompt_template = prompt_pack.get_prompt("step4")
            prompt = prompt_template.render(
                keyword=keyword,
                query_analysis=step3a_data.get("query_analysis", ""),
                cooccurrence_analysis=step3b_data.get("cooccurrence_analysis", ""),
                competitor_analysis=step3c_data.get("competitor_analysis", ""),
            )
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client from model_config
        model_config = config.get("model_config", {})
        llm_provider = model_config.get("platform", config.get("llm_provider", "gemini"))
        llm_model = model_config.get("model", config.get("llm_model"))
        llm = get_llm_client(llm_provider, model=llm_model)

        # Execute LLM call
        try:
            llm_config = LLMRequestConfig(
                max_tokens=config.get("max_tokens", 4000),
                temperature=config.get("temperature", 0.6),
            )
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an SEO content strategist.",
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
            "outline": response.content,
            "model": response.model,
            "usage": {
                "input_tokens": response.token_usage.input,
                "output_tokens": response.token_usage.output,
            },
        }


@activity.defn(name="step4_strategic_outline")
async def step4_strategic_outline(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 4."""
    step = Step4StrategicOutline()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
