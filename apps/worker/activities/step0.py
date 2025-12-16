"""Step 0: Keyword Selection Activity.

Analyzes input keyword to determine optimal targeting strategy.
Uses Gemini for analysis.
"""

from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.llm.base import LLMInterface, get_llm_client
from apps.api.llm.schemas import LLMRequestConfig
from apps.api.prompts.loader import PromptPackLoader

from .base import ActivityError, BaseActivity


class Step0KeywordSelection(BaseActivity):
    """Activity for keyword selection and analysis."""

    @property
    def step_id(self) -> str:
        return "step0"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute keyword selection analysis.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with keyword analysis results
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

        # Get input keyword from config
        keyword = config.get("keyword")
        if not keyword:
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Get prompt for this step
        try:
            prompt_template = prompt_pack.get_prompt("step0")
            prompt = prompt_template.render(keyword=keyword)
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client (Gemini for step0)
        llm_provider = config.get("llm_provider", "gemini")
        llm_model = config.get("llm_model")
        llm: LLMInterface = get_llm_client(llm_provider, model=llm_model)

        # Execute LLM call
        try:
            llm_config = LLMRequestConfig(
                max_tokens=config.get("max_tokens", 2000),
                temperature=config.get("temperature", 0.7),
            )
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are a keyword analysis assistant.",
                config=llm_config,
            )
        except Exception as e:
            raise ActivityError(
                f"LLM call failed: {e}",
                category=ErrorCategory.RETRYABLE,
            ) from e

        # Return structured output
        return {
            "step": self.step_id,
            "keyword": keyword,
            "analysis": response.content,
            "model": response.model,
            "usage": {
                "input_tokens": response.token_usage.input,
                "output_tokens": response.token_usage.output,
            },
        }


# Activity function for Temporal registration
@activity.defn(name="step0_keyword_selection")
async def step0_keyword_selection(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 0."""
    step = Step0KeywordSelection()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
