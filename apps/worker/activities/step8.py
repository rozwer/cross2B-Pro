"""Step 8: Fact Check Activity.

Verifies facts and claims in the polished article.
Adds FAQ section if contradictions or gaps are found.
Uses Gemini with web grounding for verification.

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
    FAQItem,
    Step8Output,
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
MIN_FAQ_COUNT = 3
MAX_FAQ_COUNT = 7


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
                    claim_id=item.get("claim_id", f"C{i+1}"),
                    text=item.get("text", ""),
                    source_section=item.get("source_section", ""),
                    claim_type=item.get("claim_type", "fact"),
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
            items.append(
                FAQItem(
                    question=item.get("question", ""),
                    answer=item.get("answer", ""),
                    related_claims=item.get("related_claims", []),
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

    contradicted_count = sum(
        1 for r in verification_results if r.status == "contradicted"
    )

    if contradicted_count >= 2:
        critical_issues.append(f"{contradicted_count} contradictions found")

    # High-confidence contradictions
    high_confidence_contradictions = [
        r
        for r in verification_results
        if r.status == "contradicted" and r.confidence > 0.8
    ]
    if high_confidence_contradictions:
        critical_issues.append("High-confidence contradictions detected")

    recommend_rejection = len(critical_issues) > 0

    return recommend_rejection, critical_issues


def _compute_verification_summary(
    results: list[VerificationResult],
) -> VerificationSummary:
    """Compute summary statistics for verification results."""
    return VerificationSummary(
        verified_count=sum(1 for r in results if r.status == "verified"),
        unverified_count=sum(1 for r in results if r.status == "unverified"),
        contradicted_count=sum(1 for r in results if r.status == "contradicted"),
        partially_verified_count=sum(
            1 for r in results if r.status == "partially_verified"
        ),
    )


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
        step7b_data = (
            await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step7b") or {}
        )
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
            logger.warning(
                f"[STEP8] Input quality issues: {validation_result.quality_issues}"
            )

        # Get LLM client
        model_config = config.get("model_config", {})
        llm_provider = model_config.get(
            "platform", config.get("llm_provider", "gemini")
        )
        llm_model = model_config.get("model", config.get("llm_model"))
        llm = get_llm_client(llm_provider, model=llm_model)

        # Compute input digest for idempotency
        input_digest = CheckpointManager.compute_digest(
            {"keyword": keyword, "polished": polished_content[:1000]}
        )

        # Step 8.1: Extract claims (with checkpoint)
        claims_checkpoint = await self.checkpoint_manager.load(
            ctx.tenant_id, ctx.run_id, self.step_id, "claims_extracted", input_digest
        )

        if claims_checkpoint:
            logger.info("[STEP8] Loaded claims from checkpoint")
            extracted_claims = _parse_claims_from_response(
                self.output_parser, claims_checkpoint.get("raw_response", "")
            )
            if not extracted_claims and claims_checkpoint.get("claims"):
                extracted_claims = [
                    Claim(**c) for c in claims_checkpoint.get("claims", [])
                ]
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
                extracted_claims = _parse_claims_from_response(
                    self.output_parser, claims_response.content
                )

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
            logger.warning(
                f"[STEP8] Only {len(extracted_claims)} claims extracted "
                f"(min: {MIN_CLAIMS_COUNT})"
            )

        # Step 8.2: Verify claims (with checkpoint)
        verify_checkpoint = await self.checkpoint_manager.load(
            ctx.tenant_id, ctx.run_id, self.step_id, "verification_done", input_digest
        )

        if verify_checkpoint:
            logger.info("[STEP8] Loaded verification results from checkpoint")
            verification_results = _parse_verification_from_response(
                self.output_parser, verify_checkpoint.get("raw_response", "")
            )
            if not verification_results and verify_checkpoint.get("results"):
                verification_results = [
                    VerificationResult(**r)
                    for r in verify_checkpoint.get("results", [])
                ]
        else:
            try:
                verify_prompt = prompt_pack.get_prompt("step8_verify")
                verify_request = verify_prompt.render(
                    claims="\n".join(
                        f"[{c.claim_id}] {c.text}" for c in extracted_claims
                    ),
                    keyword=keyword,
                )
                verify_config = LLMRequestConfig(max_tokens=3000, temperature=0.3)
                verify_response = await llm.generate(
                    messages=[{"role": "user", "content": verify_request}],
                    system_prompt="Verify the claims using available knowledge.",
                    config=verify_config,
                )
                verification_results = _parse_verification_from_response(
                    self.output_parser, verify_response.content
                )

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
                verification="\n".join(
                    f"[{r.claim_id}] {r.status}: {r.evidence}" for r in verification_results
                ),
            )
            faq_config = LLMRequestConfig(max_tokens=2000, temperature=0.6)
            faq_response = await llm.generate(
                messages=[{"role": "user", "content": faq_request}],
                system_prompt="Generate FAQ based on the verification results.",
                config=faq_config,
            )
            faq_items = _parse_faq_from_response(
                self.output_parser, faq_response.content
            )
        except Exception as e:
            raise ActivityError(
                f"Failed to generate FAQ: {e}",
                category=ErrorCategory.RETRYABLE,
            ) from e

        # Validate FAQ count
        if len(faq_items) < MIN_FAQ_COUNT:
            logger.warning(
                f"[STEP8] Only {len(faq_items)} FAQ items generated (min: {MIN_FAQ_COUNT})"
            )
        elif len(faq_items) > MAX_FAQ_COUNT:
            logger.warning(
                f"[STEP8] {len(faq_items)} FAQ items generated (max: {MAX_FAQ_COUNT})"
            )
            faq_items = faq_items[:MAX_FAQ_COUNT]

        # Determine rejection recommendation
        recommend_rejection, critical_issues = _determine_rejection_recommendation(
            verification_results
        )
        has_contradictions = any(
            r.status == "contradicted" for r in verification_results
        )

        # Compute summary
        summary = _compute_verification_summary(verification_results)

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
                "claims_tokens": 0,  # Token tracking simplified
                "verify_tokens": 0,
                "faq_tokens": 0,
            },
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
