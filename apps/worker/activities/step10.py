"""Step 10: Final Output Activity.

Generates the final article output in the required format.
Includes HTML validation and publication checklist.
Uses Claude for final formatting.
"""

from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.llm.base import get_llm_client
from apps.api.llm.schemas import LLMRequestConfig
from apps.api.prompts.loader import PromptPackLoader

from .base import ActivityError, BaseActivity, load_step_data


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

        # Load step data from storage (not from config to avoid gRPC size limits)
        step9_data = await load_step_data(
            self.store, ctx.tenant_id, ctx.run_id, "step9"
        ) or {}
        final_content = step9_data.get("final_content", "")

        if not keyword:
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        if not final_content:
            raise ActivityError(
                "final content is required - run step9 first",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Get LLM client (Claude for step10 - final formatting)
        model_config = config.get("model_config", {})
        llm_provider = model_config.get("platform", config.get("llm_provider", "anthropic"))
        llm_model = model_config.get("model", config.get("llm_model"))
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

        # Step 10.2: Validate HTML structure (warning only, don't fail)
        html_valid = self._validate_html(html_content)
        if not html_valid:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"[STEP10] HTML validation warning - structure may be incomplete")

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

        return {
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
