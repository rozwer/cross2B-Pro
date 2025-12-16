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
from apps.api.prompts.loader import PromptPackLoader

from .base import ActivityError, BaseActivity


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
        step3a_data = config.get("step3a_data", {})
        step3b_data = config.get("step3b_data", {})
        step3c_data = config.get("step3c_data", {})

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

        # Get LLM client (Claude for step4 - strategic structuring)
        llm_provider = config.get("llm_provider", "anthropic")
        llm_model = config.get("llm_model")
        llm = get_llm_client(llm_provider, model=llm_model)

        # Execute LLM call
        try:
            response = await llm.generate(
                prompt=prompt,
                max_tokens=config.get("max_tokens", 4000),
                temperature=config.get("temperature", 0.6),
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
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
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
