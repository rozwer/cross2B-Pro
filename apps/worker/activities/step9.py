"""Step 9: Final Rewrite Activity.

Performs the final rewrite incorporating fact check results and FAQ.
Uses Claude for high-quality final refinement.

blog.System Ver8.3 Integration:
- 文字数監査（目標±10%）
- ファクトチェック結果反映
- FAQ配置最適化
- 4本柱最終チェック
- 品質スコア算出（8項目）
- 見出しクリーンアップ（H2-1等削除）
- CTA最終確認（工程0指定との整合性）

Integrated helpers:
- InputValidator: Validates step7b/step8 inputs
- QualityValidator: Validates rewrite quality
- OutputParser: Parses JSON response
- ContentMetrics: Calculates final metrics
- CheckpointManager: Caches input data
"""

import json
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
from apps.worker.activities.schemas.step9 import (
    FactcheckCorrection,
    FAQPlacement,
    FourPillarsFinalVerification,
    QualityScores,
    RedundancyCheck,
    RewriteChange,
    RewriteMetrics,
    SEOFinalAdjustments,
    Step9Output,
    WordCountFinal,
)
from apps.worker.helpers.checkpoint_manager import CheckpointManager
from apps.worker.helpers.content_metrics import ContentMetrics
from apps.worker.helpers.input_validator import InputValidator
from apps.worker.helpers.output_parser import OutputParser
from apps.worker.helpers.quality_validator import (
    CompletenessValidator,
    CompositeValidator,
    StructureValidator,
)
from apps.worker.helpers.schemas import QualityResult

from .base import ActivityError, BaseActivity, load_step_data

logger = logging.getLogger(__name__)

# Constants
MIN_POLISHED_LENGTH = 500
META_DESCRIPTION_PATTERN = re.compile(r"<!--\s*META_DESCRIPTION:\s*(.+?)\s*-->", re.DOTALL)
HEADING_CLEANUP_PATTERN = re.compile(r"^(#+)\s*H\d+-\d+[:\s]*", re.MULTILINE)
QUALITY_SCORE_THRESHOLD = 0.90


class Step9QualityValidator:
    """Quality validator for Step9 with blog.System Ver8.3 requirements."""

    def validate(self, content: str) -> QualityResult:
        """Validate step9 output quality."""
        issues: list[str] = []

        # Check for H2 sections
        h2_count = len(re.findall(r"^##\s", content, re.MULTILINE))
        if h2_count < 2:
            issues.append(f"h2_sections_insufficient: found {h2_count}, minimum 2 required")

        # Check for heading cleanup (H2-1, H3-2 etc. should be removed)
        management_headers = HEADING_CLEANUP_PATTERN.findall(content)
        if management_headers:
            issues.append("heading_cleanup_required: management headers (H2-1, H3-2) still present")

        # Check for truncation
        if content.rstrip().endswith("...") or content.rstrip().endswith("…"):
            issues.append("content_truncated: content appears to be incomplete")

        # Check for 参考文献 section
        if "## 参考文献" not in content and "## 参考資料" not in content:
            issues.append("references_missing: 参考文献 section should be maintained")

        return QualityResult(
            is_acceptable=len(issues) == 0,
            issues=issues,
            score=1.0 - (len(issues) * 0.1),
        )


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
            f"not_reduced: final content significantly reduced ({final_words}/{polished_words} = {final_words / polished_words:.1%})"
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
        warnings.append(f"sections_maintained: section count decreased from {polished_sections} to {final_sections}")

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
        logger.info(f"[STEP9] execute called: tenant_id={ctx.tenant_id}, run_id={ctx.run_id}")

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
        inputs_checkpoint = await self.checkpoint_manager.load(ctx.tenant_id, ctx.run_id, self.step_id, "inputs_loaded", input_digest)

        if inputs_checkpoint:
            logger.info("[STEP9] Loaded inputs from checkpoint")
            polished_content = inputs_checkpoint.get("polished", "")
            faq_content = inputs_checkpoint.get("faq", "")
            verification = inputs_checkpoint.get("verification", "")
            step8_data = inputs_checkpoint.get("step8_data", {})
        else:
            # Load step data from storage
            logger.info("[STEP9] Loading step7b and step8 data...")
            step7b_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step7b") or {}
            step8_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step8") or {}

            logger.info(f"[STEP9] step7b_data keys: {list(step7b_data.keys()) if step7b_data else 'None'}")
            logger.info(f"[STEP9] step8_data keys: {list(step8_data.keys()) if step8_data else 'None'}")

            polished_content = step7b_data.get("polished", "")
            faq_content = step8_data.get("faq", "")
            if not faq_content:
                # Try to extract from faq_items
                faq_items = step8_data.get("faq_items", [])
                if faq_items:
                    faq_content = "\n\n".join(
                        f"Q: {item.get('question', '')}\nA: {item.get('answer', '')}" for item in faq_items if isinstance(item, dict)
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
            logger.warning(f"[STEP9] Missing recommended inputs: {validation_result.missing_recommended}")

        if validation_result.quality_issues:
            logger.warning(f"[STEP9] Input quality issues: {validation_result.quality_issues}")

        # Warn about contradictions
        if step8_data.get("has_contradictions"):
            logger.warning("[STEP9] Content has contradictions - ensure corrections are applied")

        # Load step0 data for target_word_count and CTA info
        step0_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step0") or {}
        step3c_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step3c") or {}

        target_word_count = step3c_data.get("target_word_count") or step0_data.get("target_word_count", 6000)
        current_word_count = len(polished_content)
        cta_info = step0_data.get("cta", {})
        cta_info_str = json.dumps(cta_info, ensure_ascii=False) if cta_info else ""

        logger.info(f"[STEP9] Target word count: {target_word_count}, Current: {current_word_count}")

        # Render prompt with new variables
        try:
            prompt_template = prompt_pack.get_prompt("step9")
            prompt = prompt_template.render(
                keyword=keyword,
                target_word_count=target_word_count,
                current_word_count=current_word_count,
                polished_content=polished_content,
                faq=faq_content,
                verification_notes=verification,
                cta_info=cta_info_str,
            )
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client (Claude for step9)
        model_config = config.get("model_config", {})
        llm_provider = model_config.get("platform", config.get("llm_provider", "anthropic"))
        llm_model = model_config.get("model", config.get("llm_model"))
        llm = get_llm_client(llm_provider, model=llm_model)

        # Enhanced system prompt for blog.System Ver8.3
        system_prompt = """あなたは最終リライト・品質向上の専門家です。
以下のタスクを確実に実行してください：
1. 文字数監査（目標±10%）
2. ファクトチェック結果反映
3. FAQ統合
4. 見出しクリーンアップ（H2-1等の管理番号削除）
5. 4本柱最終チェック
6. 品質スコア算出（0.90以上目標）

出力は必ず指定されたJSON形式で行ってください。"""

        # Execute LLM call
        try:
            llm_config = LLMRequestConfig(
                max_tokens=config.get("max_tokens", 32000),
                temperature=config.get("temperature", 0.5),
            )
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=system_prompt,
                config=llm_config,
            )
        except Exception as e:
            raise ActivityError(
                f"LLM call failed: {e}",
                category=ErrorCategory.RETRYABLE,
            ) from e

        logger.info(f"[STEP9] Raw response length: {len(response.content)}")

        # Parse JSON response
        parsed_data = self._parse_json_response(response.content)

        # Extract final content
        final_content = parsed_data.get("final_content", "").strip()

        if not final_content:
            raise ActivityError(
                "Empty final_content in response",
                category=ErrorCategory.RETRYABLE,
            )

        # Post-process: Clean up heading management numbers
        final_content = HEADING_CLEANUP_PATTERN.sub(r"\1 ", final_content)

        logger.info(f"[STEP9] Final content length: {len(final_content)} chars")

        # Validate rewrite quality
        quality_warnings: list[str] = parsed_data.get("quality_warnings", [])
        is_quality_ok, quality_issues = _validate_rewrite_quality(polished_content, final_content, step8_data)
        if not is_quality_ok:
            quality_warnings.extend(quality_issues)
            logger.warning(f"[STEP9] Rewrite quality issues: {quality_issues}")

        # Additional quality check using Step9QualityValidator
        step9_validator = Step9QualityValidator()
        structure_result = step9_validator.validate(final_content)
        if not structure_result.is_acceptable:
            quality_warnings.extend(structure_result.issues)
            logger.warning(f"[STEP9] Structure quality issues: {structure_result.issues}")

        # Extract or generate meta description
        meta_description = parsed_data.get("meta_description", "")
        if not meta_description:
            meta_description = _extract_or_generate_meta_description(final_content, None)

        # Calculate metrics
        text_metrics = self.content_metrics.text_metrics(final_content)
        md_metrics = self.content_metrics.markdown_metrics(final_content)
        polished_text_metrics = self.content_metrics.text_metrics(polished_content)

        # Check if FAQ was integrated
        faq_indicators = ["FAQ", "よくある質問", "Q&A", "Q:"]
        faq_integrated = any(ind in final_content for ind in faq_indicators)

        # Count factcheck corrections
        factcheck_corrections_data = parsed_data.get("factcheck_corrections", [])
        factcheck_corrections_count = len(factcheck_corrections_data)

        rewrite_metrics = RewriteMetrics(
            original_word_count=polished_text_metrics.word_count,
            final_word_count=text_metrics.word_count,
            word_diff=text_metrics.word_count - polished_text_metrics.word_count,
            sections_count=md_metrics.h2_count,
            faq_integrated=faq_integrated,
            factcheck_corrections_applied=factcheck_corrections_count,
        )

        # Build factcheck corrections list
        factcheck_corrections = [
            FactcheckCorrection(
                claim_id=fc.get("claim_id", ""),
                original=fc.get("original", ""),
                corrected=fc.get("corrected", ""),
                reason=fc.get("reason", ""),
                source=fc.get("source", ""),
            )
            for fc in factcheck_corrections_data
        ]

        # Build FAQ placement
        faq_placement_data = parsed_data.get("faq_placement")
        faq_placement = None
        if faq_placement_data:
            faq_placement = FAQPlacement(
                position=faq_placement_data.get("position", "before_conclusion"),
                items_count=faq_placement_data.get("items_count", 0),
                integrated=faq_placement_data.get("integrated", faq_integrated),
            )

        # Build SEO final adjustments
        seo_data = parsed_data.get("seo_final_adjustments")
        seo_final_adjustments = None
        if seo_data:
            seo_final_adjustments = SEOFinalAdjustments(
                headings_optimized=seo_data.get("headings_optimized", []),
                internal_links_added=seo_data.get("internal_links_added", 0),
                alt_texts_generated=seo_data.get("alt_texts_generated", []),
                meta_description_optimized=seo_data.get("meta_description_optimized", bool(meta_description)),
                keyword_density=seo_data.get("keyword_density", 0.0),
                heading_cleanup_done=seo_data.get("heading_cleanup_done", True),
            )

        # Build 4 pillars verification
        four_pillars_data = parsed_data.get("four_pillars_final_verification")
        four_pillars_verification = None
        if four_pillars_data:
            four_pillars_verification = FourPillarsFinalVerification.model_validate(four_pillars_data)

        # Build word count final
        wc_data = parsed_data.get("word_count_final")
        word_count_final = None
        if wc_data:
            # Normalize status from LLM (may return English values)
            status_map = {
                "achieved": "achieved",
                "under_target_but_optimized": "補筆推奨",
                "under_target": "補筆推奨",
                "補筆推奨": "補筆推奨",
                "under_target_critical": "補筆必須",
                "補筆必須": "補筆必須",
                "over_target": "要約必須",
                "要約必須": "要約必須",
            }
            raw_status = wc_data.get("status", "achieved")
            normalized_status = status_map.get(raw_status, "achieved")
            word_count_final = WordCountFinal(
                target=wc_data.get("target", target_word_count),
                actual=wc_data.get("actual", text_metrics.word_count),
                variance=wc_data.get("variance", text_metrics.word_count - target_word_count),
                variance_percent=wc_data.get("variance_percent", 0.0),
                status=normalized_status,
                compression_applied=wc_data.get("compression_applied", False),
            )
        else:
            # Compute word count status
            variance = text_metrics.word_count - target_word_count
            variance_percent = (variance / target_word_count * 100) if target_word_count else 0
            if variance_percent < -20:
                status = "補筆必須"
            elif variance_percent < -10:
                status = "補筆推奨"
            elif variance_percent > 20:
                status = "要約必須"
            else:
                status = "achieved"

            word_count_final = WordCountFinal(
                target=target_word_count,
                actual=text_metrics.word_count,
                variance=variance,
                variance_percent=variance_percent,
                status=status,
                compression_applied=False,
            )

        # Build quality scores
        qs_data = parsed_data.get("quality_scores")
        quality_scores = None
        if qs_data:
            total_score = qs_data.get("total_score", 0.0)
            quality_scores = QualityScores(
                accuracy=qs_data.get("accuracy", 0.0),
                readability=qs_data.get("readability", 0.0),
                persuasiveness=qs_data.get("persuasiveness", 0.0),
                comprehensiveness=qs_data.get("comprehensiveness", 0.0),
                differentiation=qs_data.get("differentiation", 0.0),
                practicality=qs_data.get("practicality", 0.0),
                seo_optimization=qs_data.get("seo_optimization", 0.0),
                cta_effectiveness=qs_data.get("cta_effectiveness", 0.0),
                total_score=total_score,
                publication_ready=total_score >= QUALITY_SCORE_THRESHOLD,
            )

        # Build redundancy check
        rc_data = parsed_data.get("redundancy_check")
        redundancy_check = None
        if rc_data:
            redundancy_check = RedundancyCheck(
                redundant_expressions_removed=rc_data.get("redundant_expressions_removed", 0),
                duplicate_content_merged=rc_data.get("duplicate_content_merged", 0),
                long_sentences_split=rc_data.get("long_sentences_split", 0),
            )

        # Build changes summary
        changes_data = parsed_data.get("changes_summary", [])
        changes_summary = [
            RewriteChange(
                change_type=c.get("change_type", ""),
                section=c.get("section", ""),
                description=c.get("description", ""),
                original=c.get("original", ""),
                corrected=c.get("corrected", ""),
            )
            for c in changes_data
        ]

        # Build output
        output = Step9Output(
            step=self.step_id,
            keyword=keyword or "",
            final_content=final_content,
            meta_description=meta_description,
            changes_summary=changes_summary,
            rewrite_metrics=rewrite_metrics,
            internal_link_suggestions=parsed_data.get("internal_link_suggestions", []),
            quality_warnings=quality_warnings,
            model=response.model,
            token_usage={
                "input": response.token_usage.input,
                "output": response.token_usage.output,
            },
            # New fields
            factcheck_corrections=factcheck_corrections,
            faq_placement=faq_placement,
            seo_final_adjustments=seo_final_adjustments,
            four_pillars_final_verification=four_pillars_verification,
            word_count_final=word_count_final,
            quality_scores=quality_scores,
            redundancy_check=redundancy_check,
        )

        return output.model_dump()

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        """Parse JSON response from LLM."""
        content = content.strip()

        # Try to extract JSON from code block
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON object directly
            start_idx = content.find("{")
            end_idx = content.rfind("}") + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
            else:
                # Fallback: treat entire content as final_content (backward compatible)
                logger.warning("[STEP9] Could not parse JSON, using raw content as final_content")
                return {"final_content": content}

        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"[STEP9] JSON parse error: {e}, using raw content")
            return {"final_content": content}


@activity.defn(name="step9_final_rewrite")
async def step9_final_rewrite(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 9."""
    step = Step9FinalRewrite()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
