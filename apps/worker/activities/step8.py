"""Step 8: Fact Check Activity.

Verifies facts and claims in the polished article.
Adds FAQ section if contradictions or gaps are found.
Uses Gemini with web grounding for verification.

blog.System Ver8.3 enhancements:
- Verification categories (numeric, source, timeline, logical)
- FAQ LLMO optimization (voice search, structured data)
- Four pillars FAQ integration (neuroscience, behavioral economics, LLMO, KGI)
- Enhanced rejection analysis with severity levels
- Auto-correction prohibition (human review required)

Integrated helpers:
- InputValidator: Validates step7b polished content
- OutputParser: Parses JSON responses (claims, verification, FAQ)
- QualityValidator: Validates claims and verification quality
- CheckpointManager: Checkpoints for 3-stage LLM calls
"""

import logging
from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.llm.base import get_llm_client
from apps.api.llm.schemas import LLMRequestConfig
from apps.api.prompts.loader import PromptPackLoader
from apps.worker.activities.schemas.step8 import (
    Claim,
    FAQFourPillars,
    FAQItem,
    FAQLLMOOptimization,
    FAQSummary,
    RejectionAnalysis,
    Step8Output,
    VerificationCategories,
    VerificationCategoryResult,
    VerificationResult,
    VerificationSummary,
)
from apps.worker.helpers.checkpoint_manager import CheckpointManager
from apps.worker.helpers.input_validator import InputValidator
from apps.worker.helpers.output_parser import OutputParser

from .base import ActivityError, BaseActivity, load_step_data

logger = logging.getLogger(__name__)

# Constants
MIN_POLISHED_LENGTH = 500
MIN_CLAIMS_COUNT = 3
# blog.System Ver8.3: FAQ target is 10-15 items
MIN_FAQ_COUNT = 10
MAX_FAQ_COUNT = 15
# blog.System Ver8.3: Question words for voice search optimization
QUESTION_WORDS = ["どのくらい", "どのように", "なぜ", "いつ", "何", "どこ", "だれ", "どんな"]
# blog.System Ver8.3: Target answer length (characters)
FAQ_ANSWER_MIN_LENGTH = 120
FAQ_ANSWER_MAX_LENGTH = 180


def _parse_claims_from_response(
    parser: OutputParser,
    content: str,
) -> list[Claim]:
    """Parse claims from LLM response."""
    parse_result = parser.parse_json(content)

    if not parse_result.success or not parse_result.data:
        logger.warning("[STEP8] Failed to parse claims JSON, returning empty list")
        return []

    claims_data = parse_result.data
    if isinstance(claims_data, dict):
        claims_list = claims_data.get("claims", [])
    elif isinstance(claims_data, list):
        claims_list = claims_data
    else:
        return []

    claims: list[Claim] = []
    for i, item in enumerate(claims_list):
        if isinstance(item, dict):
            claims.append(
                Claim(
                    claim_id=item.get("claim_id", f"C{i + 1}"),
                    text=item.get("text", ""),
                    source_section=item.get("source_section", ""),
                    claim_type=item.get("claim_type", "fact"),
                    # blog.System extensions
                    verification_category=item.get("verification_category"),
                    data_anchor_id=item.get("data_anchor_id"),
                )
            )
    return claims


def _parse_verification_from_response(
    parser: OutputParser,
    content: str,
) -> list[VerificationResult]:
    """Parse verification results from LLM response."""
    parse_result = parser.parse_json(content)

    if not parse_result.success or not parse_result.data:
        logger.warning("[STEP8] Failed to parse verification JSON, returning empty list")
        return []

    data = parse_result.data
    if isinstance(data, dict):
        results_list = data.get("verification_results", data.get("results", []))
    elif isinstance(data, list):
        results_list = data
    else:
        return []

    results: list[VerificationResult] = []
    for item in results_list or []:
        if isinstance(item, dict):
            results.append(
                VerificationResult(
                    claim_id=item.get("claim_id", ""),
                    status=item.get("status", "unverified"),
                    confidence=float(item.get("confidence", 0.5)),
                    evidence=item.get("evidence", ""),
                    source=item.get("source", ""),
                    recommendation=item.get("recommendation", ""),
                    # blog.System extensions
                    verification_method=item.get("verification_method", ""),
                    url_checked=item.get("url_checked", False),
                    url_valid=item.get("url_valid"),
                )
            )
    return results


def _parse_faq_from_response(
    parser: OutputParser,
    content: str,
) -> list[FAQItem]:
    """Parse FAQ items from LLM response."""
    parse_result = parser.parse_json(content)

    if not parse_result.success or not parse_result.data:
        logger.warning("[STEP8] Failed to parse FAQ JSON, returning empty list")
        return []

    data = parse_result.data
    if isinstance(data, dict):
        faq_list = data.get("faq_items", data.get("faq", []))
    elif isinstance(data, list):
        faq_list = data
    else:
        return []

    items: list[FAQItem] = []
    for item in faq_list or []:
        if isinstance(item, dict):
            question = item.get("question", "")
            answer = item.get("answer", "")

            # blog.System: Detect question word used
            question_word_used = None
            for qw in QUESTION_WORDS:
                if qw in question:
                    question_word_used = qw
                    break

            # blog.System: Parse four pillars if provided
            four_pillars = None
            if "four_pillars" in item and isinstance(item["four_pillars"], dict):
                fp = item["four_pillars"]
                four_pillars = FAQFourPillars(
                    neuroscience_applied=fp.get("neuroscience_applied", False),
                    neuroscience_details=fp.get("neuroscience_details", ""),
                    behavioral_economics_applied=fp.get("behavioral_economics_applied", False),
                    behavioral_economics_details=fp.get("behavioral_economics_details", ""),
                    llmo_optimized=fp.get("llmo_optimized", False),
                    llmo_details=fp.get("llmo_details", ""),
                    kgi_integrated=fp.get("kgi_integrated", False),
                    kgi_details=fp.get("kgi_details", ""),
                )

            items.append(
                FAQItem(
                    question=question,
                    answer=answer,
                    related_claims=item.get("related_claims", []),
                    # blog.System extensions
                    voice_search_optimized=item.get("voice_search_optimized", question_word_used is not None),
                    question_word_used=question_word_used,
                    answer_length=len(answer),
                    has_data_anchor=item.get("has_data_anchor", "[PS-" in answer or "[ER-" in answer),
                    has_cta=item.get("has_cta", False),
                    has_internal_link=item.get("has_internal_link", False),
                    four_pillars=four_pillars,
                )
            )
    return items


def _determine_rejection_recommendation(
    verification_results: list[VerificationResult],
) -> tuple[bool, list[str]]:
    """
    Determine if rejection should be recommended.

    Returns:
        tuple[bool, list[str]]: (recommend_rejection, critical_issues)
    """
    critical_issues: list[str] = []

    contradicted_count = sum(1 for r in verification_results if r.status == "contradicted")

    if contradicted_count >= 2:
        critical_issues.append(f"{contradicted_count} contradictions found")

    # High-confidence contradictions
    high_confidence_contradictions = [r for r in verification_results if r.status == "contradicted" and r.confidence > 0.8]
    if high_confidence_contradictions:
        critical_issues.append("High-confidence contradictions detected")

    recommend_rejection = len(critical_issues) > 0

    return recommend_rejection, critical_issues


def _compute_verification_summary(
    results: list[VerificationResult],
    claims: list[Claim],
) -> VerificationSummary:
    """Compute summary statistics for verification results.

    blog.System Ver8.3: Enhanced with total claims, verification rate, data anchors, URLs.
    """
    verified_count = sum(1 for r in results if r.status == "verified")
    total_claims = len(claims)
    urls_checked = sum(1 for r in results if r.url_checked)
    urls_valid = sum(1 for r in results if r.url_valid is True)
    data_anchors = sum(1 for c in claims if c.data_anchor_id)

    return VerificationSummary(
        verified_count=verified_count,
        unverified_count=sum(1 for r in results if r.status == "unverified"),
        contradicted_count=sum(1 for r in results if r.status == "contradicted"),
        partially_verified_count=sum(1 for r in results if r.status == "partially_verified"),
        # blog.System extensions
        total_claims=total_claims,
        verification_rate=verified_count / total_claims if total_claims > 0 else 0.0,
        data_anchors_verified=data_anchors,
        urls_checked=urls_checked,
        urls_valid=urls_valid,
    )


# ============================================================================
# blog.System Ver8.3 Extension Functions
# ============================================================================


def _compute_verification_categories(
    claims: list[Claim],
    results: list[VerificationResult],
) -> VerificationCategories:
    """Compute verification results by category.

    blog.System Ver8.3: Categorize verification into numeric, source, timeline, logical.
    """
    # Map claim_id to verification result
    result_map = {r.claim_id: r for r in results}

    categories = {
        "numeric_data": VerificationCategoryResult(),
        "source_accuracy": VerificationCategoryResult(),
        "timeline_consistency": VerificationCategoryResult(),
        "logical_consistency": VerificationCategoryResult(),
    }

    for claim in claims:
        category = claim.verification_category
        if category and category in categories:
            cat_result = categories[category]
            cat_result.claims_checked += 1

            result = result_map.get(claim.claim_id)
            if result:
                if result.status == "verified":
                    cat_result.verified += 1
                elif result.status in ("contradicted", "unverified"):
                    cat_result.issues.append(f"[{claim.claim_id}] {claim.text[:50]}...: {result.status}")

    return VerificationCategories(
        numeric_data=categories["numeric_data"],
        source_accuracy=categories["source_accuracy"],
        timeline_consistency=categories["timeline_consistency"],
        logical_consistency=categories["logical_consistency"],
    )


def _compute_faq_llmo_optimization(
    faq_items: list[FAQItem],
) -> FAQLLMOOptimization:
    """Compute FAQ LLMO optimization summary.

    blog.System Ver8.3: Voice search and structured data optimization analysis.
    """
    if not faq_items:
        return FAQLLMOOptimization()

    question_format_count = sum(1 for faq in faq_items if faq.question_word_used is not None)
    voice_search_count = sum(1 for faq in faq_items if faq.voice_search_optimized)
    total_answer_length = sum(faq.answer_length for faq in faq_items)

    # Natural language score: Based on question word usage and answer length
    natural_lang_factors = []
    for faq in faq_items:
        score = 0.0
        if faq.question_word_used:
            score += 0.5
        if FAQ_ANSWER_MIN_LENGTH <= faq.answer_length <= FAQ_ANSWER_MAX_LENGTH:
            score += 0.5
        natural_lang_factors.append(score)

    natural_language_score = sum(natural_lang_factors) / len(natural_lang_factors) if natural_lang_factors else 0.0

    return FAQLLMOOptimization(
        question_format_count=question_format_count,
        voice_search_friendly=voice_search_count >= len(faq_items) * 0.8,
        structured_data_ready=question_format_count >= len(faq_items) * 0.7,
        natural_language_score=natural_language_score,
        average_answer_length=total_answer_length // len(faq_items) if faq_items else 0,
    )


def _compute_faq_summary(
    faq_items: list[FAQItem],
) -> FAQSummary:
    """Compute FAQ generation summary.

    blog.System Ver8.3: FAQ statistics with four pillars compliance.
    """
    if not faq_items:
        return FAQSummary()

    voice_search_count = sum(1 for faq in faq_items if faq.voice_search_optimized)
    cta_count = sum(1 for faq in faq_items if faq.has_cta)
    internal_link_count = sum(1 for faq in faq_items if faq.has_internal_link)

    # Four pillars compliance: All four must be applied
    four_pillars_compliant = 0
    for faq in faq_items:
        if faq.four_pillars:
            fp = faq.four_pillars
            if fp.neuroscience_applied and fp.behavioral_economics_applied and fp.llmo_optimized and fp.kgi_integrated:
                four_pillars_compliant += 1

    return FAQSummary(
        faq_count=len(faq_items),
        voice_search_optimized_count=voice_search_count,
        four_pillars_compliance_rate=(four_pillars_compliant / len(faq_items) if faq_items else 0.0),
        cta_integrated_count=cta_count,
        internal_link_count=internal_link_count,
    )


def _compute_rejection_analysis(
    verification_results: list[VerificationResult],
    claims: list[Claim],
) -> RejectionAnalysis:
    """Compute enhanced rejection analysis.

    blog.System Ver8.3: Severity levels and human review requirement.
    IMPORTANT: Auto-correction is PROHIBITED - human review required.
    """
    reasons: list[str] = []
    suggested_actions: list[str] = []

    contradicted = [r for r in verification_results if r.status == "contradicted"]
    unverified = [r for r in verification_results if r.status == "unverified"]

    # Determine severity
    severity: str = "none"
    should_reject = False

    # Critical: High-confidence contradictions or multiple contradictions
    high_confidence_contradictions = [r for r in contradicted if r.confidence > 0.8]
    if high_confidence_contradictions:
        severity = "critical"
        should_reject = True
        reasons.append(f"{len(high_confidence_contradictions)} high-confidence contradictions detected")
        suggested_actions.append("人間レビューで事実確認を行ってください")
        suggested_actions.append("データソースの再検証が必要です")

    elif len(contradicted) >= 2:
        severity = "critical"
        should_reject = True
        reasons.append(f"{len(contradicted)} contradictions found")
        suggested_actions.append("複数の矛盾が検出されました。原稿の精査が必要です")

    # Major: Some contradictions or many unverified
    elif len(contradicted) == 1:
        severity = "major"
        should_reject = True
        reasons.append("1 contradiction found - requires human verification")
        suggested_actions.append("該当箇所の事実確認をお願いします")

    elif len(unverified) >= len(verification_results) * 0.3:
        severity = "major"
        reasons.append(f"{len(unverified)} claims could not be verified ({len(unverified) / len(verification_results) * 100:.0f}%)")
        suggested_actions.append("未検証の主張についてソース確認をお願いします")

    # Minor: Few unverified claims
    elif unverified:
        severity = "minor"
        reasons.append(f"{len(unverified)} claims remain unverified")
        suggested_actions.append("可能であれば追加ソースの提供をお願いします")

    return RejectionAnalysis(
        should_reject=should_reject,
        severity=severity,  # type: ignore[arg-type]
        reasons=reasons,
        human_review_required=bool(contradicted),  # Always require human review for contradictions
        auto_correction_prohibited=True,  # blog.System rule: NEVER auto-correct
        suggested_actions=suggested_actions,
    )


def _generate_faq_markdown(
    faq_items: list[FAQItem],
    keyword: str,
) -> str:
    """Generate FAQ section in Markdown format.

    blog.System Ver8.3: Structured FAQ for article integration.
    """
    if not faq_items:
        return ""

    lines = [
        "## よくある質問（FAQ）",
        "",
    ]

    for i, faq in enumerate(faq_items, 1):
        lines.append(f"### Q{i}. {faq.question}")
        lines.append("")
        lines.append(f"**A.** {faq.answer}")
        lines.append("")

    return "\n".join(lines)


class Step8FactCheck(BaseActivity):
    """Activity for fact checking and FAQ generation."""

    def __init__(self) -> None:
        """Initialize with helpers."""
        super().__init__()
        self.input_validator = InputValidator()
        self.output_parser = OutputParser()
        self._checkpoint_manager: CheckpointManager | None = None

    @property
    def checkpoint_manager(self) -> CheckpointManager:
        """Lazy initialization of checkpoint manager."""
        if self._checkpoint_manager is None:
            self._checkpoint_manager = CheckpointManager(self.store)
        return self._checkpoint_manager

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

        # Load step data from storage
        step7b_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step7b") or {}
        polished_content = step7b_data.get("polished", "")

        # Input validation
        validation_result = self.input_validator.validate(
            data={"keyword": keyword, "polished": polished_content},
            required=["keyword", "polished"],
            min_lengths={"polished": MIN_POLISHED_LENGTH},
        )

        if not validation_result.is_valid:
            missing = ", ".join(validation_result.missing_required)
            raise ActivityError(
                f"Input validation failed: missing {missing}",
                category=ErrorCategory.NON_RETRYABLE,
            )

        if validation_result.quality_issues:
            logger.warning(f"[STEP8] Input quality issues: {validation_result.quality_issues}")

        # Get LLM client
        model_config = config.get("model_config", {})
        llm_provider = model_config.get("platform", config.get("llm_provider", "gemini"))
        llm_model = model_config.get("model", config.get("llm_model"))
        llm = get_llm_client(llm_provider, model=llm_model)

        # Compute input digest for idempotency
        input_digest = CheckpointManager.compute_digest({"keyword": keyword, "polished": polished_content[:1000]})

        # Step 8.1: Extract claims (with checkpoint)
        claims_checkpoint = await self.checkpoint_manager.load(ctx.tenant_id, ctx.run_id, self.step_id, "claims_extracted", input_digest)

        if claims_checkpoint:
            logger.info("[STEP8] Loaded claims from checkpoint")
            extracted_claims = _parse_claims_from_response(self.output_parser, claims_checkpoint.get("raw_response", ""))
            if not extracted_claims and claims_checkpoint.get("claims"):
                extracted_claims = [Claim(**c) for c in claims_checkpoint.get("claims", [])]
        else:
            try:
                claims_prompt = prompt_pack.get_prompt("step8_claims")
                claims_request = claims_prompt.render(content=polished_content)
                claims_config = LLMRequestConfig(max_tokens=2000, temperature=0.3)
                claims_response = await llm.generate(
                    messages=[{"role": "user", "content": claims_request}],
                    system_prompt="Extract claims from the provided content.",
                    config=claims_config,
                )
                extracted_claims = _parse_claims_from_response(self.output_parser, claims_response.content)

                # Save checkpoint
                await self.checkpoint_manager.save(
                    ctx.tenant_id,
                    ctx.run_id,
                    self.step_id,
                    "claims_extracted",
                    {
                        "claims": [c.model_dump() for c in extracted_claims],
                        "raw_response": claims_response.content,
                    },
                    input_digest,
                )
            except Exception as e:
                raise ActivityError(
                    f"Failed to extract claims: {e}",
                    category=ErrorCategory.RETRYABLE,
                ) from e

        # Validate claims count
        if len(extracted_claims) < MIN_CLAIMS_COUNT:
            logger.warning(f"[STEP8] Only {len(extracted_claims)} claims extracted (min: {MIN_CLAIMS_COUNT})")

        # Step 8.2: Verify claims (with checkpoint)
        verify_checkpoint = await self.checkpoint_manager.load(ctx.tenant_id, ctx.run_id, self.step_id, "verification_done", input_digest)

        if verify_checkpoint:
            logger.info("[STEP8] Loaded verification results from checkpoint")
            verification_results = _parse_verification_from_response(self.output_parser, verify_checkpoint.get("raw_response", ""))
            if not verification_results and verify_checkpoint.get("results"):
                verification_results = [VerificationResult(**r) for r in verify_checkpoint.get("results", [])]
        else:
            try:
                verify_prompt = prompt_pack.get_prompt("step8_verify")
                verify_request = verify_prompt.render(
                    claims="\n".join(f"[{c.claim_id}] {c.text}" for c in extracted_claims),
                    keyword=keyword,
                )
                verify_config = LLMRequestConfig(max_tokens=3000, temperature=0.3)
                verify_response = await llm.generate(
                    messages=[{"role": "user", "content": verify_request}],
                    system_prompt="Verify the claims using available knowledge.",
                    config=verify_config,
                )
                verification_results = _parse_verification_from_response(self.output_parser, verify_response.content)

                # Save checkpoint
                await self.checkpoint_manager.save(
                    ctx.tenant_id,
                    ctx.run_id,
                    self.step_id,
                    "verification_done",
                    {
                        "results": [r.model_dump() for r in verification_results],
                        "raw_response": verify_response.content,
                    },
                    input_digest,
                )
            except Exception as e:
                raise ActivityError(
                    f"Failed to verify claims: {e}",
                    category=ErrorCategory.RETRYABLE,
                ) from e

        # Step 8.3: Generate FAQ (no checkpoint - final step)
        try:
            faq_prompt = prompt_pack.get_prompt("step8_faq")
            faq_request = faq_prompt.render(
                keyword=keyword,
                verification="\n".join(f"[{r.claim_id}] {r.status}: {r.evidence}" for r in verification_results),
            )
            faq_config = LLMRequestConfig(max_tokens=2000, temperature=0.6)
            faq_response = await llm.generate(
                messages=[{"role": "user", "content": faq_request}],
                system_prompt="Generate FAQ based on the verification results.",
                config=faq_config,
            )
            faq_items = _parse_faq_from_response(self.output_parser, faq_response.content)
        except Exception as e:
            raise ActivityError(
                f"Failed to generate FAQ: {e}",
                category=ErrorCategory.RETRYABLE,
            ) from e

        # Validate FAQ count
        if len(faq_items) < MIN_FAQ_COUNT:
            logger.warning(f"[STEP8] Only {len(faq_items)} FAQ items generated (min: {MIN_FAQ_COUNT})")
        elif len(faq_items) > MAX_FAQ_COUNT:
            logger.warning(f"[STEP8] {len(faq_items)} FAQ items generated (max: {MAX_FAQ_COUNT})")
            faq_items = faq_items[:MAX_FAQ_COUNT]

        # Determine rejection recommendation (legacy)
        recommend_rejection, critical_issues = _determine_rejection_recommendation(verification_results)
        has_contradictions = any(r.status == "contradicted" for r in verification_results)

        # Compute summary (enhanced for blog.System Ver8.3)
        summary = _compute_verification_summary(verification_results, extracted_claims)

        # blog.System Ver8.3: Compute extended metrics
        verification_categories = _compute_verification_categories(extracted_claims, verification_results)
        faq_llmo_optimization = _compute_faq_llmo_optimization(faq_items)
        faq_summary = _compute_faq_summary(faq_items)
        rejection_analysis = _compute_rejection_analysis(verification_results, extracted_claims)
        faq_section_markdown = _generate_faq_markdown(faq_items, keyword or "")

        # Log blog.System metrics
        logger.info(
            f"[STEP8] blog.System metrics: "
            f"verification_rate={summary.verification_rate:.1%}, "
            f"faq_count={faq_summary.faq_count}, "
            f"four_pillars_compliance={faq_summary.four_pillars_compliance_rate:.1%}, "
            f"rejection_severity={rejection_analysis.severity}"
        )

        # Build output
        output = Step8Output(
            step=self.step_id,
            keyword=keyword or "",
            claims=extracted_claims,
            verification_results=verification_results,
            faq_items=faq_items,
            summary=summary,
            has_contradictions=has_contradictions,
            critical_issues=critical_issues,
            recommend_rejection=recommend_rejection,
            model=llm_model or "default",
            token_usage={
                "input": 0,  # Token tracking simplified
                "output": 0,
            },
            # blog.System Ver8.3 extensions
            verification_categories=verification_categories,
            faq_llmo_optimization=faq_llmo_optimization,
            faq_summary=faq_summary,
            rejection_analysis=rejection_analysis,
            faq_section_markdown=faq_section_markdown,
            references_verified=summary.urls_checked > 0 and summary.urls_valid == summary.urls_checked,
        )

        return output.model_dump()


@activity.defn(name="step8_fact_check")
async def step8_fact_check(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 8."""
    step = Step8FactCheck()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
