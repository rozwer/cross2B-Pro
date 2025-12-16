"""Step 9: Final Rewrite Activity.

Performs the final rewrite incorporating fact check results and FAQ.
Uses Claude for high-quality final refinement.
"""

from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.llm.base import get_llm_client
from apps.api.llm.schemas import LLMRequestConfig
from apps.api.prompts.loader import PromptPackLoader

from .base import ActivityError, BaseActivity


class Step9FinalRewrite(BaseActivity):
    """Activity for final rewrite."""

    @property
    def step_id(self) -> str:
        return "step9"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute final rewrite.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with final rewritten content
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
        step7b_data = config.get("step7b_data", {})
        step8_data = config.get("step8_data", {})

        polished_content = step7b_data.get("polished", "")
        faq_content = step8_data.get("faq", "")
        verification = step8_data.get("verification", "")

        if not keyword:
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        if not polished_content:
            raise ActivityError(
                "polished content is required - run step7b first",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Render prompt
        try:
            prompt_template = prompt_pack.get_prompt("step9")
            prompt = prompt_template.render(
                keyword=keyword,
                polished_content=polished_content,
                faq=faq_content,
                verification_notes=verification,
            )
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client (Claude for step9 - final quality refinement)
        llm_provider = config.get("llm_provider", "anthropic")
        llm_model = config.get("llm_model")
        llm = get_llm_client(llm_provider, model=llm_model)

        # Execute LLM call
        try:
            llm_config = LLMRequestConfig(
                max_tokens=config.get("max_tokens", 8000),
                temperature=config.get("temperature", 0.6),
            )
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="Perform the final rewrite of the article.",
                config=llm_config,
            )
        except Exception as e:
            raise ActivityError(
                f"LLM call failed: {e}",
                category=ErrorCategory.RETRYABLE,
            ) from e

        # Calculate content stats
        final_content = response.content
        word_count = len(final_content.split())
        char_count = len(final_content)

        return {
            "step": self.step_id,
            "keyword": keyword,
            "final_content": final_content,
            "stats": {
                "word_count": word_count,
                "char_count": char_count,
            },
            "model": response.model,
            "usage": {
                "input_tokens": response.token_usage.input,
                "output_tokens": response.token_usage.output,
            },
        }


@activity.defn(name="step9_final_rewrite")
async def step9_final_rewrite(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 9."""
    step = Step9FinalRewrite()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
