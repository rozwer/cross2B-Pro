"""Step 6.5: Integration Package Activity.

Creates the integrated package combining all analysis and outline work.
This is the critical handoff point before content generation.
Uses Claude for comprehensive integration.

Integrated helpers:
- InputValidator: Validates all 7 steps of input data
- OutputParser: Parses JSON responses with repair capability
- QualityValidator: Validates package completeness
- CheckpointManager: Manages all-data loading checkpoint
"""

from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.llm.base import get_llm_client
from apps.api.llm.schemas import LLMRequestConfig
from apps.api.prompts.loader import PromptPackLoader
from apps.worker.activities.schemas.step6_5 import (
    InputSummary,
    PackageQuality,
    Step6_5Output,
)
from apps.worker.helpers import (
    CheckpointManager,
    InputValidator,
    OutputParser,
    QualityResult,
)

from .base import ActivityError, BaseActivity, load_step_data


class Step65IntegrationPackage(BaseActivity):
    """Activity for integration package creation."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.input_validator = InputValidator()
        self.parser = OutputParser()
        self.checkpoint = CheckpointManager(self.store)

    @property
    def step_id(self) -> str:
        return "step6_5"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute integration package creation.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with integration package
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

        # Get keyword
        keyword = config.get("keyword")

        if not keyword:
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # === CheckpointManager統合: 全データロードのキャッシュ ===
        data_checkpoint = await self.checkpoint.load(ctx.tenant_id, ctx.run_id, self.step_id, "all_data_loaded")

        if data_checkpoint:
            all_data = data_checkpoint.get("all_data", {})
            integration_input = data_checkpoint.get("integration_input", {})
            activity.logger.info("Loaded all step data from checkpoint")
        else:
            # Load ALL step data from storage
            all_data = await self._load_all_step_data(ctx)
            integration_input = self._prepare_integration_input(all_data, keyword)

            await self.checkpoint.save(
                ctx.tenant_id,
                ctx.run_id,
                self.step_id,
                "all_data_loaded",
                {
                    "all_data": all_data,
                    "integration_input": integration_input,
                },
            )

        # === InputValidator統合: 7ステップ分の入力検証 ===
        validation = self.input_validator.validate(
            data=all_data,
            required=[
                "step4.outline",  # 戦略アウトラインは必須
                "step6.enhanced_outline",  # 拡張アウトラインは必須
            ],
            recommended=[
                "step0.analysis",
                "step3a.query_analysis",
                "step3b.cooccurrence_analysis",
                "step3c.competitor_analysis",
                "step3_5.emotional_analysis",
                "step5.sources",
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

        # Build input summaries
        input_summaries = self._build_input_summaries(all_data)

        # Render prompt
        try:
            prompt_template = prompt_pack.get_prompt("step6_5")
            prompt = prompt_template.render(**integration_input)
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client (Claude for step6.5 - comprehensive integration)
        model_config = config.get("model_config", {})
        llm_provider = model_config.get("platform", config.get("llm_provider", "anthropic"))
        llm_model = model_config.get("model", config.get("llm_model"))
        llm = get_llm_client(llm_provider, model=llm_model)

        # Execute LLM call
        try:
            llm_config = LLMRequestConfig(
                max_tokens=config.get("max_tokens", 6000),
                temperature=config.get("temperature", 0.5),
            )
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an SEO content integration specialist.",
                config=llm_config,
            )
        except Exception as e:
            raise ActivityError(
                f"LLM call failed: {e}",
                category=ErrorCategory.RETRYABLE,
            ) from e

        # === OutputParser統合 (JSON修復機能付き) ===
        parse_result = self.parser.parse_json(response.content)

        if not parse_result.success or not parse_result.data:
            # フォールバック禁止: エラーを投げる
            raise ActivityError(
                f"Failed to parse JSON response: format={parse_result.format_detected}",
                category=ErrorCategory.RETRYABLE,
                details={
                    "raw": response.content[:500],
                    "format_detected": parse_result.format_detected,
                },
            )

        if parse_result.fixes_applied:
            activity.logger.info(f"JSON fixes applied: {parse_result.fixes_applied}")

        parsed = parse_result.data
        if not isinstance(parsed, dict):
            raise ActivityError(
                "Parsed response is not a dictionary",
                category=ErrorCategory.RETRYABLE,
            )

        integration_package = parsed.get("integration_package", "")
        outline_summary = parsed.get("outline_summary", "")
        section_count = parsed.get("section_count", 0)
        total_sources = parsed.get("total_sources", 0)

        # === QualityValidator統合: パッケージ完全性チェック ===
        quality = self._validate_package_quality(
            package=parsed,
            all_data=all_data,
        )

        if not quality.is_acceptable:
            activity.logger.warning(f"Package quality issues: {quality.issues}")

        # Build inputs_summary
        inputs_summary = {
            "has_keyword_analysis": bool(all_data.get("step0")),
            "has_query_analysis": bool(all_data.get("step3a")),
            "has_cooccurrence": bool(all_data.get("step3b")),
            "has_competitor_analysis": bool(all_data.get("step3c")),
            "has_strategic_outline": bool(all_data.get("step4")),
            "has_sources": len(all_data.get("step5", {}).get("sources", [])) > 0,
            "has_enhanced_outline": bool(all_data.get("step6")),
        }

        # Calculate quality score
        quality_score = sum(1 for v in inputs_summary.values() if v) / len(inputs_summary)

        output = Step6_5Output(
            step=self.step_id,
            keyword=keyword,
            integration_package=integration_package,
            outline_summary=outline_summary,
            section_count=section_count,
            total_sources=total_sources,
            input_summaries=input_summaries,
            inputs_summary=inputs_summary,
            quality=PackageQuality(
                is_acceptable=quality.is_acceptable,
                issues=quality.issues,
                warnings=quality.warnings,
                scores=quality.scores,
            ),
            quality_score=quality_score,
            handoff_notes=quality.warnings,
            model=response.model,
            usage={
                "input_tokens": response.token_usage.input,
                "output_tokens": response.token_usage.output,
            },
        )

        return output.model_dump()

    async def _load_all_step_data(self, ctx: ExecutionContext) -> dict[str, Any]:
        """Load all step data from storage."""
        step0_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step0") or {}
        step3a_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step3a") or {}
        step3b_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step3b") or {}
        step3c_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step3c") or {}
        step3_5_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step3_5") or {}
        step4_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step4") or {}
        step5_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step5") or {}
        step6_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step6") or {}

        return {
            "step0": step0_data,
            "step3a": step3a_data,
            "step3b": step3b_data,
            "step3c": step3c_data,
            "step3_5": step3_5_data,
            "step4": step4_data,
            "step5": step5_data,
            "step6": step6_data,
        }

    def _prepare_integration_input(self, all_data: dict[str, Any], keyword: str) -> dict[str, Any]:
        """Prepare integration input for prompt rendering."""
        return {
            "keyword": keyword,
            "keyword_analysis": all_data.get("step0", {}).get("analysis", ""),
            "query_analysis": all_data.get("step3a", {}).get("query_analysis", all_data.get("step3a", {}).get("analysis", "")),
            "cooccurrence_analysis": all_data.get("step3b", {}).get(
                "cooccurrence_analysis", all_data.get("step3b", {}).get("analysis", "")
            ),
            "competitor_analysis": all_data.get("step3c", {}).get("competitor_analysis", all_data.get("step3c", {}).get("analysis", "")),
            "human_touch_elements": self._extract_human_touch_elements(all_data.get("step3_5", {})),
            "strategic_outline": all_data.get("step4", {}).get("outline", ""),
            "sources": all_data.get("step5", {}).get("sources", []),
            "enhanced_outline": all_data.get("step6", {}).get("enhanced_outline", ""),
        }

    def _build_input_summaries(self, all_data: dict[str, Any]) -> list[InputSummary]:
        """Build input summaries for each step."""
        summaries = []

        step_configs = [
            ("step0", "keyword_analysis", ["analysis"]),
            ("step3a", "query_analysis", ["query_analysis", "analysis"]),
            ("step3b", "cooccurrence_analysis", ["cooccurrence_analysis", "analysis"]),
            ("step3c", "competitor_analysis", ["competitor_analysis", "analysis"]),
            ("step3_5", "human_touch_elements", ["emotional_analysis", "human_touch_patterns"]),
            ("step4", "strategic_outline", ["outline"]),
            ("step5", "sources", ["sources"]),
            ("step6", "enhanced_outline", ["enhanced_outline"]),
        ]

        for step_id, label, fields in step_configs:
            data = all_data.get(step_id, {})
            available = bool(data)

            # Determine data quality
            data_quality = "unknown"
            if available:
                has_content = any(data.get(f) for f in fields)
                data_quality = "good" if has_content else "poor"

            summaries.append(
                InputSummary(
                    step_id=step_id,
                    available=available,
                    key_points=[],
                    data_quality=data_quality,
                )
            )

        return summaries

    def _extract_human_touch_elements(self, step3_5_data: dict[str, Any]) -> str:
        """Extract human touch elements as a prompt-ready string.

        step3_5 outputs: emotional_analysis, human_touch_patterns, experience_episodes, emotional_hooks
        This method extracts and formats these into a single string for prompt rendering.
        """
        if not step3_5_data:
            return ""

        parts: list[str] = []

        # Extract emotional_analysis (dict with primary_emotion, pain_points, desires)
        emotional = step3_5_data.get("emotional_analysis")
        if isinstance(emotional, dict):
            if emotional.get("primary_emotion"):
                parts.append(f"主要感情: {emotional['primary_emotion']}")
            if emotional.get("pain_points"):
                pain = emotional["pain_points"]
                parts.append(f"ペインポイント: {', '.join(pain) if isinstance(pain, list) else pain}")
            if emotional.get("desires"):
                desires = emotional["desires"]
                parts.append(f"願望: {', '.join(desires) if isinstance(desires, list) else desires}")
        elif emotional:
            parts.append(f"感情分析: {emotional}")

        # Extract human_touch_patterns (list of {type, content, placement_suggestion})
        patterns = step3_5_data.get("human_touch_patterns", [])
        if patterns and isinstance(patterns, list):
            pattern_strs = []
            for p in patterns[:5]:
                if isinstance(p, dict) and p.get("content"):
                    pattern_strs.append(f"- {p.get('type', 'general')}: {p['content']}")
            if pattern_strs:
                parts.append("人間味パターン:\n" + "\n".join(pattern_strs))

        # Extract experience_episodes (list of {scenario, narrative, lesson})
        episodes = step3_5_data.get("experience_episodes", [])
        if episodes and isinstance(episodes, list):
            episode_strs = []
            for ep in episodes[:3]:
                if isinstance(ep, dict) and ep.get("narrative"):
                    episode_strs.append(f"- {ep.get('scenario', '')}: {ep['narrative']}")
            if episode_strs:
                parts.append("体験エピソード:\n" + "\n".join(episode_strs))

        # Extract emotional_hooks (list of strings)
        hooks = step3_5_data.get("emotional_hooks", [])
        if hooks and isinstance(hooks, list):
            hooks_str = ", ".join(hooks[:5]) if all(isinstance(h, str) for h in hooks[:5]) else str(hooks[:5])
            parts.append(f"感情フック: {hooks_str}")

        # Fallback to raw_output if structured fields are empty
        if not parts and step3_5_data.get("raw_output"):
            return str(step3_5_data["raw_output"])[:2000]

        return "\n\n".join(parts)

    def _validate_package_quality(self, package: dict[str, Any], all_data: dict[str, Any]) -> QualityResult:
        """Validate integration package quality."""
        issues: list[str] = []
        warnings: list[str] = []
        scores: dict[str, float] = {}

        # Check: integration_package is required
        if not package.get("integration_package"):
            issues.append("integration_package_missing")

        # Check: outline_summary is required
        if not package.get("outline_summary"):
            issues.append("outline_summary_missing")

        # Check: section_count should be reasonable
        section_count = package.get("section_count", 0)
        scores["section_count"] = float(section_count)
        if section_count < 3:
            warnings.append(f"section_count_low: {section_count} < 3")

        # Check: sources should be integrated if available
        sources_available = len(all_data.get("step5", {}).get("sources", [])) > 0
        total_sources = package.get("total_sources", 0)
        scores["total_sources"] = float(total_sources)

        if sources_available and total_sources == 0:
            warnings.append("sources_not_integrated")

        return QualityResult(
            is_acceptable=len(issues) == 0,
            issues=issues,
            warnings=warnings,
            scores=scores,
        )


@activity.defn(name="step6_5_integration_package")
async def step6_5_integration_package(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 6.5."""
    step = Step65IntegrationPackage()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
