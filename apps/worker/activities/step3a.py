"""Step 3A: Query Analysis & Persona Activity.

Analyzes search query intent and builds user personas.
Runs in parallel with step3b and step3c.
Uses Gemini for analysis.
"""

from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.llm.base import get_llm_client
from apps.api.llm.exceptions import (
    LLMAuthenticationError,
    LLMInvalidRequestError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from apps.api.llm.schemas import LLMCallMetadata, LLMRequestConfig
from apps.api.prompts.loader import PromptPackLoader

from .base import ActivityError, BaseActivity, load_step_data


class Step3AQueryAnalysis(BaseActivity):
    """Activity for query analysis and persona building."""

    @property
    def step_id(self) -> str:
        return "step3a"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute query analysis.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with query analysis and personas
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
        step0_data = await load_step_data(
            self.store, ctx.tenant_id, ctx.run_id, "step0"
        ) or {}
        step1_data = await load_step_data(
            self.store, ctx.tenant_id, ctx.run_id, "step1"
        ) or {}

        if not keyword:
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Render prompt
        try:
            prompt_template = prompt_pack.get_prompt("step3a")
            prompt = prompt_template.render(
                keyword=keyword,
                keyword_analysis=step0_data.get("analysis", ""),
                competitor_count=len(step1_data.get("competitors", [])),
            )
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client (Gemini for step3a)
        llm_provider = config.get("llm_provider", "gemini")
        llm_model = config.get("llm_model")
        llm = get_llm_client(llm_provider, model=llm_model)

        # Execute LLM call with metadata for traceability
        llm_config = LLMRequestConfig(
            max_tokens=config.get("max_tokens", 3000),
            temperature=config.get("temperature", 0.7),
        )
        metadata = LLMCallMetadata(
            run_id=ctx.run_id,
            step_id=self.step_id,
            attempt=ctx.attempt,
            tenant_id=ctx.tenant_id,
        )
        try:
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are a search query analysis expert.",
                config=llm_config,
                metadata=metadata,
            )
        except (LLMRateLimitError, LLMTimeoutError) as e:
            # RETRYABLE errors - rate limit and timeout
            raise ActivityError(
                f"LLM temporary failure: {e}",
                category=ErrorCategory.RETRYABLE,
                details={"llm_error": str(e)},
            ) from e
        except (LLMAuthenticationError, LLMInvalidRequestError) as e:
            # NON_RETRYABLE errors - auth and invalid requests
            raise ActivityError(
                f"LLM permanent failure: {e}",
                category=ErrorCategory.NON_RETRYABLE,
                details={"llm_error": str(e)},
            ) from e
        except Exception as e:
            raise ActivityError(
                f"LLM call failed: {e}",
                category=ErrorCategory.RETRYABLE,
            ) from e

        return {
            "step": self.step_id,
            "keyword": keyword,
            "query_analysis": response.content,
            "model": response.model,
            "usage": {
                "input_tokens": response.token_usage.input,
                "output_tokens": response.token_usage.output,
            },
        }


@activity.defn(name="step3a_query_analysis")
async def step3a_query_analysis(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 3A."""
    step = Step3AQueryAnalysis()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
