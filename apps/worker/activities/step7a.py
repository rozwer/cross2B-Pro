"""Step 7A: Draft Generation Activity.

Generates the first draft of the article based on integration package.
This is the longest step (600s timeout) due to long-form content generation.
Uses Claude for high-quality content generation.

Integrated helpers:
- InputValidator: Validates integration_package input
- OutputParser: Parses JSON/Markdown hybrid responses
- QualityValidator: Validates draft completeness and quality
- ContentMetrics: Calculates detailed text metrics
- CheckpointManager: Manages draft progress with continuation support
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
from apps.worker.activities.schemas.step7a import (
    DraftQuality,
    DraftQualityMetrics,
    GenerationStats,
    Step7aOutput,
)
from apps.worker.helpers import (
    CheckpointManager,
    CompletenessValidator,
    CompositeValidator,
    ContentMetrics,
    InputValidator,
    OutputParser,
    StructureValidator,
)

from .base import ActivityError, BaseActivity, load_step_data

# 定数
MIN_WORD_COUNT = 1000
MIN_SECTION_COUNT = 3


class Step7ADraftGeneration(BaseActivity):
    """Activity for article draft generation."""

    def __init__(self) -> None:
        """Initialize with helpers."""
        super().__init__()
        self.input_validator = InputValidator()
        self.parser = OutputParser()
        self.metrics = ContentMetrics()
        self.checkpoint = CheckpointManager(self.store)

        # ドラフト品質検証
        self.draft_validator = CompositeValidator(
            [
                StructureValidator(
                    min_h2_sections=MIN_SECTION_COUNT,
                    require_h3=False,
                    min_word_count=MIN_WORD_COUNT,
                ),
                CompletenessValidator(
                    conclusion_patterns=["まとめ", "結論", "おわり", "conclusion"],
                    check_truncation=True,
                ),
            ]
        )

    @property
    def step_id(self) -> str:
        return "step7a"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute draft generation.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with draft content
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

        # Load step data from storage
        step6_5_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step6_5") or {}

        # === InputValidator統合 ===
        validation = self.input_validator.validate(
            data={"step6_5": step6_5_data},
            required=["step6_5.integration_package"],
            recommended=[],
            min_lengths={"step6_5.integration_package": 500},
        )

        if not validation.is_valid:
            raise ActivityError(
                f"Critical inputs missing: {validation.missing_required}",
                category=ErrorCategory.NON_RETRYABLE,
                details={"missing": validation.missing_required},
            )

        integration_package = step6_5_data.get("integration_package", "")

        # === CheckpointManager統合: 部分生成のチェックポイント ===
        draft_checkpoint = await self.checkpoint.load(ctx.tenant_id, ctx.run_id, self.step_id, "draft_progress")

        checkpoint_resumed = False
        continuation_used = False

        if draft_checkpoint and draft_checkpoint.get("needs_continuation"):
            current_draft = draft_checkpoint.get("draft", "")
            checkpoint_resumed = True
            activity.logger.info(f"Resuming from checkpoint: {len(current_draft)} chars done")

            # 続きを生成
            continuation = await self._continue_generation(config, current_draft, integration_package)
            current_draft = current_draft + "\n\n" + continuation
            continuation_used = True
        else:
            # 最初から生成
            current_draft = await self._generate_draft(config, keyword, integration_package, prompt_pack)

        # === OutputParser統合 (ハイブリッド) ===
        parse_result = self.parser.parse_json(current_draft)

        draft_content = current_draft
        llm_word_count = 0
        section_count = 0
        cta_positions: list[str] = []

        if parse_result.success and parse_result.data:
            data = parse_result.data
            if isinstance(data, dict):
                draft_content = str(data.get("draft", current_draft))
                llm_word_count = data.get("word_count", 0)
                section_count = data.get("section_count", 0)
                cta_positions = data.get("cta_positions", [])

            if parse_result.fixes_applied:
                activity.logger.info(f"JSON fixes applied: {parse_result.fixes_applied}")
        else:
            # Markdownフォールバック
            if self.parser.looks_like_markdown(current_draft):
                activity.logger.info("Treating response as markdown (JSON parse failed)")
                draft_content = current_draft
                section_count = len(re.findall(r"^##\s", current_draft, re.M))

        # === QualityValidator統合: 完全性チェック ===
        quality_result = self.draft_validator.validate(draft_content)

        # 切れていた場合は続きを生成
        if not quality_result.is_acceptable and "appears_truncated" in quality_result.issues:
            activity.logger.info("Draft appears truncated, generating continuation...")

            # チェックポイント保存
            await self.checkpoint.save(
                ctx.tenant_id,
                ctx.run_id,
                self.step_id,
                "draft_progress",
                {
                    "draft": draft_content,
                    "needs_continuation": True,
                },
            )

            continuation = await self._continue_generation(config, draft_content, integration_package)
            draft_content = draft_content + "\n\n" + continuation
            continuation_used = True

            # 再検証
            quality_result = self.draft_validator.validate(draft_content)

        # 最終チェックポイント保存
        await self.checkpoint.save(
            ctx.tenant_id,
            ctx.run_id,
            self.step_id,
            "draft_progress",
            {
                "draft": draft_content,
                "needs_continuation": False,
            },
        )

        # === ContentMetrics統合 ===
        text_metrics = self.metrics.text_metrics(draft_content)
        md_metrics = self.metrics.markdown_metrics(draft_content)
        keyword_density = self.metrics.keyword_density(draft_content, keyword)

        # Check for introduction and conclusion
        has_introduction = any(ind in draft_content.lower()[:500] for ind in ["はじめに", "導入", "introduction", "概要"])
        has_conclusion = any(ind in draft_content.lower() for ind in ["まとめ", "結論", "おわり", "conclusion"])

        # Build quality metrics
        quality_metrics = DraftQualityMetrics(
            word_count=text_metrics.word_count,
            char_count=text_metrics.char_count,
            section_count=md_metrics.h2_count,
            avg_section_length=text_metrics.word_count // max(1, md_metrics.h2_count),
            keyword_density=keyword_density,
            has_introduction=has_introduction,
            has_conclusion=has_conclusion,
        )

        # Build quality
        quality = DraftQuality(
            is_acceptable=quality_result.is_acceptable,
            issues=quality_result.issues,
            warnings=quality_result.warnings,
            scores=quality_result.scores,
        )

        # Build generation stats
        stats = GenerationStats(
            word_count=text_metrics.word_count,
            char_count=text_metrics.char_count,
            llm_reported_word_count=llm_word_count,
            continuation_used=continuation_used,
            checkpoint_resumed=checkpoint_resumed,
        )

        # Get response metadata
        response = getattr(self, "_last_response", None)
        model_name = response.model if response else ""
        usage = {
            "input_tokens": response.token_usage.input if response else 0,
            "output_tokens": response.token_usage.output if response else 0,
        }

        output = Step7aOutput(
            step=self.step_id,
            keyword=keyword,
            draft=draft_content,
            section_count=md_metrics.h2_count or section_count,
            cta_positions=cta_positions,
            quality_metrics=quality_metrics,
            quality=quality,
            stats=stats,
            generation_stats={
                "word_count": text_metrics.word_count,
                "char_count": text_metrics.char_count,
                "llm_reported_word_count": llm_word_count,
            },
            continued=continuation_used,
            model=model_name,
            usage=usage,
        )

        return output.model_dump()

    async def _generate_draft(
        self,
        config: dict[str, Any],
        keyword: str,
        integration_package: str,
        prompt_pack: Any,
    ) -> str:
        """Generate draft from scratch."""
        # Render prompt
        try:
            prompt_template = prompt_pack.get_prompt("step7a")
            prompt = prompt_template.render(
                keyword=keyword,
                integration_package=integration_package,
            )
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client
        model_config = config.get("model_config", {})
        llm_provider = model_config.get("platform", config.get("llm_provider", "anthropic"))
        llm_model = model_config.get("model", config.get("llm_model"))
        llm = get_llm_client(llm_provider, model=llm_model)

        try:
            llm_config = LLMRequestConfig(
                max_tokens=config.get("max_tokens", 16000),
                temperature=config.get("temperature", 0.7),
            )
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an SEO content writer.",
                config=llm_config,
            )
            self._last_response = response
            return response.content
        except Exception as e:
            raise ActivityError(
                f"LLM call failed: {e}",
                category=ErrorCategory.RETRYABLE,
            ) from e

    async def _continue_generation(
        self,
        config: dict[str, Any],
        current_draft: str,
        integration_package: str,
    ) -> str:
        """Generate continuation of draft."""
        continuation_prompt = f"""
以下は記事ドラフトの途中です。この続きから完成させてください。

## 現在のドラフト（最後の500文字）
{current_draft[-500:]}

## 統合パッケージ（参照用）
{integration_package[:2000]}

## 指示
- 既存の内容と自然につながるように続きを書いてください
- 必ず「まとめ」または「結論」セクションで締めくくってください
- JSON形式ではなく、マークダウン形式で出力してください
"""

        # Get LLM client
        model_config = config.get("model_config", {})
        llm_provider = model_config.get("platform", config.get("llm_provider", "anthropic"))
        llm_model = model_config.get("model", config.get("llm_model"))
        llm = get_llm_client(llm_provider, model=llm_model)

        try:
            llm_config = LLMRequestConfig(
                max_tokens=8000,
                temperature=0.7,
            )
            response = await llm.generate(
                messages=[{"role": "user", "content": continuation_prompt}],
                system_prompt="Continue the article draft.",
                config=llm_config,
            )
            return response.content
        except Exception as e:
            raise ActivityError(
                f"Continuation generation failed: {e}",
                category=ErrorCategory.RETRYABLE,
            ) from e


@activity.defn(name="step7a_draft_generation")
async def step7a_draft_generation(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 7A."""
    step = Step7ADraftGeneration()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
