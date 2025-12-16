"""Step 7B: Brush Up Activity.

Polishes and improves the draft with natural language and flow.
Uses Gemini for natural language enhancement.
"""

from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.llm.base import get_llm_client
from apps.api.prompts.loader import PromptPackLoader

from .base import ActivityError, BaseActivity


class Step7BBrushUp(BaseActivity):
    """Activity for draft polishing and brush up."""

    @property
    def step_id(self) -> str:
        return "step7b"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute draft brush up.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with polished content
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
        step7a_data = config.get("step7a_data", {})
        draft = step7a_data.get("draft", "")

        if not keyword:
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        if not draft:
            raise ActivityError(
                "draft is required - run step7a first",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Render prompt
        try:
            prompt_template = prompt_pack.get_prompt("step7b")
            prompt = prompt_template.render(
                keyword=keyword,
                draft=draft,
            )
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client (Gemini for step7b - natural language polish)
        llm_provider = config.get("llm_provider", "gemini")
        llm_model = config.get("llm_model")
        llm = get_llm_client(llm_provider, model=llm_model)

        # Execute LLM call
        try:
            response = await llm.generate(
                prompt=prompt,
                max_tokens=config.get("max_tokens", 8000),
                temperature=config.get("temperature", 0.8),  # Slightly higher for creativity
            )
        except Exception as e:
            raise ActivityError(
                f"LLM call failed: {e}",
                category=ErrorCategory.RETRYABLE,
            ) from e

        # Calculate content stats
        polished_content = response.content
        word_count = len(polished_content.split())
        char_count = len(polished_content)

        # Compare with original
        original_word_count = len(draft.split())
        word_diff = word_count - original_word_count

        return {
            "step": self.step_id,
            "keyword": keyword,
            "polished": polished_content,
            "stats": {
                "word_count": word_count,
                "char_count": char_count,
                "word_diff_from_draft": word_diff,
            },
            "model": response.model,
            "usage": {
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
            },
        }


@activity.defn(name="step7b_brush_up")
async def step7b_brush_up(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 7B."""
    step = Step7BBrushUp()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
