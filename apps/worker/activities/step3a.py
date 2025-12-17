"""Step 3A: Query Analysis & Persona Activity.

Analyzes search query intent and builds user personas.
Runs in parallel with step3b and step3c.
Uses Gemini for analysis.
"""

import logging
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
from apps.worker.helpers import (
    CheckpointManager,
    ContentMetrics,
    InputValidator,
    OutputParser,
    QualityRetryLoop,
    RequiredElementsValidator,
)

from .base import ActivityError, BaseActivity, load_step_data

logger = logging.getLogger(__name__)


class Step3AQueryAnalysis(BaseActivity):
    """Activity for query analysis and persona building."""

    # Required elements for quality validation
    REQUIRED_ELEMENTS = {
        "search_intent": ["検索意図", "search intent", "intent"],
        "persona": ["ペルソナ", "persona", "ユーザー像"],
        "pain_points": ["課題", "pain point", "悩み"],
    }

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.parser = OutputParser()
        self.checkpoint = CheckpointManager(self.store)
        self.metrics = ContentMetrics()
        self.input_validator = InputValidator()
        self.quality_validator = RequiredElementsValidator(
            required_patterns=self.REQUIRED_ELEMENTS,
            max_missing=1,
        )

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

        # Input validation
        validation = self.input_validator.validate(
            data={"step0": step0_data, "step1": step1_data},
            required=["step0.analysis"],
            recommended=["step1.competitors"],
        )

        if not validation.is_valid:
            raise ActivityError(
                f"Input validation failed: {validation.missing_required}",
                category=ErrorCategory.NON_RETRYABLE,
            )

        if validation.missing_recommended:
            logger.warning(
                f"Missing recommended fields: {validation.missing_recommended}"
            )

        # Checkpoint: input data loaded
        input_checkpoint = await self.checkpoint.load(
            ctx.tenant_id, ctx.run_id, self.step_id, "inputs_loaded"
        )

        if not input_checkpoint:
            await self.checkpoint.save(
                ctx.tenant_id,
                ctx.run_id,
                self.step_id,
                "inputs_loaded",
                {"step0_data": step0_data, "step1_data": step1_data},
            )

        # Render prompt
        try:
            prompt_template = prompt_pack.get_prompt("step3a")
            initial_prompt = prompt_template.render(
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

        # LLM config
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

        # Define LLM call function for retry loop
        async def llm_call(prompt: str) -> Any:
            try:
                return await llm.generate(
                    messages=[{"role": "user", "content": prompt}],
                    system_prompt="You are a search query analysis expert.",
                    config=llm_config,
                    metadata=metadata,
                )
            except (LLMRateLimitError, LLMTimeoutError) as e:
                raise ActivityError(
                    f"LLM temporary failure: {e}",
                    category=ErrorCategory.RETRYABLE,
                    details={"llm_error": str(e)},
                ) from e
            except (LLMAuthenticationError, LLMInvalidRequestError) as e:
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

        # Define prompt enhancement function
        def enhance_prompt(prompt: str, issues: list[str]) -> str:
            enhancement = "\n\n【追加指示】以下の要素を必ず含めてください：\n"
            for issue in issues:
                if issue == "missing_search_intent":
                    enhancement += (
                        "- 検索意図（informational/navigational/"
                        "transactional/commercialのいずれか）\n"
                    )
                elif issue == "missing_persona":
                    enhancement += "- ユーザーペルソナ（具体的な人物像）\n"
                elif issue == "missing_pain_points":
                    enhancement += "- ユーザーの課題・悩み\n"
            return prompt + enhancement

        # Quality retry loop
        retry_loop = QualityRetryLoop(max_retries=1, accept_on_final=True)

        loop_result = await retry_loop.execute(
            llm_call=llm_call,
            initial_prompt=initial_prompt,
            validator=self.quality_validator,
            enhance_prompt=enhance_prompt,
            extract_content=lambda r: r.content,
        )

        if not loop_result.success or loop_result.result is None:
            quality_issues = (
                loop_result.quality.issues if loop_result.quality else "unknown"
            )
            raise ActivityError(
                f"Quality validation failed after retries: {quality_issues}",
                category=ErrorCategory.RETRYABLE,
            )

        response = loop_result.result
        content: str = response.content

        # Parse output (attempt JSON extraction)
        parse_result = self.parser.parse_json(content)

        if parse_result.success and isinstance(parse_result.data, dict):
            logger.info(f"Parsed JSON output: {list(parse_result.data.keys())}")

        # Calculate content metrics
        text_metrics = self.metrics.text_metrics(content)

        return {
            "step": self.step_id,
            "keyword": keyword,
            "query_analysis": content,
            "parsed_data": parse_result.data if parse_result.success else None,
            "format_detected": parse_result.format_detected,
            "model": response.model,
            "usage": {
                "input_tokens": response.token_usage.input,
                "output_tokens": response.token_usage.output,
            },
            "metrics": {
                "char_count": text_metrics.char_count,
                "word_count": text_metrics.word_count,
            },
            "quality": {
                "attempts": loop_result.attempts,
                "issues": loop_result.quality.issues if loop_result.quality else [],
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
