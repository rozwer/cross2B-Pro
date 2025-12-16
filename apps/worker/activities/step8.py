"""Step 8: Fact Check Activity.

Verifies facts and claims in the polished article.
Adds FAQ section if contradictions or gaps are found.
Uses Gemini with web grounding for verification.
"""

from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.llm.base import get_llm_client
from apps.api.prompts.loader import PromptPackLoader
from apps.api.tools.registry import ToolRegistry
from apps.api.tools.schemas import ToolRequest

from .base import ActivityError, BaseActivity


class Step8FactCheck(BaseActivity):
    """Activity for fact checking and FAQ generation."""

    @property
    def step_id(self) -> str:
        return "step8"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute fact checking.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with fact check results and FAQ
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
        polished_content = step7b_data.get("polished", "")

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

        # Get LLM client (Gemini with grounding for fact checking)
        llm_provider = config.get("llm_provider", "gemini")
        llm_model = config.get("llm_model")
        llm = get_llm_client(llm_provider, model=llm_model)

        # Step 8.1: Extract claims from content
        try:
            claims_prompt = prompt_pack.get_prompt("step8_claims")
            claims_request = claims_prompt.render(content=polished_content)
            claims_response = await llm.generate(
                prompt=claims_request,
                max_tokens=2000,
                temperature=0.3,  # Low temperature for precise extraction
            )
            extracted_claims = claims_response.content
        except Exception as e:
            raise ActivityError(
                f"Failed to extract claims: {e}",
                category=ErrorCategory.RETRYABLE,
            ) from e

        # Step 8.2: Verify claims using grounding
        verification_results = []
        try:
            verify_prompt = prompt_pack.get_prompt("step8_verify")
            verify_request = verify_prompt.render(
                claims=extracted_claims,
                keyword=keyword,
            )
            verify_response = await llm.generate(
                prompt=verify_request,
                max_tokens=3000,
                temperature=0.3,
                grounding=True,  # Enable Gemini grounding for verification
            )
            verification_results = verify_response.content
        except Exception as e:
            raise ActivityError(
                f"Failed to verify claims: {e}",
                category=ErrorCategory.RETRYABLE,
            ) from e

        # Step 8.3: Generate FAQ based on verification
        try:
            faq_prompt = prompt_pack.get_prompt("step8_faq")
            faq_request = faq_prompt.render(
                keyword=keyword,
                verification=verification_results,
            )
            faq_response = await llm.generate(
                prompt=faq_request,
                max_tokens=2000,
                temperature=0.6,
            )
            faq_content = faq_response.content
        except Exception as e:
            raise ActivityError(
                f"Failed to generate FAQ: {e}",
                category=ErrorCategory.RETRYABLE,
            ) from e

        # Check for critical contradictions
        has_contradictions = "contradiction" in verification_results.lower()

        return {
            "step": self.step_id,
            "keyword": keyword,
            "claims": extracted_claims,
            "verification": verification_results,
            "faq": faq_content,
            "has_contradictions": has_contradictions,
            "recommend_rejection": has_contradictions,  # Flag for UI
            "model": llm_model or "default",
            "usage": {
                "claims_tokens": claims_response.output_tokens,
                "verify_tokens": verify_response.output_tokens,
                "faq_tokens": faq_response.output_tokens,
            },
        }


@activity.defn(name="step8_fact_check")
async def step8_fact_check(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 8."""
    step = Step8FactCheck()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
