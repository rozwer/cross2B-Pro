"""Step 10: Final Output Activity.

Generates the final article output in the required format.
Includes HTML validation and publication checklist.
Uses Claude for final formatting.
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
from apps.api.validation import Step9OutputValidator
from apps.api.validation.schemas import ValidationReport

from .base import ActivityError, BaseActivity

logger = logging.getLogger(__name__)


class Step10FinalOutput(BaseActivity):
    """Activity for final output generation."""

    @property
    def step_id(self) -> str:
        return "step10"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute final output generation.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with final article and metadata
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
        step9_data = config.get("step9_data", {})

        if not keyword:
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Validate and repair step9 output before proceeding
        validation_report = self._validate_step9_output(step9_data)

        # Log any repairs that were applied
        if validation_report.repairs:
            logger.info(
                "Step9 output repairs applied",
                extra={
                    "run_id": ctx.run_id,
                    "repair_count": len(validation_report.repairs),
                    "repairs": [
                        {"code": r.code, "description": r.description}
                        for r in validation_report.repairs
                    ],
                },
            )

        if not validation_report.valid:
            error_messages = [
                f"[{issue.code}] {issue.message}"
                for issue in validation_report.issues
                if issue.severity.value == "error"
            ]
            raise ActivityError(
                f"Step9 output validation failed: {'; '.join(error_messages)}",
                category=ErrorCategory.VALIDATION_FAIL,
                details={
                    "validation_issues": [
                        {
                            "code": issue.code,
                            "message": issue.message,
                            "severity": issue.severity.value,
                            "location": issue.location,
                        }
                        for issue in validation_report.issues
                    ],
                    "repairs_applied": [
                        {"code": r.code, "description": r.description}
                        for r in validation_report.repairs
                    ],
                },
            )

        # Use the (potentially repaired) content from step9_data
        final_content = step9_data.get("final_content", "")

        # Get LLM client (Claude for step10 - final formatting)
        llm_provider = config.get("llm_provider", "anthropic")
        llm_model = config.get("llm_model")
        llm = get_llm_client(llm_provider, model=llm_model)

        # Step 10.1: Generate final HTML
        checklist_response = None
        try:
            html_prompt = prompt_pack.get_prompt("step10_html")
            html_request = html_prompt.render(
                keyword=keyword,
                content=final_content,
            )
            html_config = LLMRequestConfig(
                max_tokens=config.get("max_tokens", 8000),
                temperature=0.3,  # Low for consistent formatting
            )
            html_response = await llm.generate(
                messages=[{"role": "user", "content": html_request}],
                system_prompt="You are an HTML formatting expert.",
                config=html_config,
            )
            html_content = html_response.content
        except Exception as e:
            raise ActivityError(
                f"Failed to generate HTML: {e}",
                category=ErrorCategory.RETRYABLE,
            ) from e

        # Step 10.2: Validate HTML structure
        html_valid = self._validate_html(html_content)
        if not html_valid:
            raise ActivityError(
                "HTML validation failed - broken HTML output is forbidden",
                category=ErrorCategory.VALIDATION_FAIL,
                details={"html_preview": html_content[:500]},
            )

        # Step 10.3: Generate publication checklist
        try:
            checklist_prompt = prompt_pack.get_prompt("step10_checklist")
            checklist_request = checklist_prompt.render(keyword=keyword)
            checklist_config = LLMRequestConfig(max_tokens=1000, temperature=0.3)
            checklist_response = await llm.generate(
                messages=[{"role": "user", "content": checklist_request}],
                system_prompt="You are a publication checklist expert.",
                config=checklist_config,
            )
            checklist = checklist_response.content
        except Exception:
            # Checklist is nice-to-have, continue if fails
            checklist = "Publication checklist generation failed."

        # Calculate final stats
        word_count = len(final_content.split())
        char_count = len(final_content)

        checklist_tokens = 0
        if checklist_response:
            checklist_tokens = checklist_response.token_usage.output

        # Build result with validation info
        result = {
            "step": self.step_id,
            "keyword": keyword,
            "article": {
                "markdown": final_content,
                "html": html_content,
            },
            "publication_checklist": checklist,
            "stats": {
                "word_count": word_count,
                "char_count": char_count,
                "html_valid": html_valid,
            },
            "model": html_response.model,
            "usage": {
                "html_tokens": html_response.token_usage.output,
                "checklist_tokens": checklist_tokens,
            },
        }

        # Include validation metadata if repairs were applied
        if validation_report.repairs:
            result["validation"] = {
                "repairs_applied": [
                    {
                        "code": r.code,
                        "description": r.description,
                        "applied_at": r.applied_at.isoformat(),
                    }
                    for r in validation_report.repairs
                ],
                "original_hash": validation_report.original_hash,
                "repaired_hash": validation_report.repaired_hash,
            }

        return result

    def _validate_step9_output(
        self, step9_data: dict[str, Any]
    ) -> ValidationReport:
        """Validate and repair step9 output before processing.

        Applies deterministic repairs (BOM removal, line ending normalization,
        trailing whitespace trimming, heading level normalization) and validates
        the content structure.

        Args:
            step9_data: The output dictionary from step9 (modified in-place if repairs applied)

        Returns:
            ValidationReport with validation results and any repairs applied
        """
        validator = Step9OutputValidator()
        return validator.validate(step9_data, auto_repair=True)

    def _validate_html(self, html_content: str) -> bool:
        """Basic HTML validation.

        Args:
            html_content: HTML string to validate

        Returns:
            True if HTML is structurally valid
        """
        # Basic tag matching validation
        required_tags = ["<html", "<head", "<body"]
        for tag in required_tags:
            if tag not in html_content.lower():
                return False

        # Check for unclosed major tags
        open_tags = ["<html", "<head", "<body", "<div", "<p"]
        close_tags = ["</html>", "</head>", "</body>", "</div>", "</p>"]

        for open_tag, close_tag in zip(open_tags, close_tags):
            open_count = html_content.lower().count(open_tag)
            close_count = html_content.lower().count(close_tag)
            # Allow some flexibility (not all divs need closing in HTML5)
            if open_tag in ["<html", "<head", "<body"]:
                if open_count != close_count:
                    return False

        return True


@activity.defn(name="step10_final_output")
async def step10_final_output(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 10."""
    step = Step10FinalOutput()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
