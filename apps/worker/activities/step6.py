"""Step 6: Enhanced Outline Activity.

Enhances the strategic outline with primary sources and detailed structure.
Uses Claude for comprehensive outline enhancement.

Integrated helpers:
- InputValidator: Validates required/recommended inputs from previous steps
- OutputParser: Parses JSON/Markdown responses from LLM
- QualityValidator: Validates outline enhancement quality
- ContentMetrics: Calculates text and markdown metrics
- CheckpointManager: Manages intermediate checkpoints for idempotency
"""

import hashlib
import re
from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.llm.base import get_llm_client
from apps.api.llm.schemas import LLMRequestConfig
from apps.api.prompts.loader import PromptPackLoader
from apps.worker.activities.schemas.step6 import (
    EnhancedOutlineMetrics,
    EnhancedOutlineQuality,
    EnhancementSummary,
    Step6Output,
)
from apps.worker.helpers import (
    CheckpointManager,
    CompletenessValidator,
    CompositeValidator,
    ContentMetrics,
    InputValidator,
    OutputParser,
    QualityRetryLoop,
    StructureValidator,
)

from .base import ActivityError, BaseActivity, load_step_data


class Step6EnhancedOutline(BaseActivity):
    """Activity for enhanced outline generation."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.input_validator = InputValidator()
        self.parser = OutputParser()
        self.metrics = ContentMetrics()
        self.checkpoint = CheckpointManager(self.store)

        # アウトライン拡張品質検証
        self.outline_validator = CompositeValidator([
            StructureValidator(
                min_h2_sections=3,
                require_h3=True,  # 拡張なのでH3必須
                min_word_count=200,
            ),
            CompletenessValidator(
                conclusion_patterns=["まとめ", "結論", "おわり", "conclusion"],
                check_truncation=True,
            ),
        ])

    @property
    def step_id(self) -> str:
        return "step6"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute enhanced outline generation.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with enhanced outline
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

        if not keyword:
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Load step data from storage (not from config to avoid gRPC size limits)
        step4_data = await load_step_data(
            self.store, ctx.tenant_id, ctx.run_id, "step4"
        ) or {}
        step5_data = await load_step_data(
            self.store, ctx.tenant_id, ctx.run_id, "step5"
        ) or {}

        # === InputValidator統合 ===
        validation = self.input_validator.validate(
            data={
                "step4": step4_data,
                "step5": step5_data,
            },
            required=["step4.outline"],  # step4 のアウトラインは必須
            recommended=["step5.sources"],  # step5 のソースは推奨
        )

        if not validation.is_valid:
            raise ActivityError(
                f"Critical inputs missing: {validation.missing_required}",
                category=ErrorCategory.NON_RETRYABLE,
                details={"missing": validation.missing_required},
            )

        if validation.missing_recommended:
            activity.logger.warning(
                f"Recommended inputs missing: {validation.missing_recommended}"
            )

        original_outline = step4_data.get("outline", "")

        # === CheckpointManager統合: ソースサマリーのキャッシュ ===
        sources = step5_data.get("sources", [])
        input_digest = self.checkpoint.compute_digest({
            "keyword": keyword,
            "outline": original_outline[:500],
            "sources_count": len(sources),
        })

        source_checkpoint = await self.checkpoint.load(
            ctx.tenant_id, ctx.run_id, self.step_id, "source_summaries",
            input_digest=input_digest,
        )

        if source_checkpoint:
            source_summaries = source_checkpoint.get("summaries", [])
            url_to_id = source_checkpoint.get("url_to_id", {})
            activity.logger.info(f"Loaded {len(source_summaries)} source summaries from checkpoint")
        else:
            source_summaries, url_to_id = self._prepare_source_summaries(sources)
            await self.checkpoint.save(
                ctx.tenant_id, ctx.run_id, self.step_id, "source_summaries",
                {
                    "summaries": source_summaries,
                    "url_to_id": url_to_id,
                },
                input_digest=input_digest,
            )

        # Render prompt
        try:
            prompt_template = prompt_pack.get_prompt("step6")
            prompt = prompt_template.render(
                keyword=keyword,
                outline=original_outline,
                sources=source_summaries,
            )
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client (Claude for step6)
        model_config = config.get("model_config", {})
        llm_provider = model_config.get("platform", config.get("llm_provider", "anthropic"))
        llm_model = model_config.get("model", config.get("llm_model"))
        llm = get_llm_client(llm_provider, model=llm_model)

        llm_config = LLMRequestConfig(
            max_tokens=config.get("max_tokens", 5000),
            temperature=config.get("temperature", 0.6),
        )

        # === QualityRetryLoop統合 ===
        async def llm_call(prompt_text: str) -> str:
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt_text}],
                system_prompt="You are an SEO content outline specialist.",
                config=llm_config,
            )
            self._last_response = response
            return response.content

        def enhance_prompt(original: str, issues: list[str]) -> str:
            guidance = []
            if any("h2_count" in issue for issue in issues):
                guidance.append("- 最低3つのH2セクションを含めてください")
            if any("h3" in issue.lower() for issue in issues):
                guidance.append("- 各H2セクションに少なくとも1つのH3サブセクションを追加してください")
            if "no_conclusion_section" in issues:
                guidance.append("- 「まとめ」または「結論」セクションを追加してください")
            if "appears_truncated" in issues:
                guidance.append("- 文章を途中で切らず、最後まで完結させてください")

            if guidance:
                return original + "\n\n【追加の指示】\n" + "\n".join(guidance)
            return original

        retry_loop = QualityRetryLoop(
            max_retries=1,
            accept_on_final=True,
        )

        result = await retry_loop.execute(
            llm_call=llm_call,
            initial_prompt=prompt,
            validator=self.outline_validator,
            enhance_prompt=enhance_prompt,
            extract_content=lambda x: x,
        )

        if not result.success:
            raise ActivityError(
                f"Failed to generate acceptable enhanced outline: {result.quality.issues if result.quality else 'unknown'}",
                category=ErrorCategory.RETRYABLE,
            )

        enhanced_outline = result.result or ""
        quality_result = result.quality

        # === OutputParser統合 ===
        parse_result = self.parser.parse_json(enhanced_outline)

        if parse_result.success and parse_result.data:
            data = parse_result.data
            if isinstance(data, dict):
                enhanced_outline = str(data.get("enhanced_outline", data.get("outline", enhanced_outline)))
            if parse_result.fixes_applied:
                activity.logger.info(f"JSON fixes applied: {parse_result.fixes_applied}")
        else:
            if self.parser.looks_like_markdown(enhanced_outline):
                activity.logger.info("Treating response as markdown (JSON parse failed)")

        # === ContentMetrics統合 ===
        text_metrics = self.metrics.text_metrics(enhanced_outline)
        md_metrics = self.metrics.markdown_metrics(enhanced_outline)
        original_text_metrics = self.metrics.text_metrics(original_outline)

        # === QualityValidator統合: 拡張品質チェック ===
        enhancement_quality = self._validate_enhancement_quality(
            original_outline, enhanced_outline
        )

        if not enhancement_quality.is_acceptable:
            activity.logger.warning(f"Enhancement quality issues: {enhancement_quality.issues}")

        # Build metrics
        metrics = EnhancedOutlineMetrics(
            word_count=text_metrics.word_count,
            char_count=text_metrics.char_count,
            h2_count=md_metrics.h2_count,
            h3_count=md_metrics.h3_count,
            h4_count=md_metrics.h4_count,
            original_word_count=original_text_metrics.word_count,
            word_increase=text_metrics.word_count - original_text_metrics.word_count,
        )

        # Build quality
        quality = EnhancedOutlineQuality(
            is_acceptable=quality_result.is_acceptable if quality_result else True,
            issues=quality_result.issues if quality_result else [],
            warnings=quality_result.warnings if quality_result else [],
            scores=quality_result.scores if quality_result else {},
        )

        # Enhancement summary
        enhancement_summary = EnhancementSummary(
            sections_enhanced=md_metrics.h2_count,
            sections_added=max(0, md_metrics.h3_count - self.metrics.markdown_metrics(original_outline).h3_count),
            sources_integrated=len(source_summaries),
            total_word_increase=metrics.word_increase,
        )

        # Get response metadata
        response = getattr(self, "_last_response", None)
        model_name = response.model if response else ""
        usage = {
            "input_tokens": response.token_usage.input if response else 0,
            "output_tokens": response.token_usage.output if response else 0,
        }

        # Compute original outline hash
        original_outline_hash = hashlib.sha256(original_outline.encode()).hexdigest()[:16]

        output = Step6Output(
            step=self.step_id,
            keyword=keyword,
            enhanced_outline=enhanced_outline,
            enhancement_summary=enhancement_summary,
            source_citations=url_to_id,
            original_outline_hash=original_outline_hash,
            metrics=metrics,
            quality=quality,
            sources_used=len(source_summaries),
            model=model_name,
            usage=usage,
            warnings=enhancement_quality.warnings,
        )

        return output.model_dump()

    def _prepare_source_summaries(
        self, sources: list[dict[str, Any]]
    ) -> tuple[list[dict[str, str]], dict[str, list[str]]]:
        """Prepare source summaries for prompt.

        Returns:
            tuple: (source_summaries, url_to_id mapping)
        """
        source_summaries = []
        url_to_id: dict[str, list[str]] = {}

        for i, s in enumerate(sources[:10]):  # Top 10 sources
            source_id = f"[S{i+1}]"
            url = s.get("url", "")
            summary = {
                "id": source_id,
                "url": url,
                "title": s.get("title", ""),
                "excerpt": s.get("excerpt", "")[:200],
            }
            source_summaries.append(summary)

            if url:
                if url not in url_to_id:
                    url_to_id[url] = []
                url_to_id[url].append(source_id)

        return source_summaries, url_to_id

    def _validate_enhancement_quality(
        self, original: str, enhanced: str
    ) -> EnhancedOutlineQuality:
        """Validate enhancement quality."""
        issues: list[str] = []
        warnings: list[str] = []
        scores: dict[str, float] = {}

        # Check: Enhanced should be longer than original
        if len(enhanced) < len(original):
            warnings.append("enhanced_shorter_than_original")

        # Check: All H2 sections from original should be preserved
        original_h2s = set(re.findall(r"^##\s+(.+)$", original, re.M))
        enhanced_h2s = set(re.findall(r"^##\s+(.+)$", enhanced, re.M))

        if not original_h2s <= enhanced_h2s:
            missing = original_h2s - enhanced_h2s
            warnings.append(f"h2_sections_missing: {missing}")

        # Check: Enhanced should have more H3 subsections
        original_h3_count = len(re.findall(r"^###\s", original, re.M))
        enhanced_h3_count = len(re.findall(r"^###\s", enhanced, re.M))
        scores["h3_increase"] = float(enhanced_h3_count - original_h3_count)

        if enhanced_h3_count <= original_h3_count:
            warnings.append("no_h3_increase")

        # Calculate enhancement ratio
        if len(original) > 0:
            enhancement_ratio = len(enhanced) / len(original)
            scores["enhancement_ratio"] = enhancement_ratio

        return EnhancedOutlineQuality(
            is_acceptable=len(issues) == 0,
            issues=issues,
            warnings=warnings,
            scores=scores,
        )


@activity.defn(name="step6_enhanced_outline")
async def step6_enhanced_outline(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 6."""
    step = Step6EnhancedOutline()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
