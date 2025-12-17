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
from apps.api.llm.schemas import LLMRequestConfig
from apps.api.prompts.loader import PromptPackLoader

from .base import ActivityError, BaseActivity, load_step_data


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

        # Load step data from storage (not from config to avoid gRPC size limits)
        step7a_data = await load_step_data(
            self.store, ctx.tenant_id, ctx.run_id, "step7a"
        ) or {}
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
        import logging
        logger = logging.getLogger(__name__)

        model_config = config.get("model_config", {})
        llm_provider = model_config.get("platform", config.get("llm_provider", "gemini"))
        llm_model = model_config.get("model", config.get("llm_model"))
        llm = get_llm_client(llm_provider, model=llm_model)

        logger.info(f"[STEP7B] Starting LLM call - provider: {llm_provider}, model: {llm_model}")
        logger.info(f"[STEP7B] Draft length: {len(draft)} chars")

        # Execute LLM call
        try:
            # Increase max_tokens for Japanese content (higher token count per character)
            llm_config = LLMRequestConfig(
                max_tokens=config.get("max_tokens", 16000),
                temperature=config.get("temperature", 0.8),  # Slightly higher for creativity
            )
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are a content polishing expert.",
                config=llm_config,
            )
        except Exception as e:
            logger.error(f"[STEP7B] LLM call exception: {type(e).__name__}: {e}")
            raise ActivityError(
                f"LLM call failed: {e}",
                category=ErrorCategory.RETRYABLE,
            ) from e

        # Process response (plain markdown, not JSON)
        logger.info(f"[STEP7B] LLM call completed successfully")
        logger.info(f"[STEP7B] Raw response length: {len(response.content)}")
        logger.info(f"[STEP7B] Raw response (first 500 chars): {response.content[:500]}")

        # The response is expected to be plain markdown
        polished_content = response.content.strip()

        # Remove any code block markers if LLM still added them
        if polished_content.startswith("```markdown"):
            polished_content = polished_content[11:]
        elif polished_content.startswith("```"):
            polished_content = polished_content[3:]
        if polished_content.endswith("```"):
            polished_content = polished_content[:-3]
        polished_content = polished_content.strip()

        if not polished_content:
            raise ActivityError(
                "Empty response from LLM",
                category=ErrorCategory.RETRYABLE,
            )

        logger.info(f"[STEP7B] Polished content length: {len(polished_content)} chars")

        # Calculate actual content stats
        word_count = len(polished_content.split())
        char_count = len(polished_content)

        # Compare with original
        original_word_count = len(draft.split())
        word_diff = word_count - original_word_count

        return {
            "step": self.step_id,
            "keyword": keyword,
            "polished": polished_content,
            "changes_made": [],  # Not tracked in plain markdown response
            "stats": {
                "word_count": word_count,
                "char_count": char_count,
                "word_diff_from_draft": word_diff,
            },
            "model": response.model,
            "usage": {
                "input_tokens": response.token_usage.input,
                "output_tokens": response.token_usage.output,
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
