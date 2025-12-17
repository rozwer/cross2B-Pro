"""Step 7A: Draft Generation Activity.

Generates the first draft of the article based on integration package.
This is the longest step (600s timeout) due to long-form content generation.
Uses Claude for high-quality content generation.
"""

import json
from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.llm.base import get_llm_client
from apps.api.llm.schemas import LLMRequestConfig
from apps.api.prompts.loader import PromptPackLoader

from .base import ActivityError, BaseActivity, load_step_data


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

        # Load step data from storage (not from config to avoid gRPC size limits)
        step6_5_data = await load_step_data(
            self.store, ctx.tenant_id, ctx.run_id, "step6_5"
        ) or {}
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
        model_config = config.get("model_config", {})
        llm_provider = model_config.get("platform", config.get("llm_provider", "anthropic"))
        llm_model = model_config.get("model", config.get("llm_model"))
        llm = get_llm_client(llm_provider, model=llm_model)

        # Execute LLM call with higher token limit for long-form content
        try:
            llm_config = LLMRequestConfig(
                max_tokens=config.get("max_tokens", 8000),
                temperature=config.get("temperature", 0.7),
            )
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an SEO content writer.",
                config=llm_config,
            )
        except Exception as e:
            raise ActivityError(
                f"LLM call failed: {e}",
                category=ErrorCategory.RETRYABLE,
            ) from e

        # Parse JSON response
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[STEP7A] Raw response length: {len(response.content)}")
        logger.info(f"[STEP7A] Raw response (first 1000 chars): {response.content[:1000]}")

        try:
            # Handle markdown code blocks
            content = response.content.strip()
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                if end > start:
                    content = content[start:end].strip()
            elif "```" in content:
                start = content.find("```") + 3
                end = content.find("```", start)
                if end > start:
                    content = content[start:end].strip()

            if not content:
                raise ActivityError(
                    "Empty response from LLM",
                    category=ErrorCategory.RETRYABLE,
                )

            parsed = json.loads(content)
            draft_content = parsed.get("draft", "")
            llm_word_count = parsed.get("word_count", 0)
            section_count = parsed.get("section_count", 0)
            cta_positions = parsed.get("cta_positions", [])
        except json.JSONDecodeError as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"[STEP7A] JSON parse error. Response content (first 500 chars): {response.content[:500]}")
            raise ActivityError(
                f"Failed to parse JSON response: {e}",
                category=ErrorCategory.RETRYABLE,
            ) from e

        # Calculate actual content stats
        word_count = len(draft_content.split())
        char_count = len(draft_content)

        return {
            "step": self.step_id,
            "keyword": keyword,
            "draft": draft_content,
            "section_count": section_count,
            "cta_positions": cta_positions,
            "stats": {
                "word_count": word_count,
                "char_count": char_count,
                "llm_reported_word_count": llm_word_count,
            },
            "model": response.model,
            "usage": {
                "input_tokens": response.token_usage.input,
                "output_tokens": response.token_usage.output,
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
