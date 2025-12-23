"""Step 4: Strategic Outline Activity.

Creates the strategic article outline based on analysis from steps 0-3.
Uses Claude for structured outline generation.

Integrated helpers:
- InputValidator: Validates required/recommended inputs from previous steps
- OutputParser: Parses JSON/Markdown responses from LLM
- QualityValidator: Validates outline structure and content quality
- ContentMetrics: Calculates text and markdown metrics
- CheckpointManager: Manages intermediate checkpoints for idempotency
- QualityRetryLoop: Retries LLM calls when quality is insufficient
"""

from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.llm.base import get_llm_client
from apps.api.llm.schemas import LLMRequestConfig
from apps.api.prompts.loader import PromptPackLoader
from apps.worker.activities.schemas.step4 import (
    OutlineMetrics,
    OutlineQuality,
    Step4Output,
)
from apps.worker.helpers import (
    CheckpointManager,
    CompletenessValidator,
    CompositeValidator,
    ContentMetrics,
    InputValidator,
    KeywordValidator,
    OutputParser,
    QualityRetryLoop,
    StructureValidator,
)

from .base import ActivityError, BaseActivity, load_step_data


class Step4StrategicOutline(BaseActivity):
    """Activity for strategic outline generation."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.input_validator = InputValidator()
        self.parser = OutputParser()
        self.metrics = ContentMetrics()
        self.checkpoint = CheckpointManager(self.store)

        # アウトライン品質検証
        self.outline_validator = CompositeValidator(
            [
                StructureValidator(
                    min_h2_sections=3,
                    require_h3=False,
                    min_word_count=100,
                ),
                CompletenessValidator(
                    conclusion_patterns=["まとめ", "結論", "おわり", "conclusion"],
                    check_truncation=True,
                ),
            ]
        )

    @property
    def step_id(self) -> str:
        return "step4"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute strategic outline generation.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with strategic outline
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

        # Get inputs from previous steps
        keyword = config.get("keyword")

        if not keyword:
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Load step data from storage (not from config to avoid gRPC size limits)
        step0_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step0") or {}
        step3a_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step3a") or {}
        step3b_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step3b") or {}
        step3c_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step3c") or {}

        # === InputValidator統合 ===
        validation = self.input_validator.validate(
            data={
                "step0": step0_data,
                "step3a": step3a_data,
                "step3b": step3b_data,
                "step3c": step3c_data,
            },
            required=[
                "step3a.query_analysis",  # 検索意図・ペルソナは必須
                "step3b.cooccurrence_analysis",  # 共起キーワードは必須
            ],
            recommended=[
                "step0.analysis",  # キーワード分析
                "step3c.competitor_analysis",  # 競合分析は推奨
            ],
        )

        if not validation.is_valid:
            raise ActivityError(
                f"Critical inputs missing: {validation.missing_required}",
                category=ErrorCategory.NON_RETRYABLE,
                details={"missing": validation.missing_required},
            )

        if validation.missing_recommended:
            activity.logger.warning(f"Recommended inputs missing: {validation.missing_recommended}")

        if validation.quality_issues:
            activity.logger.warning(f"Input quality issues: {validation.quality_issues}")

        # === CheckpointManager統合: 統合データのチェックポイント ===
        input_digest = self.checkpoint.compute_digest(
            {
                "keyword": keyword,
                "step3a": step3a_data.get("query_analysis", ""),
                "step3b": step3b_data.get("cooccurrence_analysis", ""),
                "step3c": step3c_data.get("competitor_analysis", ""),
            }
        )

        integrated_checkpoint = await self.checkpoint.load(
            ctx.tenant_id,
            ctx.run_id,
            self.step_id,
            "integrated_inputs",
            input_digest=input_digest,
        )

        if integrated_checkpoint:
            integrated_data = integrated_checkpoint
            activity.logger.info("Loaded integrated inputs from checkpoint")
        else:
            # 統合処理
            integrated_data = self._integrate_analysis_data(
                keyword=keyword,
                query_analysis=step3a_data.get("query_analysis", ""),
                cooccurrence=step3b_data.get("cooccurrence_analysis", ""),
                competitor=step3c_data.get("competitor_analysis", ""),
            )

            await self.checkpoint.save(
                ctx.tenant_id,
                ctx.run_id,
                self.step_id,
                "integrated_inputs",
                integrated_data,
                input_digest=input_digest,
            )

        # Render prompt with all analysis inputs
        try:
            prompt_template = prompt_pack.get_prompt("step4")
            prompt = prompt_template.render(
                keyword=keyword,
                query_analysis=step3a_data.get("query_analysis", ""),
                cooccurrence_analysis=step3b_data.get("cooccurrence_analysis", ""),
                competitor_analysis=step3c_data.get("competitor_analysis", ""),
            )
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client from model_config
        model_config = config.get("model_config", {})
        llm_provider = model_config.get("platform", config.get("llm_provider", "gemini"))
        llm_model = model_config.get("model", config.get("llm_model"))
        llm = get_llm_client(llm_provider, model=llm_model)

        llm_config = LLMRequestConfig(
            max_tokens=config.get("max_tokens", 4000),
            temperature=config.get("temperature", 0.6),
        )

        # === QualityRetryLoop統合 ===
        # キーワード検証を追加
        keyword_validator = KeywordValidator(min_density=0.0, max_density=5.0)

        async def llm_call(prompt_text: str) -> str:
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt_text}],
                system_prompt="You are an SEO content strategist.",
                config=llm_config,
            )
            # Store response metadata for later use
            self._last_response = response
            return response.content

        def enhance_prompt(original: str, issues: list[str]) -> str:
            guidance = []
            if any("h2_count" in issue for issue in issues):
                guidance.append("- 最低3つのH2セクションを含めてください")
            if any("keyword" in issue for issue in issues):
                guidance.append(f"- キーワード「{keyword}」を見出しに含めてください")
            if "no_conclusion_section" in issues:
                guidance.append("- 「まとめ」または「結論」セクションを追加してください")
            if "appears_truncated" in issues:
                guidance.append("- 文章を途中で切らず、最後まで完結させてください")

            if guidance:
                return original + "\n\n【追加の指示】\n" + "\n".join(guidance)
            return original

        # Combined validator for retry loop
        combined_validator = CompositeValidator(
            [
                self.outline_validator.validators[0],  # StructureValidator
                self.outline_validator.validators[1],  # CompletenessValidator
                keyword_validator,
            ]
        )

        retry_loop = QualityRetryLoop(
            max_retries=1,
            accept_on_final=True,
        )

        result = await retry_loop.execute(
            llm_call=llm_call,
            initial_prompt=prompt,
            validator=combined_validator,
            enhance_prompt=enhance_prompt,
            extract_content=lambda x: x,  # Already a string
        )

        if not result.success:
            raise ActivityError(
                f"Failed to generate acceptable outline: {result.quality.issues if result.quality else 'unknown'}",
                category=ErrorCategory.RETRYABLE,
            )

        outline_content = result.result or ""
        quality_result = result.quality

        # === OutputParser統合 ===
        # Try to parse as JSON first
        parse_result = self.parser.parse_json(outline_content)

        outline: str = outline_content
        if parse_result.success and parse_result.data:
            data = parse_result.data
            if isinstance(data, dict):
                outline = str(data.get("raw_outline", data.get("outline", outline_content)))
        else:
            # JSONパース失敗時はMarkdownとして処理
            if self.parser.looks_like_markdown(outline_content):
                activity.logger.info("Treating response as markdown (JSON parse failed)")

        if parse_result.fixes_applied:
            activity.logger.info(f"JSON fixes applied: {parse_result.fixes_applied}")

        # === ContentMetrics統合 ===
        text_metrics = self.metrics.text_metrics(outline)
        md_metrics = self.metrics.markdown_metrics(outline)

        # Build structured output
        metrics = OutlineMetrics(
            word_count=text_metrics.word_count,
            char_count=text_metrics.char_count,
            h2_count=md_metrics.h2_count,
            h3_count=md_metrics.h3_count,
            h4_count=md_metrics.h4_count,
        )

        quality = OutlineQuality(
            is_acceptable=quality_result.is_acceptable if quality_result else True,
            issues=quality_result.issues if quality_result else [],
            warnings=quality_result.warnings if quality_result else [],
            scores=quality_result.scores if quality_result else {},
        )

        # Get response metadata
        response = getattr(self, "_last_response", None)
        model_name = response.model if response else ""
        usage = {
            "input_tokens": response.token_usage.input if response else 0,
            "output_tokens": response.token_usage.output if response else 0,
        }

        output = Step4Output(
            step=self.step_id,
            keyword=keyword,
            outline=outline,
            metrics=metrics,
            quality=quality,
            model=model_name,
            usage=usage,
        )

        return output.model_dump()

    def _integrate_analysis_data(
        self,
        keyword: str,
        query_analysis: str,
        cooccurrence: str,
        competitor: str,
    ) -> dict[str, Any]:
        """Integrate analysis data from previous steps."""
        return {
            "keyword": keyword,
            "query_analysis_summary": query_analysis[:500] if query_analysis else "",
            "cooccurrence_summary": cooccurrence[:500] if cooccurrence else "",
            "competitor_summary": competitor[:500] if competitor else "",
            "integrated": True,
        }


@activity.defn(name="step4_strategic_outline")
async def step4_strategic_outline(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 4."""
    step = Step4StrategicOutline()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
