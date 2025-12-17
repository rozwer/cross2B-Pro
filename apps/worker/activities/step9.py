"""Step 9: Final Rewrite Activity.

Performs the final rewrite incorporating fact check results and FAQ.
Uses Claude for high-quality final refinement.

Integrated helpers:
- InputValidator: Validates step7b/step8 inputs
- QualityValidator: Validates rewrite quality
- OutputParser: Parses Markdown response + meta description extraction
- ContentMetrics: Calculates final metrics
- CheckpointManager: Caches input data
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
from apps.worker.activities.schemas.step9 import RewriteMetrics, Step9Output
from apps.worker.helpers.checkpoint_manager import CheckpointManager
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
MIN_POLISHED_LENGTH = 500
META_DESCRIPTION_PATTERN = re.compile(r"<!--\s*META_DESCRIPTION:\s*(.+?)\s*-->", re.DOTALL)


def _build_step9_quality_validator() -> CompositeValidator:
    """Build quality validator for Step9."""
    return CompositeValidator(
        validators=[
            StructureValidator(min_h2_sections=2),
            CompletenessValidator(check_truncation=True),
        ]
    )


def _validate_rewrite_quality(
    polished: str,
    final: str,
    step8_data: dict[str, Any],
) -> tuple[bool, list[str]]:
    """
    Validate rewrite quality.

    Checks:
    - Content not significantly reduced (>20%)
    - FAQ integrated when available
    - Section count maintained

    Returns:
        tuple[bool, list[str]]: (is_acceptable, list of warnings)
    """
    warnings: list[str] = []

    # Word count comparison
    polished_words = len(polished.split())
    final_words = len(final.split())

    if polished_words > 0 and final_words < polished_words * 0.8:
        warnings.append(
            f"not_reduced: final content significantly reduced "
            f"({final_words}/{polished_words} = {final_words/polished_words:.1%})"
        )

    # FAQ integration check
    faq_data = step8_data.get("faq_items", step8_data.get("faq", []))
    if faq_data:
        faq_indicators = ["FAQ", "よくある質問", "Q&A", "Q:"]
        has_faq = any(ind in final for ind in faq_indicators)
        if not has_faq:
            warnings.append("faq_integrated: FAQ should be integrated when available")

    # Section count check
    polished_sections = len(re.findall(r"^##\s", polished, re.MULTILINE))
    final_sections = len(re.findall(r"^##\s", final, re.MULTILINE))

    if polished_sections > 0 and final_sections < polished_sections:
        warnings.append(
            f"sections_maintained: section count decreased "
            f"from {polished_sections} to {final_sections}"
        )

    return len(warnings) == 0, warnings


def _extract_or_generate_meta_description(
    content: str,
    extracted_meta: str | None,
) -> str:
    """
    Extract or generate meta description.

    Priority:
    1. Explicitly marked META_DESCRIPTION
    2. Generate from first paragraph

    Returns:
        str: Meta description (max 160 chars)
    """
    # Use extracted meta if available
    if extracted_meta:
        return extracted_meta[:160]

    # Try to extract from content
    match = META_DESCRIPTION_PATTERN.search(content)
    if match:
        return match.group(1).strip()[:160]

    # Generate from first paragraph
    paragraphs = content.split("\n\n")
    for p in paragraphs:
        p = p.strip()
        # Skip headings and short paragraphs
        if not p.startswith("#") and len(p) > 50:
            sentences = p.split("。")
            description = ""
            for s in sentences:
                if len(description) + len(s) + 1 <= 160:
                    description += s + "。"
                else:
                    break
            if description:
                return description
            return p[:160]

    return ""


class Step9FinalRewrite(BaseActivity):
    """Activity for final rewrite."""

    def __init__(self) -> None:
        """Initialize with helpers."""
        super().__init__()
        self.input_validator = InputValidator()
        self.output_parser = OutputParser()
        self.content_metrics = ContentMetrics()
        self.quality_validator = _build_step9_quality_validator()
        self._checkpoint_manager: CheckpointManager | None = None

    @property
    def checkpoint_manager(self) -> CheckpointManager:
        """Lazy initialization of checkpoint manager."""
        if self._checkpoint_manager is None:
            self._checkpoint_manager = CheckpointManager(self.store)
        return self._checkpoint_manager

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
        logger.info(
            f"[STEP9] execute called: tenant_id={ctx.tenant_id}, run_id={ctx.run_id}"
        )

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

        # Compute input digest for idempotency
        input_digest = CheckpointManager.compute_digest({"keyword": keyword})

        # Try to load cached inputs
        inputs_checkpoint = await self.checkpoint_manager.load(
            ctx.tenant_id, ctx.run_id, self.step_id, "inputs_loaded", input_digest
        )

        if inputs_checkpoint:
            logger.info("[STEP9] Loaded inputs from checkpoint")
            polished_content = inputs_checkpoint.get("polished", "")
            faq_content = inputs_checkpoint.get("faq", "")
            verification = inputs_checkpoint.get("verification", "")
            step8_data = inputs_checkpoint.get("step8_data", {})
        else:
            # Load step data from storage
            logger.info("[STEP9] Loading step7b and step8 data...")
            step7b_data = (
                await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step7b")
                or {}
            )
            step8_data = (
                await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step8")
                or {}
            )

            logger.info(
                f"[STEP9] step7b_data keys: {list(step7b_data.keys()) if step7b_data else 'None'}"
            )
            logger.info(
                f"[STEP9] step8_data keys: {list(step8_data.keys()) if step8_data else 'None'}"
            )

            polished_content = step7b_data.get("polished", "")
            faq_content = step8_data.get("faq", "")
            if not faq_content:
                # Try to extract from faq_items
                faq_items = step8_data.get("faq_items", [])
                if faq_items:
                    faq_content = "\n\n".join(
                        f"Q: {item.get('question', '')}\nA: {item.get('answer', '')}"
                        for item in faq_items
                        if isinstance(item, dict)
                    )
            verification = step8_data.get("verification", "")

            # Cache inputs
            await self.checkpoint_manager.save(
                ctx.tenant_id,
                ctx.run_id,
                self.step_id,
                "inputs_loaded",
                {
                    "polished": polished_content,
                    "faq": faq_content,
                    "verification": verification,
                    "step8_data": step8_data,
                    "has_contradictions": step8_data.get("has_contradictions", False),
                },
                input_digest,
            )

        # Input validation - step7b is required, step8 is recommended
        validation_result = self.input_validator.validate(
            data={"keyword": keyword, "polished": polished_content},
            required=["keyword", "polished"],
            recommended=["faq", "verification"],
            min_lengths={"polished": MIN_POLISHED_LENGTH},
        )

        if not validation_result.is_valid:
            missing = ", ".join(validation_result.missing_required)
            raise ActivityError(
                f"Input validation failed: missing {missing}",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Log warnings for recommended fields
        if validation_result.missing_recommended:
            logger.warning(
                f"[STEP9] Missing recommended inputs: {validation_result.missing_recommended}"
            )

        if validation_result.quality_issues:
            logger.warning(
                f"[STEP9] Input quality issues: {validation_result.quality_issues}"
            )

        # Warn about contradictions
        if step8_data.get("has_contradictions"):
            logger.warning(
                "[STEP9] Content has contradictions - ensure corrections are applied"
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

        # Get LLM client (Claude for step9)
        model_config = config.get("model_config", {})
        llm_provider = model_config.get(
            "platform", config.get("llm_provider", "anthropic")
        )
        llm_model = model_config.get("model", config.get("llm_model"))
        llm = get_llm_client(llm_provider, model=llm_model)

        # Execute LLM call
        try:
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

        logger.info(f"[STEP9] Raw response length: {len(response.content)}")

        # Parse response
        final_content = response.content.strip()

        # Remove code block markers if present
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

        # Validate rewrite quality
        quality_warnings: list[str] = []
        is_quality_ok, quality_issues = _validate_rewrite_quality(
            polished_content, final_content, step8_data
        )
        if not is_quality_ok:
            quality_warnings.extend(quality_issues)
            logger.warning(f"[STEP9] Rewrite quality issues: {quality_issues}")

        # Additional quality check using CompositeValidator
        structure_result = self.quality_validator.validate(final_content)
        if not structure_result.is_acceptable:
            quality_warnings.extend(structure_result.issues)
            logger.warning(
                f"[STEP9] Structure quality issues: {structure_result.issues}"
            )

        # Extract or generate meta description
        meta_description = _extract_or_generate_meta_description(final_content, None)

        # Calculate metrics
        text_metrics = self.content_metrics.text_metrics(final_content)
        md_metrics = self.content_metrics.markdown_metrics(final_content)
        polished_text_metrics = self.content_metrics.text_metrics(polished_content)

        # Check if FAQ was integrated
        faq_indicators = ["FAQ", "よくある質問", "Q&A", "Q:"]
        faq_integrated = any(ind in final_content for ind in faq_indicators)

        # Count factcheck corrections (estimate)
        factcheck_corrections = 0
        if step8_data.get("verification_results"):
            verification_results = step8_data.get("verification_results", [])
            factcheck_corrections = sum(
                1
                for r in verification_results
                if isinstance(r, dict) and r.get("status") == "contradicted"
            )

        rewrite_metrics = RewriteMetrics(
            original_word_count=polished_text_metrics.word_count,
            final_word_count=text_metrics.word_count,
            word_diff=text_metrics.word_count - polished_text_metrics.word_count,
            sections_count=md_metrics.h2_count,
            faq_integrated=faq_integrated,
            factcheck_corrections_applied=factcheck_corrections,
        )

        # Build output
        output = Step9Output(
            step=self.step_id,
            keyword=keyword or "",
            final_content=final_content,
            meta_description=meta_description,
            changes_summary=[],
            rewrite_metrics=rewrite_metrics,
            internal_link_suggestions=[],
            quality_warnings=quality_warnings,
            model=response.model,
            token_usage={
                "input_tokens": response.token_usage.input,
                "output_tokens": response.token_usage.output,
            },
        )

        return output.model_dump()


@activity.defn(name="step9_final_rewrite")
async def step9_final_rewrite(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 9."""
    step = Step9FinalRewrite()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
