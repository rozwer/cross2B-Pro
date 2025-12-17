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

from .base import ActivityError, BaseActivity, load_step_data


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
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[STEP9] execute called: tenant_id={ctx.tenant_id}, run_id={ctx.run_id}")

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
        logger.info(f"[STEP9] Loading step7b and step8 data...")
        step7b_data = await load_step_data(
            self.store, ctx.tenant_id, ctx.run_id, "step7b"
        ) or {}
        step8_data = await load_step_data(
            self.store, ctx.tenant_id, ctx.run_id, "step8"
        ) or {}

        logger.info(f"[STEP9] step7b_data keys: {list(step7b_data.keys()) if step7b_data else 'None'}")
        logger.info(f"[STEP9] step8_data keys: {list(step8_data.keys()) if step8_data else 'None'}")

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
        model_config = config.get("model_config", {})
        llm_provider = model_config.get("platform", config.get("llm_provider", "anthropic"))
        llm_model = model_config.get("model", config.get("llm_model"))
        llm = get_llm_client(llm_provider, model=llm_model)

        # Execute LLM call
        try:
            # Increase max_tokens for Japanese content
            llm_config = LLMRequestConfig(
                max_tokens=config.get("max_tokens", 16000),
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

        # Process response (plain markdown, not JSON)
        logger.info(f"[STEP9] Raw response length: {len(response.content)}")
        logger.info(f"[STEP9] Raw response (first 500 chars): {response.content[:500]}")

        # The response is expected to be plain markdown
        final_content = response.content.strip()

        # Remove any code block markers if LLM still added them
        if final_content.startswith("```markdown"):
            final_content = final_content[11:]
        elif final_content.startswith("```"):
            final_content = final_content[3:]
        if final_content.endswith("```"):
            final_content = final_content[:-3]
        final_content = final_content.strip()

        if not final_content:
            raise ActivityError(
                "Empty response from LLM",
                category=ErrorCategory.RETRYABLE,
            )

        logger.info(f"[STEP9] Final content length: {len(final_content)} chars")

        # Calculate actual content stats
        word_count = len(final_content.split())
        char_count = len(final_content)

        return {
            "step": self.step_id,
            "keyword": keyword,
            "final_content": final_content,
            "meta_description": "",  # Not tracked in plain markdown response
            "internal_link_suggestions": [],  # Not tracked in plain markdown response
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
