"""Step 6.5: Integration Package Activity.

Creates the integrated package combining all analysis and outline work.
This is the critical handoff point before content generation.
Uses Claude for comprehensive integration.
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


class Step65IntegrationPackage(BaseActivity):
    """Activity for integration package creation."""

    @property
    def step_id(self) -> str:
        return "step6_5"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute integration package creation.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with integration package
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

        # Get ALL inputs from previous steps
        keyword = config.get("keyword")
        step0_data = config.get("step0_data", {})
        step3a_data = config.get("step3a_data", {})
        step3b_data = config.get("step3b_data", {})
        step3c_data = config.get("step3c_data", {})
        step4_data = config.get("step4_data", {})
        step5_data = config.get("step5_data", {})
        step6_data = config.get("step6_data", {})

        if not keyword:
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Prepare comprehensive input
        integration_input = {
            "keyword": keyword,
            "keyword_analysis": step0_data.get("analysis", ""),
            "query_personas": step3a_data.get("query_analysis", ""),
            "cooccurrence_keywords": step3b_data.get("cooccurrence_analysis", ""),
            "competitor_differentiation": step3c_data.get("competitor_analysis", ""),
            "strategic_outline": step4_data.get("outline", ""),
            "primary_sources": step5_data.get("sources", []),
            "enhanced_outline": step6_data.get("enhanced_outline", ""),
        }

        # Render prompt
        try:
            prompt_template = prompt_pack.get_prompt("step6_5")
            prompt = prompt_template.render(**integration_input)
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client (Claude for step6.5 - comprehensive integration)
        llm_provider = config.get("llm_provider", "anthropic")
        llm_model = config.get("llm_model")
        llm = get_llm_client(llm_provider, model=llm_model)

        # Execute LLM call
        try:
            llm_config = LLMRequestConfig(
                max_tokens=config.get("max_tokens", 6000),
                temperature=config.get("temperature", 0.5),
            )
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an SEO content integration specialist.",
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
            "integration_package": response.content,
            "inputs_summary": {
                "has_keyword_analysis": bool(step0_data),
                "has_query_analysis": bool(step3a_data),
                "has_cooccurrence": bool(step3b_data),
                "has_competitor_analysis": bool(step3c_data),
                "has_strategic_outline": bool(step4_data),
                "has_sources": len(step5_data.get("sources", [])) > 0,
                "has_enhanced_outline": bool(step6_data),
            },
            "model": response.model,
            "usage": {
                "input_tokens": response.token_usage.input,
                "output_tokens": response.token_usage.output,
            },
        }


@activity.defn(name="step6_5_integration_package")
async def step6_5_integration_package(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 6.5."""
    step = Step65IntegrationPackage()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
