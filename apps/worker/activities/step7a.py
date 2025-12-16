"""Step 7A: Draft Generation Activity.

Generates the first draft of the article based on integration package.
This is the longest step (600s timeout) due to long-form content generation.
Uses Claude for high-quality content generation.
"""

from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.llm.base import get_llm_client
from apps.api.prompts.loader import PromptPackLoader

from .base import ActivityError, BaseActivity


class Step7ADraftGeneration(BaseActivity):
    """Activity for article draft generation."""

    @property
    def step_id(self) -> str:
        return "step7a"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute draft generation.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with draft content
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
        step6_5_data = config.get("step6_5_data", {})
        integration_package = step6_5_data.get("integration_package", "")

        if not keyword:
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        if not integration_package:
            raise ActivityError(
                "integration_package is required - run step6.5 first",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Render prompt
        try:
            prompt_template = prompt_pack.get_prompt("step7a")
            prompt = prompt_template.render(
                keyword=keyword,
                integration_package=integration_package,
            )
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client (Claude for step7a - long-form content)
        llm_provider = config.get("llm_provider", "anthropic")
        llm_model = config.get("llm_model")
        llm = get_llm_client(llm_provider, model=llm_model)

        # Execute LLM call with higher token limit for long-form content
        try:
            response = await llm.generate(
                prompt=prompt,
                max_tokens=config.get("max_tokens", 8000),
                temperature=config.get("temperature", 0.7),
            )
        except Exception as e:
            raise ActivityError(
                f"LLM call failed: {e}",
                category=ErrorCategory.RETRYABLE,
            ) from e

        # Calculate content stats
        draft_content = response.content
        word_count = len(draft_content.split())
        char_count = len(draft_content)

        return {
            "step": self.step_id,
            "keyword": keyword,
            "draft": draft_content,
            "stats": {
                "word_count": word_count,
                "char_count": char_count,
            },
            "model": response.model,
            "usage": {
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
            },
        }


@activity.defn(name="step7a_draft_generation")
async def step7a_draft_generation(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 7A."""
    step = Step7ADraftGeneration()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
