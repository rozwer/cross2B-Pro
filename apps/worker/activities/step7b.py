"""Step 7B: Brush Up Activity.

Polishes and improves the draft with natural language and flow.
Uses Gemini for natural language enhancement.

Integrated helpers:
- InputValidator: Validates step7a draft
- QualityValidator: Validates polishing quality
- ContentMetrics: Calculates change metrics
- OutputParser: Parses Markdown response
"""

import logging
import re
from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.llm.base import get_llm_client
from apps.api.llm.schemas import LLMRequestConfig
from apps.api.prompts.loader import PromptPackLoader
from apps.worker.activities.schemas.step7b import PolishMetrics, Step7bOutput
from apps.worker.helpers.content_metrics import ContentMetrics
from apps.worker.helpers.input_validator import InputValidator
from apps.worker.helpers.output_parser import OutputParser
from apps.worker.helpers.quality_validator import (
    CompletenessValidator,
    CompositeValidator,
    StructureValidator,
)

from .base import ActivityError, BaseActivity, load_step_data

logger = logging.getLogger(__name__)

# Constants
MIN_DRAFT_LENGTH = 500


def _build_step7b_quality_validator() -> CompositeValidator:
    """Build quality validator for Step7b."""
    return CompositeValidator(
        validators=[
            StructureValidator(min_h2_sections=2),
            CompletenessValidator(check_truncation=True),
        ]
    )


def _validate_polishing_quality(
    original: str,
    polished: str,
) -> tuple[bool, list[str]]:
    """
    Validate polishing quality.

    Checks:
    - Content not reduced by more than 30%
    - Content not inflated by more than 50%
    - Most sections preserved
    - Conclusion preserved
    - Not truncated

    Returns:
        tuple[bool, list[str]]: (is_acceptable, list of issues)
    """
    issues: list[str] = []

    # Word count comparison
    orig_words = len(original.split())
    polished_words = len(polished.split())

    if orig_words > 0:
        # Check not reduced by more than 30%
        if polished_words < orig_words * 0.7:
            issues.append(
                f"not_reduced: polished content significantly reduced "
                f"({polished_words}/{orig_words} = {polished_words/orig_words:.1%})"
            )

        # Check not inflated by more than 50%
        if polished_words > orig_words * 1.5:
            issues.append(
                f"not_inflated: polished content significantly inflated "
                f"({polished_words}/{orig_words} = {polished_words/orig_words:.1%})"
            )

    # Section preservation check
    orig_sections = len(re.findall(r"^##\s", original, re.MULTILINE))
    polished_sections = len(re.findall(r"^##\s", polished, re.MULTILINE))

    if orig_sections > 0 and polished_sections < orig_sections * 0.8:
        issues.append(
            f"sections_preserved: sections reduced from {orig_sections} to {polished_sections}"
        )

    # Conclusion preservation check
    conclusion_patterns = ["まとめ", "結論", "おわり"]
    orig_has_conclusion = any(p in original.lower() for p in conclusion_patterns)
    polished_has_conclusion = any(p in polished.lower() for p in conclusion_patterns)

    if orig_has_conclusion and not polished_has_conclusion:
        issues.append("conclusion_preserved: conclusion section missing in polished content")

    # Truncation check
    truncation_indicators = ["...", "…", "、"]
    stripped = polished.rstrip()
    if any(stripped.endswith(ind) for ind in truncation_indicators):
        issues.append("not_truncated: polished content appears to be truncated")

    return len(issues) == 0, issues


class Step7BBrushUp(BaseActivity):
    """Activity for draft polishing and brush up."""

    def __init__(self) -> None:
        """Initialize with helpers."""
        super().__init__()
        self.input_validator = InputValidator()
        self.output_parser = OutputParser()
        self.content_metrics = ContentMetrics()
        self.quality_validator = _build_step7b_quality_validator()

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

        # Load step data from storage
        step7a_data = (
            await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step7a") or {}
        )
        draft = step7a_data.get("draft", "")

        # Input validation using InputValidator
        validation_result = self.input_validator.validate(
            data={"keyword": keyword, "draft": draft},
            required=["keyword", "draft"],
            min_lengths={"draft": MIN_DRAFT_LENGTH},
        )

        if not validation_result.is_valid:
            missing = ", ".join(validation_result.missing_required)
            raise ActivityError(
                f"Input validation failed: missing {missing}",
                category=ErrorCategory.NON_RETRYABLE,
            )

        if validation_result.quality_issues:
            logger.warning(
                f"[STEP7B] Input quality issues: {validation_result.quality_issues}"
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

        # Get LLM client
        model_config = config.get("model_config", {})
        llm_provider = model_config.get(
            "platform", config.get("llm_provider", "gemini")
        )
        llm_model = model_config.get("model", config.get("llm_model"))
        llm = get_llm_client(llm_provider, model=llm_model)

        logger.info(
            f"[STEP7B] Starting LLM call - provider: {llm_provider}, model: {llm_model}"
        )
        logger.info(f"[STEP7B] Draft length: {len(draft)} chars")

        # Execute LLM call
        try:
            llm_config = LLMRequestConfig(
                max_tokens=config.get("max_tokens", 24000),
                temperature=config.get("temperature", 0.8),
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

        logger.info("[STEP7B] LLM call completed successfully")
        logger.info(f"[STEP7B] Raw response length: {len(response.content)}")

        # Parse response using OutputParser
        polished_content = response.content.strip()

        # Remove code block markers if present
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

        # Validate polishing quality
        quality_warnings: list[str] = []
        is_quality_ok, quality_issues = _validate_polishing_quality(draft, polished_content)
        if not is_quality_ok:
            quality_warnings.extend(quality_issues)
            logger.warning(f"[STEP7B] Polishing quality issues: {quality_issues}")

        # Additional quality check using CompositeValidator
        structure_result = self.quality_validator.validate(polished_content)
        if not structure_result.is_acceptable:
            quality_warnings.extend(structure_result.issues)
            logger.warning(f"[STEP7B] Structure quality issues: {structure_result.issues}")

        # Calculate metrics using ContentMetrics
        comparison = self.content_metrics.compare_content(draft, polished_content)
        text_metrics = self.content_metrics.text_metrics(polished_content)
        md_metrics = self.content_metrics.markdown_metrics(polished_content)

        # Calculate sections modified (estimate based on h2 diff)
        orig_h2 = self.content_metrics.markdown_metrics(draft).h2_count
        polished_h2 = md_metrics.h2_count
        sections_modified = abs(polished_h2 - orig_h2)

        polish_metrics = PolishMetrics(
            original_word_count=self.content_metrics.text_metrics(draft).word_count,
            polished_word_count=text_metrics.word_count,
            word_diff=int(comparison["word_diff"]),
            word_diff_percent=(
                comparison["word_diff"]
                / self.content_metrics.text_metrics(draft).word_count
                * 100
                if self.content_metrics.text_metrics(draft).word_count > 0
                else 0.0
            ),
            sections_preserved=min(orig_h2, polished_h2),
            sections_modified=sections_modified,
        )

        # Build output
        output = Step7bOutput(
            step=self.step_id,
            keyword=keyword or "",
            polished=polished_content,
            changes_summary="",
            change_count=0,
            polish_metrics=polish_metrics,
            quality_warnings=quality_warnings,
            model=response.model,
            token_usage={
                "input_tokens": response.token_usage.input,
                "output_tokens": response.token_usage.output,
            },
        )

        return output.model_dump()


@activity.defn(name="step7b_brush_up")
async def step7b_brush_up(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 7B."""
    step = Step7BBrushUp()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
