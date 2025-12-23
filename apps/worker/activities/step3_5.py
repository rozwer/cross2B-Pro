"""Step 3.5: Human Touch Generation Activity.

Generates emotional analysis, human-like expressions, and experience episodes
based on previous step outputs. Runs after approval as the first post-approval step.
Uses Gemini for natural, creative expression generation.
"""

import logging
from datetime import datetime
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


class Step3_5HumanTouchGeneration(BaseActivity):
    """Activity for generating human touch elements.

    Takes outputs from step0, step1, step1_5 (optional), step3a, step3b, step3c
    and generates emotional analysis, human-touch patterns, and experience episodes.
    """

    REQUIRED_ELEMENTS = {
        "emotional_analysis": ["感情", "emotion", "心情"],
        "human_touch": ["人間味", "human", "体験"],
        "experience": ["エピソード", "episode", "体験談"],
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
        return "step3_5"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute human touch generation.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with human touch elements
        """
        config = ctx.config
        pack_id = config.get("pack_id")

        if not pack_id:
            raise ActivityError(
                "pack_id is required",
                category=ErrorCategory.NON_RETRYABLE,
            )

        loader = PromptPackLoader()
        prompt_pack = loader.load(pack_id)

        keyword = config.get("keyword")
        if not keyword:
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Load previous step outputs from storage
        step0_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step0") or {}
        step1_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step1") or {}
        step1_5_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step1_5")  # Optional, may be None
        step3a_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step3a") or {}
        step3b_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step3b") or {}
        step3c_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step3c") or {}

        # Track which input files were available
        input_files = ["step0", "step1", "step3a", "step3b", "step3c"]
        if step1_5_data:
            input_files.append("step1_5")

        # Input validation - step1_5 is optional
        validation = self.input_validator.validate(
            data={
                "step0": step0_data,
                "step1": step1_data,
                "step3a": step3a_data,
                "step3b": step3b_data,
                "step3c": step3c_data,
            },
            required=["step0", "step3a"],
            recommended=["step1", "step3b", "step3c"],
        )

        if not validation.is_valid:
            raise ActivityError(
                f"Input validation failed: {validation.missing_required}",
                category=ErrorCategory.NON_RETRYABLE,
            )

        if validation.missing_recommended:
            logger.warning(f"Missing recommended fields: {validation.missing_recommended}")

        # Checkpoint: input data loaded
        input_checkpoint = await self.checkpoint.load(ctx.tenant_id, ctx.run_id, self.step_id, "inputs_loaded")

        if not input_checkpoint:
            await self.checkpoint.save(
                ctx.tenant_id,
                ctx.run_id,
                self.step_id,
                "inputs_loaded",
                {
                    "input_files": input_files,
                    "step0_keys": list(step0_data.keys()),
                    "step3a_keys": list(step3a_data.keys()),
                },
            )

        # Extract relevant data for prompt
        persona_info = step3a_data.get("query_analysis", "")
        if isinstance(persona_info, dict):
            persona_info = str(persona_info)

        cooccurrence_keywords = step3b_data.get("cooccurrence_analysis", "")
        if isinstance(cooccurrence_keywords, dict):
            cooccurrence_keywords = str(cooccurrence_keywords)

        competitor_insights = step3c_data.get("competitor_analysis", "")
        if isinstance(competitor_insights, dict):
            competitor_insights = str(competitor_insights)

        # Render prompt
        try:
            prompt_template = prompt_pack.get_prompt("step3_5")
            initial_prompt = prompt_template.render(
                keyword=keyword,
                persona=persona_info,
                competitor_insights=competitor_insights,
                cooccurrence_keywords=cooccurrence_keywords,
            )
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client (Gemini for step3_5 - natural expression)
        llm_provider = config.get("llm_provider", "gemini")
        llm_model = config.get("llm_model")
        llm = get_llm_client(llm_provider, model=llm_model)

        # LLM config - slightly higher temperature for creativity
        llm_config = LLMRequestConfig(
            max_tokens=config.get("max_tokens", 4000),
            temperature=config.get("temperature", 0.7),
        )
        metadata = LLMCallMetadata(
            run_id=ctx.run_id,
            step_id=self.step_id,
            attempt=ctx.attempt,
            tenant_id=ctx.tenant_id,
        )

        async def llm_call(prompt: str) -> Any:
            try:
                return await llm.generate(
                    messages=[{"role": "user", "content": prompt}],
                    system_prompt="You are an expert at creating emotionally resonant, human-centered content.",
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

        def enhance_prompt(prompt: str, issues: list[str]) -> str:
            enhancement = "\n\n【追加指示】以下の要素を必ず含めてください：\n"
            for issue in issues:
                if issue == "missing_emotional_analysis":
                    enhancement += "- 感情分析（読者の心情・感情の傾向）\n"
                elif issue == "missing_human_touch":
                    enhancement += "- 人間味のある表現パターン（体験談、感情表現、共感フレーズ）\n"
                elif issue == "missing_experience":
                    enhancement += "- 具体的な体験エピソード（シナリオ、ナラティブ、教訓）\n"
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
            quality_issues = loop_result.quality.issues if loop_result.quality else "unknown"
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
            "human_touch_elements": content,
            "parsed_data": parse_result.data if parse_result.success else None,
            "format_detected": parse_result.format_detected,
            "input_files": input_files,
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
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "model": response.model,
                "input_files": input_files,
            },
        }


@activity.defn(name="step3_5_human_touch_generation")
async def step3_5_human_touch_generation(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 3.5."""
    step = Step3_5HumanTouchGeneration()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
