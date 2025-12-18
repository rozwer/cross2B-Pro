"""Step 10: Final Output Activity.

Generates the final article output in the required format.
Includes HTML validation and publication checklist.
Uses Claude for final formatting.

Integrated helpers:
- InputValidator: Validates required inputs from step9
- OutputParser: Parses HTML from code blocks
- QualityValidator: Validates HTML structure and content quality
- ContentMetrics: Calculates text and markdown metrics
- CheckpointManager: Manages intermediate checkpoints for idempotency
- QualityRetryLoop: Retries LLM calls when quality is insufficient
"""

import re
from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.llm.base import get_llm_client
from apps.api.llm.schemas import LLMRequestConfig
from apps.api.prompts.loader import PromptPackLoader
from apps.worker.activities.schemas.step10 import (
    ArticleStats,
    HTMLValidationResult,
    PublicationReadiness,
    Step10Output,
)
from apps.worker.helpers import (
    CheckpointManager,
    CompositeValidator,
    ContentMetrics,
    InputValidator,
    OutputParser,
    QualityResult,
    QualityRetryLoop,
)

from .base import ActivityError, BaseActivity, load_step_data


class HTMLStructureValidator:
    """HTML構造の検証."""

    REQUIRED_TAGS = ["<html", "<head", "<body", "<title"]
    STRUCTURE_TAGS = ["<html", "<head", "<body"]

    def __init__(
        self,
        min_length: int = 500,
        require_meta: bool = True,
    ):
        self.min_length = min_length
        self.require_meta = require_meta

    def validate(self, content: str, **kwargs: str) -> QualityResult:
        """HTML構造を検証."""
        issues: list[str] = []
        warnings: list[str] = []
        scores: dict[str, float] = {}

        content_lower = content.lower()

        # Check minimum length
        if len(content) < self.min_length:
            issues.append(f"html_too_short: {len(content)} < {self.min_length}")

        # Check required tags
        found_tags = sum(1 for tag in self.REQUIRED_TAGS if tag in content_lower)
        scores["required_tags_found"] = float(found_tags)

        if found_tags < len(self.REQUIRED_TAGS):
            missing = [tag for tag in self.REQUIRED_TAGS if tag not in content_lower]
            issues.append(f"missing_html_tags: {missing}")

        # Check tag closure for structural tags
        for tag in self.STRUCTURE_TAGS:
            tag_name = tag[1:]  # Remove '<'
            close_tag = f"</{tag_name}>"
            open_count = content_lower.count(tag)
            close_count = content_lower.count(close_tag)
            if open_count != close_count:
                issues.append(f"unclosed_tag: {tag_name}")

        # Check for meta tags
        if self.require_meta:
            if "<meta" not in content_lower:
                warnings.append("no_meta_tags")

        # Check heading hierarchy
        h1_count = len(re.findall(r"<h1", content_lower))
        h2_count = len(re.findall(r"<h2", content_lower))
        scores["h1_count"] = float(h1_count)
        scores["h2_count"] = float(h2_count)

        if h1_count == 0:
            warnings.append("no_h1_heading")

        return QualityResult(
            is_acceptable=len(issues) == 0,
            issues=issues,
            warnings=warnings,
            scores=scores,
        )


class ChecklistValidator:
    """チェックリスト品質の検証."""

    CHECKLIST_INDICATORS = ["□", "☐", "[ ]", "・", "-", "1.", "✓", "✔"]

    def __init__(self, min_length: int = 100):
        self.min_length = min_length

    def validate(self, content: str, **kwargs: str) -> QualityResult:
        """チェックリストを検証."""
        issues: list[str] = []

        if len(content) < self.min_length:
            issues.append(f"checklist_too_short: {len(content)} < {self.min_length}")

        has_items = any(ind in content for ind in self.CHECKLIST_INDICATORS)
        if not has_items:
            issues.append("no_checklist_items")

        return QualityResult(
            is_acceptable=len(issues) == 0,
            issues=issues,
        )


class Step10FinalOutput(BaseActivity):
    """Activity for final output generation."""

    MIN_CONTENT_LENGTH = 1000

    def __init__(self) -> None:
        """Initialize with helpers."""
        super().__init__()
        self.input_validator = InputValidator()
        self.parser = OutputParser()
        self.metrics = ContentMetrics()
        self.checkpoint = CheckpointManager(self.store)

        # HTML品質検証
        self.html_validator = CompositeValidator([
            HTMLStructureValidator(min_length=500, require_meta=True),
        ])

        # チェックリスト品質検証
        self.checklist_validator = ChecklistValidator(min_length=100)

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
        warnings: list[str] = []

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

        if not keyword:
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Load step data from storage
        step9_data = await load_step_data(
            self.store, ctx.tenant_id, ctx.run_id, "step9"
        ) or {}

        # === InputValidator統合 ===
        validation = self.input_validator.validate(
            data={"step9": step9_data},
            required=["step9.final_content"],
            recommended=["step9.meta_description"],
            min_lengths={"step9.final_content": self.MIN_CONTENT_LENGTH},
        )

        if not validation.is_valid:
            raise ActivityError(
                f"Input validation failed: {validation.missing_required}",
                category=ErrorCategory.NON_RETRYABLE,
                details={"missing": validation.missing_required},
            )

        if validation.missing_recommended:
            activity.logger.warning(
                f"Recommended inputs missing: {validation.missing_recommended}"
            )
            warnings.extend(
                f"missing_{field}" for field in validation.missing_recommended
            )

        if validation.quality_issues:
            activity.logger.warning(f"Input quality issues: {validation.quality_issues}")
            warnings.extend(validation.quality_issues)

        final_content = step9_data.get("final_content", "")
        meta_description = step9_data.get("meta_description", "")
        article_title = step9_data.get("article_title", keyword)

        # Get LLM client (Claude for step10 - final formatting)
        model_config = config.get("model_config", {})
        llm_provider = model_config.get(
            "platform", config.get("llm_provider", "anthropic")
        )
        llm_model = model_config.get("model", config.get("llm_model"))
        llm = get_llm_client(llm_provider, model=llm_model)

        # === CheckpointManager統合: HTML生成のチェックポイント ===
        input_digest = self.checkpoint.compute_digest({
            "keyword": keyword,
            "final_content": final_content[:500],  # 先頭500文字でdigest
        })

        html_checkpoint = await self.checkpoint.load(
            ctx.tenant_id, ctx.run_id, self.step_id, "html_generated",
            input_digest=input_digest,
        )

        if html_checkpoint:
            html_content = html_checkpoint.get("html", "")
            html_tokens = html_checkpoint.get("tokens", 0)
            activity.logger.info("Loaded HTML from checkpoint")
        else:
            # === QualityRetryLoop統合: HTML生成 ===
            html_content, html_tokens = await self._generate_html_with_retry(
                llm, prompt_pack, config, keyword, final_content
            )

            await self.checkpoint.save(
                ctx.tenant_id, ctx.run_id, self.step_id, "html_generated",
                {"html": html_content, "tokens": html_tokens},
                input_digest=input_digest,
            )

        # === HTML検証 ===
        html_validation_result = self.html_validator.validate(html_content)
        if not html_validation_result.is_acceptable:
            activity.logger.warning(
                f"HTML validation issues: {html_validation_result.issues}"
            )
            warnings.extend(html_validation_result.issues)

        # === CheckpointManager統合: チェックリスト生成のチェックポイント ===
        checklist_checkpoint = await self.checkpoint.load(
            ctx.tenant_id, ctx.run_id, self.step_id, "checklist_generated",
            input_digest=input_digest,
        )

        if checklist_checkpoint:
            checklist = checklist_checkpoint.get("checklist", "")
            checklist_tokens = checklist_checkpoint.get("tokens", 0)
            activity.logger.info("Loaded checklist from checkpoint")
        else:
            # === チェックリスト生成（フォールバック禁止対応） ===
            checklist, checklist_tokens = await self._generate_checklist_with_retry(
                llm, prompt_pack, config, keyword, warnings
            )

            await self.checkpoint.save(
                ctx.tenant_id, ctx.run_id, self.step_id, "checklist_generated",
                {"checklist": checklist, "tokens": checklist_tokens},
                input_digest=input_digest,
            )

        # === ContentMetrics統合 ===
        text_metrics = self.metrics.text_metrics(final_content)
        md_metrics = self.metrics.markdown_metrics(final_content)

        stats = ArticleStats(
            word_count=text_metrics.word_count,
            char_count=text_metrics.char_count,
            paragraph_count=text_metrics.paragraph_count,
            sentence_count=text_metrics.sentence_count,
            heading_count=md_metrics.h2_count + md_metrics.h3_count + md_metrics.h4_count,
            h1_count=md_metrics.h1_count,
            h2_count=md_metrics.h2_count,
            h3_count=md_metrics.h3_count,
            list_count=md_metrics.list_count,
            link_count=md_metrics.link_count,
            image_count=md_metrics.image_count,
        )

        # Build HTML validation result
        html_validation = HTMLValidationResult(
            is_valid=html_validation_result.is_acceptable,
            has_required_tags=html_validation_result.scores.get("required_tags_found", 0) >= 4,
            has_meta_tags="no_meta_tags" not in html_validation_result.warnings,
            has_proper_heading_hierarchy="no_h1_heading" not in html_validation_result.warnings,
            issues=html_validation_result.issues,
        )

        # Determine publication readiness
        blocking_issues: list[str] = []
        if not html_validation.is_valid:
            blocking_issues.extend(html_validation.issues)
        if stats.word_count < 500:
            blocking_issues.append(f"word_count_too_low: {stats.word_count}")

        publication_readiness = PublicationReadiness(
            is_ready=len(blocking_issues) == 0,
            blocking_issues=blocking_issues,
            warnings=warnings,
        )

        # Build structured output
        output = Step10Output(
            step=self.step_id,
            keyword=keyword,
            article_title=article_title,
            markdown_content=final_content,
            html_content=html_content,
            meta_description=meta_description,
            publication_checklist=checklist,
            html_validation=html_validation,
            stats=stats,
            publication_readiness=publication_readiness,
            model=llm_provider,
            usage={
                "html_tokens": html_tokens,
                "checklist_tokens": checklist_tokens,
            },
            warnings=warnings,
        )

        # Save HTML preview file separately for preview API
        if html_content:
            preview_path = self.store.build_path(
                tenant_id=ctx.tenant_id,
                run_id=ctx.run_id,
                step=self.step_id,
            ).replace("/output.json", "/preview.html")
            await self.store.put(
                content=html_content.encode("utf-8"),
                path=preview_path,
                content_type="text/html",
            )
            activity.logger.info(f"Saved HTML preview to {preview_path}")

        return output.model_dump()

    async def _generate_html_with_retry(
        self,
        llm: Any,
        prompt_pack: Any,
        config: dict[str, Any],
        keyword: str,
        content: str,
    ) -> tuple[str, int]:
        """HTML生成（品質リトライ付き）."""

        async def llm_call(prompt_text: str) -> str:
            html_config = LLMRequestConfig(
                max_tokens=config.get("max_tokens", 8000),
                temperature=0.3,
            )
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt_text}],
                system_prompt="You are an HTML formatting expert.",
                config=html_config,
            )
            self._last_html_response = response
            return str(response.content)

        def enhance_prompt(original: str, issues: list[str]) -> str:
            guidance = []
            if any("missing_html_tags" in issue for issue in issues):
                guidance.append("- 必ず<html>, <head>, <body>, <title>タグを含めてください")
            if any("unclosed_tag" in issue for issue in issues):
                guidance.append("- すべてのタグを正しく閉じてください")
            if any("html_too_short" in issue for issue in issues):
                guidance.append("- 出力が短すぎます。完全なHTMLを生成してください")

            if guidance:
                return original + "\n\n【追加の指示】\n" + "\n".join(guidance)
            return original

        # Render prompt
        html_prompt = prompt_pack.get_prompt("step10_html")
        initial_prompt = html_prompt.render(
            keyword=keyword,
            content=content,
        )

        retry_loop = QualityRetryLoop(
            max_retries=1,
            accept_on_final=True,
        )

        result = await retry_loop.execute(
            llm_call=llm_call,
            initial_prompt=initial_prompt,
            validator=self.html_validator,
            enhance_prompt=enhance_prompt,
            extract_content=lambda x: x,
        )

        html_content = result.result or ""

        # コードブロックがある場合は除去
        if "```html" in html_content or "```" in html_content:
            html_content = self.parser.extract_json_block(html_content)

        response = getattr(self, "_last_html_response", None)
        tokens = response.token_usage.output if response else 0

        return html_content, tokens

    async def _generate_checklist_with_retry(
        self,
        llm: Any,
        prompt_pack: Any,
        config: dict[str, Any],
        keyword: str,
        warnings: list[str],
    ) -> tuple[str, int]:
        """チェックリスト生成（品質リトライ付き、フォールバック禁止対応）."""

        async def llm_call(prompt_text: str) -> str:
            checklist_config = LLMRequestConfig(max_tokens=1000, temperature=0.3)
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt_text}],
                system_prompt="You are a publication checklist expert.",
                config=checklist_config,
            )
            self._last_checklist_response = response
            return str(response.content)

        # Render prompt
        checklist_prompt = prompt_pack.get_prompt("step10_checklist")
        initial_prompt = checklist_prompt.render(keyword=keyword)

        retry_loop = QualityRetryLoop(
            max_retries=1,
            accept_on_final=True,
        )

        try:
            result = await retry_loop.execute(
                llm_call=llm_call,
                initial_prompt=initial_prompt,
                validator=self.checklist_validator,
                enhance_prompt=None,
                extract_content=lambda x: x,
            )

            checklist = result.result or ""
            response = getattr(self, "_last_checklist_response", None)
            tokens = response.token_usage.output if response else 0

            return checklist, tokens

        except Exception as e:
            # フォールバック禁止: ダミー文字列ではなく空を返す
            activity.logger.error(f"Checklist generation failed: {e}")
            warnings.append("checklist_generation_failed")
            return "", 0


@activity.defn(name="step10_final_output")
async def step10_final_output(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 10."""
    step = Step10FinalOutput()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
