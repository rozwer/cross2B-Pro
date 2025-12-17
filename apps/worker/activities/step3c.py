"""Step 3C: Competitor Analysis & Differentiation Activity.

Analyzes competitors to find differentiation opportunities.
Runs in parallel with step3a and step3b.
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
    QualityResult,
    QualityRetryLoop,
)

from .base import ActivityError, BaseActivity, load_step_data

logger = logging.getLogger(__name__)


class Step3CQualityValidator:
    """Quality validator for competitor analysis."""

    def validate(self, content: str, **kwargs: str) -> QualityResult:
        """Validate competitor analysis quality.

        Checks:
        1. Differentiation analysis keywords
        2. Presence of recommendations
        """
        issues: list[str] = []
        content_lower = content.lower()

        # Check for differentiation keywords
        differentiation_keywords = [
            "差別化",
            "differentiation",
            "独自",
            "unique",
            "強み",
            "strength",
            "弱み",
            "weakness",
        ]
        found = sum(1 for kw in differentiation_keywords if kw in content_lower)
        if found < 2:
            issues.append("insufficient_differentiation_analysis")

        # Check for recommendation keywords
        recommendation_indicators = [
            "推奨",
            "recommend",
            "すべき",
            "should",
            "提案",
            "suggest",
            "戦略",
            "strategy",
        ]
        found_rec = sum(1 for kw in recommendation_indicators if kw in content_lower)
        if found_rec < 1:
            issues.append("no_recommendations")

        return QualityResult(
            is_acceptable=len(issues) <= 1,
            issues=issues,
        )


class Step3CCompetitorAnalysis(BaseActivity):
    """Activity for competitor analysis and differentiation."""

    # Quality thresholds
    MIN_COMPETITORS = 2
    MIN_CONTENT_PER_COMPETITOR = 200

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.parser = OutputParser()
        self.checkpoint = CheckpointManager(self.store)
        self.metrics = ContentMetrics()
        self.input_validator = InputValidator()
        self.quality_validator = Step3CQualityValidator()

    @property
    def step_id(self) -> str:
        return "step3c"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute competitor analysis.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with competitor analysis and differentiation strategy
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
        step1_data = await load_step_data(
            self.store, ctx.tenant_id, ctx.run_id, "step1"
        ) or {}
        competitors = step1_data.get("competitors", [])

        if not keyword:
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Input validation
        validation = self.input_validator.validate(
            data={"step1": step1_data},
            required=["step1.competitors"],
        )

        if not validation.is_valid:
            raise ActivityError(
                f"Input validation failed: {validation.missing_required}",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Filter quality competitors (minimum content length)
        quality_competitors = [
            c
            for c in competitors
            if len(c.get("content", "")) >= self.MIN_CONTENT_PER_COMPETITOR
        ]

        if len(quality_competitors) < self.MIN_COMPETITORS:
            raise ActivityError(
                f"Insufficient quality competitors: {len(quality_competitors)} "
                f"(minimum: {self.MIN_COMPETITORS})",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Checkpoint: analysis data
        analysis_checkpoint = await self.checkpoint.load(
            ctx.tenant_id, ctx.run_id, self.step_id, "analysis_data"
        )

        if analysis_checkpoint:
            competitor_analysis = analysis_checkpoint["competitor_analysis"]
        else:
            competitor_analysis = self._prepare_competitor_analysis(quality_competitors)
            await self.checkpoint.save(
                ctx.tenant_id,
                ctx.run_id,
                self.step_id,
                "analysis_data",
                {"competitor_analysis": competitor_analysis},
            )

        # Render prompt
        try:
            prompt_template = prompt_pack.get_prompt("step3c")
            initial_prompt = prompt_template.render(
                keyword=keyword,
                competitors=competitor_analysis,
            )
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client (Gemini for step3c)
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
                    system_prompt="You are a competitor analysis expert.",
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
            enhancement = "\n\n【追加指示】以下を必ず含めてください：\n"
            for issue in issues:
                if issue == "insufficient_differentiation_analysis":
                    enhancement += "- 各競合の強み・弱みの分析\n"
                    enhancement += "- 差別化ポイントの明示\n"
                elif issue == "no_recommendations":
                    enhancement += "- 具体的な戦略・提案\n"
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

        # Parse output
        parse_result = self.parser.parse_json(content)

        if parse_result.success and isinstance(parse_result.data, dict):
            logger.info(f"Parsed JSON output: {list(parse_result.data.keys())}")

        # Calculate content metrics
        text_metrics = self.metrics.text_metrics(content)

        return {
            "step": self.step_id,
            "keyword": keyword,
            "competitor_analysis": content,
            "parsed_data": parse_result.data if parse_result.success else None,
            "format_detected": parse_result.format_detected,
            "competitor_count": len(competitors),
            "quality_competitor_count": len(quality_competitors),
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

    def _prepare_competitor_analysis(
        self, competitors: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Prepare competitor analysis data for prompt."""
        analysis = []
        for comp in competitors:
            analysis.append({
                "url": comp.get("url", ""),
                "title": comp.get("title", ""),
                "content_length": len(comp.get("content", "")),
                "content_preview": comp.get("content", "")[:300],
            })
        return analysis


@activity.defn(name="step3c_competitor_analysis")
async def step3c_competitor_analysis(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 3C."""
    step = Step3CCompetitorAnalysis()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
