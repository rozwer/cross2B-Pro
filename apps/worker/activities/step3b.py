"""Step 3B: Co-occurrence & Related Keywords Extraction Activity.

This is the HEART of the SEO analysis - extracts co-occurrence patterns
and related keywords from competitor content.
Runs in parallel with step3a and step3c.
Uses Gemini for analysis.

IMPORTANT: This step applies strict quality standards as the core of the workflow.
"""

import logging
import re
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


class Step3BQualityValidator:
    """Strict quality validator for step3b (heart of workflow)."""

    def validate(self, content: str, **kwargs: str) -> QualityResult:
        """Validate co-occurrence extraction quality.

        Checks:
        1. Presence of keyword list indicators
        2. Presence of keyword category patterns
        """
        issues: list[str] = []

        # Check for keyword list indicators
        list_indicators = ["・", "-", "*", "1.", "2."]
        has_list = any(ind in content for ind in list_indicators)
        if not has_list:
            issues.append("no_keyword_list")

        # Check for keyword category patterns
        keyword_patterns = [
            r"関連キーワード|related keyword",
            r"共起|co-occur",
            r"LSI|latent semantic",
        ]
        found_patterns = sum(
            1 for p in keyword_patterns if re.search(p, content, re.I)
        )
        if found_patterns < 1:
            issues.append("no_keyword_categories")

        return QualityResult(
            is_acceptable=len(issues) <= 1,
            issues=issues,
        )


class Step3BCooccurrenceExtraction(BaseActivity):
    """Activity for co-occurrence and keyword extraction.

    This is the critical "heart" step of the workflow.
    Quality standards are STRICT.
    """

    # Strict quality thresholds
    MIN_COOCCURRENCE_KEYWORDS = 10
    MIN_LSI_KEYWORDS = 5
    MIN_COMPETITORS_FOR_QUALITY = 3

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.parser = OutputParser()
        self.checkpoint = CheckpointManager(self.store)
        self.metrics = ContentMetrics()
        self.input_validator = InputValidator()
        self.quality_validator = Step3BQualityValidator()

    @property
    def step_id(self) -> str:
        return "step3b"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute co-occurrence extraction.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with extracted keywords and patterns
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
        competitors = step1_data.get("competitors", [])

        if not keyword:
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Input validation
        validation = self.input_validator.validate(
            data={"step1": step1_data, "step0": step0_data},
            required=["step1.competitors"],
            recommended=["step0.analysis"],
            min_counts={"step1.competitors": self.MIN_COMPETITORS_FOR_QUALITY},
        )

        if not validation.is_valid:
            raise ActivityError(
                f"Input validation failed: {validation.missing_required}",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Strict competitor count check (heart of workflow)
        if len(competitors) < self.MIN_COMPETITORS_FOR_QUALITY:
            raise ActivityError(
                f"Insufficient competitor data: {len(competitors)} "
                f"(minimum: {self.MIN_COMPETITORS_FOR_QUALITY})",
                category=ErrorCategory.NON_RETRYABLE,
            )

        if validation.missing_recommended:
            logger.warning(
                f"Missing recommended fields: {validation.missing_recommended}"
            )

        if validation.quality_issues:
            logger.warning(f"Input quality issues: {validation.quality_issues}")

        # Checkpoint: competitor summaries
        summaries_checkpoint = await self.checkpoint.load(
            ctx.tenant_id, ctx.run_id, self.step_id, "competitor_summaries"
        )

        if summaries_checkpoint:
            competitor_summaries = summaries_checkpoint["summaries"]
        else:
            competitor_summaries = self._prepare_competitor_summaries(competitors)
            await self.checkpoint.save(
                ctx.tenant_id,
                ctx.run_id,
                self.step_id,
                "competitor_summaries",
                {"summaries": competitor_summaries},
            )

        # Render prompt
        try:
            prompt_template = prompt_pack.get_prompt("step3b")
            initial_prompt = prompt_template.render(
                keyword=keyword,
                competitor_summaries=competitor_summaries,
            )
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client (Gemini for step3b - grounding enabled)
        llm_provider = config.get("llm_provider", "gemini")
        llm_model = config.get("llm_model")
        llm = get_llm_client(llm_provider, model=llm_model)

        # LLM config (lower temperature for consistent extraction)
        llm_config = LLMRequestConfig(
            max_tokens=config.get("max_tokens", 4000),
            temperature=config.get("temperature", 0.5),
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
                    system_prompt="You are a co-occurrence keyword analysis expert.",
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
            enhancement = "\n\n【重要】以下の形式で必ず出力してください：\n"
            for issue in issues:
                if issue == "no_keyword_list":
                    enhancement += "- 各キーワードは箇条書き（・、-、*、数字）で列挙\n"
                elif issue == "no_keyword_categories":
                    enhancement += (
                        "- 「共起キーワード」「LSIキーワード」"
                        "「関連キーワード」のカテゴリを明示\n"
                    )
            return prompt + enhancement

        # Quality retry loop (strict for heart of workflow)
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

        data: dict[str, Any]
        if parse_result.success and isinstance(parse_result.data, dict):
            data = parse_result.data
            # Enforce quality standards (warnings only, don't fail)
            quality_warnings = self._enforce_quality_standards(data)
            if quality_warnings:
                logger.warning(f"Quality warnings: {quality_warnings}")
        else:
            # Extract keywords from freeform content
            data = self._extract_keywords_from_freeform(content)
            quality_warnings = []

        # Calculate content metrics
        text_metrics = self.metrics.text_metrics(content)

        return {
            "step": self.step_id,
            "keyword": keyword,
            "cooccurrence_analysis": content,
            "parsed_data": data,
            "format_detected": parse_result.format_detected,
            "competitor_count": len(competitors),
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
                "warnings": quality_warnings,
            },
        }

    def _prepare_competitor_summaries(
        self, competitors: list[dict[str, Any]]
    ) -> list[dict[str, str]]:
        """Prepare competitor summaries for prompt.

        Limits to top 5 competitors and first 500 chars of content.
        """
        summaries = []
        for comp in competitors[:5]:
            summaries.append({
                "title": comp.get("title", ""),
                "content_preview": comp.get("content", "")[:500],
            })
        return summaries

    def _enforce_quality_standards(self, data: dict[str, Any]) -> list[str]:
        """Enforce quality standards on parsed data.

        Returns warnings (does not fail).
        """
        warnings: list[str] = []

        cooccurrence = data.get("cooccurrence_keywords", [])
        lsi = data.get("lsi_keywords", [])

        if len(cooccurrence) < self.MIN_COOCCURRENCE_KEYWORDS:
            warnings.append(f"cooccurrence_count: {len(cooccurrence)}")

        if len(lsi) < self.MIN_LSI_KEYWORDS:
            warnings.append(f"lsi_count: {len(lsi)}")

        return warnings

    def _extract_keywords_from_freeform(
        self, content: str
    ) -> dict[str, Any]:
        """Extract keywords from freeform content.

        Basic extraction when JSON parsing fails.
        """
        # Simple pattern-based extraction
        lines = content.split("\n")
        keywords: list[str] = []

        for line in lines:
            line = line.strip()
            # Match list items
            if line.startswith(("・", "-", "*", "•")) or re.match(r"^\d+\.", line):
                # Extract keyword (remove list marker)
                keyword = re.sub(r"^[・\-*•]\s*|\d+\.\s*", "", line)
                keyword = keyword.strip()
                if keyword and len(keyword) < 50:
                    keywords.append(keyword)

        return {
            "cooccurrence_keywords": keywords[:self.MIN_COOCCURRENCE_KEYWORDS],
            "lsi_keywords": keywords[
                self.MIN_COOCCURRENCE_KEYWORDS : self.MIN_COOCCURRENCE_KEYWORDS
                + self.MIN_LSI_KEYWORDS
            ],
            "extracted_from_freeform": True,
        }


@activity.defn(name="step3b_cooccurrence_extraction")
async def step3b_cooccurrence_extraction(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 3B."""
    step = Step3BCooccurrenceExtraction()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
