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
from apps.worker.helpers.model_config import get_step_llm_client, get_step_model_config
from apps.api.llm.schemas import LLMRequestConfig
from apps.api.prompts.loader import PromptPackLoader
from apps.worker.activities.schemas.step4 import (
    BehavioralEconomicsConfig,
    CTAPlacements,
    CTAPosition,
    KGIConfig,
    LLMOConfig,
    NeuroscienceConfig,
    OutlineMetrics,
    OutlineQuality,
    PhaseSection,
    SectionFourPillars,
    Step4Output,
    ThreePhaseStructure,
    TitleMetadata,
    WordCountTracking,
)
from apps.worker.helpers import (
    CTA_POSITION_EARLY,
    CTA_POSITION_FINAL_OFFSET,
    CTA_POSITION_MID,
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
from apps.worker.helpers.truncation_limits import (
    MAX_EPISODES,
    MAX_HOOKS,
    MAX_PATTERNS,
    PROMPT_ANALYSIS_LIMIT,
    PROMPT_EXCERPT_MEDIUM,
    PROMPT_RAW_OUTPUT_LIMIT,
)

from apps.api.llm.exceptions import LLMRateLimitError, LLMTimeoutError

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
        step3_5_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step3_5") or {}
        enable_step3_5 = config.get("enable_step3_5", True)

        # === InputValidator統合 ===
        # step3_5が有効な場合はemotional_analysisを必須にする（step3_5の実際の出力フィールド）
        required_fields = [
            "step3a.query_analysis",  # 検索意図・ペルソナは必須
            "step3b.cooccurrence_analysis",  # 共起キーワードは必須
        ]
        if enable_step3_5:
            required_fields.append("step3_5.emotional_analysis")

        recommended_fields = [
            "step0.analysis",  # キーワード分析
            "step3c.competitor_analysis",  # 競合分析は推奨
        ]

        validation = self.input_validator.validate(
            data={
                "step0": step0_data,
                "step3a": step3a_data,
                "step3b": step3b_data,
                "step3c": step3c_data,
                "step3_5": step3_5_data,
            },
            required=required_fields,
            recommended=recommended_fields,
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
        human_touch_elements = self._extract_human_touch_elements(step3_5_data)
        analysis_summary = self._build_analysis_summary(
            step0_data=step0_data,
            step3a_data=step3a_data,
            step3b_data=step3b_data,
            step3c_data=step3c_data,
        )
        input_digest = self.checkpoint.compute_digest(
            {
                "keyword": keyword,
                "step3a": step3a_data.get("query_analysis", ""),
                "step3b": step3b_data.get("cooccurrence_analysis", ""),
                "step3c": step3c_data.get("competitor_analysis", ""),
                "step3_5": human_touch_elements,
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
                human_touch=human_touch_elements,
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
                analysis_summary=analysis_summary,
                query_analysis=step3a_data.get("query_analysis", ""),
                cooccurrence_analysis=step3b_data.get("cooccurrence_analysis", ""),
                competitor_analysis=step3c_data.get("competitor_analysis", ""),
                human_touch_elements=human_touch_elements,
            )
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client - uses 3-tier priority: UI per-step > step defaults > global config
        llm_provider, llm_model = get_step_model_config(self.step_id, config)
        llm = await get_step_llm_client(self.step_id, config, tenant_id=ctx.tenant_id)

        llm_config = LLMRequestConfig(
            max_tokens=config.get("max_tokens", 8000),
            temperature=config.get("temperature", 0.6),
        )

        # === QualityRetryLoop統合 ===
        # キーワード検証を追加
        keyword_validator = KeywordValidator(min_density=0.0, max_density=5.0)

        async def llm_call(prompt_text: str) -> str:
            try:
                response = await llm.generate(
                    messages=[{"role": "user", "content": prompt_text}],
                    system_prompt="You are an SEO content strategist.",
                    config=llm_config,
                )
            except (LLMRateLimitError, LLMTimeoutError) as e:
                raise ActivityError(
                    f"LLM temporary failure: {e}",
                    category=ErrorCategory.RETRYABLE,
                    details={"llm_error": str(e)},
                ) from e
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
        token_usage = {
            "input": response.token_usage.input if response else 0,
            "output": response.token_usage.output if response else 0,
        }

        # V2モード検出: pack_idがv2_blog_systemの場合
        is_v2_mode = pack_id == "v2_blog_system" or config.get("v2_mode", False)

        # V2フィールドの構築
        title_metadata = None
        three_phase_structure = None
        four_pillars_per_section: list[SectionFourPillars] = []
        cta_placements = None
        word_count_tracking = None

        if is_v2_mode:
            # タイトルメタデータの構築
            article_title = ""
            if parse_result.success and parse_result.data:
                data = parse_result.data
                if isinstance(data, dict):
                    article_title = data.get("article_title", "")

            if article_title:
                title_metadata = self._build_title_metadata(article_title, keyword)

            # 3フェーズ構成の構築
            target_word_count = config.get("target_word_count", 5000)
            three_phase_structure = self._build_three_phase_structure(outline, target_word_count, md_metrics)

            # セクション別4本柱の構築
            four_pillars_per_section = self._build_four_pillars_per_section(outline)

            # CTA配置の構築
            cta_placements = self._build_cta_placements(target_word_count, outline)

            # 文字数管理の構築
            word_count_tracking = self._build_word_count_tracking(target_word_count, text_metrics.char_count)

        output = Step4Output(
            step=self.step_id,
            keyword=keyword,
            outline=outline,
            metrics=metrics,
            quality=quality,
            model=model_name,
            model_config_data={
                "platform": llm_provider,
                "model": llm_model or "",
            },
            token_usage=token_usage,
            # V2フィールド
            title_metadata=title_metadata,
            three_phase_structure=three_phase_structure,
            four_pillars_per_section=four_pillars_per_section,
            cta_placements=cta_placements,
            word_count_tracking=word_count_tracking,
        )

        return output.model_dump()

    def _integrate_analysis_data(
        self,
        keyword: str,
        query_analysis: str,
        cooccurrence: str,
        competitor: str,
        human_touch: str,
    ) -> dict[str, Any]:
        """Integrate analysis data from previous steps."""
        return {
            "keyword": keyword,
            "query_analysis_summary": query_analysis[:PROMPT_EXCERPT_MEDIUM] if query_analysis else "",
            "cooccurrence_summary": cooccurrence[:PROMPT_EXCERPT_MEDIUM] if cooccurrence else "",
            "competitor_summary": competitor[:PROMPT_EXCERPT_MEDIUM] if competitor else "",
            "human_touch_summary": human_touch[:PROMPT_EXCERPT_MEDIUM] if human_touch else "",
            "integrated": True,
        }

    def _extract_human_touch_elements(self, step3_5_data: dict[str, Any]) -> str:
        """Extract human touch elements as a prompt-ready string.

        step3_5 outputs: emotional_analysis, human_touch_patterns, experience_episodes, emotional_hooks
        This method extracts and formats these into a single string for step4 prompt.
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
                pain_str = ", ".join(pain) if isinstance(pain, list) else pain
                parts.append(f"ペインポイント: {pain_str}")
            if emotional.get("desires"):
                desires = emotional["desires"]
                desires_str = ", ".join(desires) if isinstance(desires, list) else desires
                parts.append(f"願望: {desires_str}")
        elif emotional:
            parts.append(f"感情分析: {emotional}")

        # Extract human_touch_patterns (list of {type, content, placement_suggestion})
        patterns = step3_5_data.get("human_touch_patterns", [])
        if patterns and isinstance(patterns, list):
            pattern_strs = []
            for p in patterns[:MAX_PATTERNS]:  # Limit to avoid too long prompt
                if isinstance(p, dict) and p.get("content"):
                    pattern_strs.append(f"- {p.get('type', 'general')}: {p['content']}")
            if pattern_strs:
                parts.append("人間味パターン:\n" + "\n".join(pattern_strs))

        # Extract experience_episodes (list of {scenario, narrative, lesson})
        episodes = step3_5_data.get("experience_episodes", [])
        if episodes and isinstance(episodes, list):
            episode_strs = []
            for ep in episodes[:MAX_EPISODES]:  # Limit to avoid too long prompt
                if isinstance(ep, dict) and ep.get("narrative"):
                    episode_strs.append(f"- {ep.get('scenario', '')}: {ep['narrative']}")
            if episode_strs:
                parts.append("体験エピソード:\n" + "\n".join(episode_strs))

        # Extract emotional_hooks (list of strings)
        hooks = step3_5_data.get("emotional_hooks", [])
        if hooks and isinstance(hooks, list):
            hooks_str = ", ".join(hooks[:MAX_HOOKS]) if all(isinstance(h, str) for h in hooks[:MAX_HOOKS]) else str(hooks[:MAX_HOOKS])
            parts.append(f"感情フック: {hooks_str}")

        # Fallback to raw_output if structured fields are empty
        if not parts and step3_5_data.get("raw_output"):
            return str(step3_5_data["raw_output"])[:PROMPT_RAW_OUTPUT_LIMIT]

        return "\n\n".join(parts)

    def _build_analysis_summary(
        self,
        step0_data: dict[str, Any],
        step3a_data: dict[str, Any],
        step3b_data: dict[str, Any],
        step3c_data: dict[str, Any],
    ) -> str:
        """Build a compact analysis summary for prompt context."""
        parts: list[str] = []
        if step0_data.get("analysis"):
            parts.append(f"キーワード分析: {str(step0_data.get('analysis'))[:PROMPT_ANALYSIS_LIMIT]}")
        if step3a_data.get("query_analysis"):
            parts.append(f"クエリ分析: {str(step3a_data.get('query_analysis'))[:PROMPT_ANALYSIS_LIMIT]}")
        if step3b_data.get("cooccurrence_analysis"):
            parts.append(f"共起語分析: {str(step3b_data.get('cooccurrence_analysis'))[:PROMPT_ANALYSIS_LIMIT]}")
        if step3c_data.get("competitor_analysis"):
            parts.append(f"競合分析: {str(step3c_data.get('competitor_analysis'))[:PROMPT_ANALYSIS_LIMIT]}")
        return "\n\n".join(parts)

    # ==========================================================================
    # blog.System Ver8.3 対応メソッド
    # ==========================================================================

    def _build_title_metadata(self, title: str, keyword: str) -> TitleMetadata:
        """タイトルメタデータを構築."""
        import re

        char_count = len(title)
        contains_number = bool(re.search(r"\d", title))
        contains_keyword = keyword.lower() in title.lower()
        # 括弧チェック: (), [], 【】, 「」, 『』
        bracket_pattern = r"[\(\)\[\]【】「」『』\(\)]"
        no_brackets = not bool(re.search(bracket_pattern, title))

        issues: list[str] = []
        if char_count < 28 or char_count > 36:
            issues.append(f"文字数が理想範囲外（{char_count}文字、理想: 28-36文字）")
        if not contains_number:
            issues.append("数字を含んでいません")
        if not contains_keyword:
            issues.append(f"キーワード「{keyword}」を含んでいません")
        if not no_brackets:
            issues.append("括弧を含んでいます（禁止）")

        validation_passed = len(issues) == 0

        return TitleMetadata(
            char_count=char_count,
            contains_number=contains_number,
            contains_keyword=contains_keyword,
            no_brackets=no_brackets,
            validation_passed=validation_passed,
            issues=issues,
        )

    def _build_three_phase_structure(self, outline: str, target_word_count: int, md_metrics: Any) -> ThreePhaseStructure:
        """3フェーズ構成を構築."""
        import re

        # H2セクションを抽出
        h2_pattern = r"^##\s+(.+)$"
        h2_sections = re.findall(h2_pattern, outline, re.MULTILINE)

        # フェーズ割り当て（簡易版: 最初の1/3をPhase1、中央をPhase2、最後をPhase3）
        total_sections = len(h2_sections)
        if total_sections == 0:
            return ThreePhaseStructure()

        phase1_end = max(1, total_sections // 6)  # 約15%
        phase3_start = total_sections - max(1, total_sections // 6)  # 約15%

        phase1_sections = h2_sections[:phase1_end]
        phase2_sections = h2_sections[phase1_end:phase3_start]
        phase3_sections = h2_sections[phase3_start:]

        # 文字数比率の計算
        phase1_ratio = 0.12 if phase1_sections else 0.0
        phase2_ratio = 0.70 if phase2_sections else 0.0
        phase3_ratio = 0.18 if phase3_sections else 0.0

        # バランスチェック
        balance_issues: list[str] = []
        if phase1_ratio < 0.10 or phase1_ratio > 0.20:
            balance_issues.append(f"Phase1比率が範囲外（{phase1_ratio:.0%}、理想: 10-20%）")
        if phase2_ratio < 0.60 or phase2_ratio > 0.80:
            balance_issues.append(f"Phase2比率が範囲外（{phase2_ratio:.0%}、理想: 60-80%）")
        if phase3_ratio < 0.10 or phase3_ratio > 0.20:
            balance_issues.append(f"Phase3比率が範囲外（{phase3_ratio:.0%}、理想: 10-20%）")

        return ThreePhaseStructure(
            phase1=PhaseSection(
                word_count_ratio=phase1_ratio,
                target_word_count=int(target_word_count * phase1_ratio),
                sections=phase1_sections,
            ),
            phase2=PhaseSection(
                word_count_ratio=phase2_ratio,
                target_word_count=int(target_word_count * phase2_ratio),
                sections=phase2_sections,
            ),
            phase3=PhaseSection(
                word_count_ratio=phase3_ratio,
                target_word_count=int(target_word_count * phase3_ratio),
                sections=phase3_sections,
            ),
            is_balanced=len(balance_issues) == 0,
            balance_issues=balance_issues,
        )

    def _build_four_pillars_per_section(self, outline: str) -> list[SectionFourPillars]:
        """セクション別4本柱を構築."""
        import re

        h2_pattern = r"^##\s+(.+)$"
        h2_sections = re.findall(h2_pattern, outline, re.MULTILINE)

        result: list[SectionFourPillars] = []
        for i, section_title in enumerate(h2_sections):
            # フェーズ決定（位置ベース）
            position_ratio = i / max(1, len(h2_sections) - 1) if len(h2_sections) > 1 else 0.5
            if position_ratio < 0.2:
                phase = "1"
                cognitive_load = "low"
            elif position_ratio > 0.8:
                phase = "3"
                cognitive_load = "medium"
            else:
                phase = "2"
                cognitive_load = "medium"

            # CTA配置決定
            if position_ratio < 0.15:
                cta_placement = "early"
            elif 0.5 < position_ratio < 0.7:
                cta_placement = "mid"
            elif position_ratio > 0.85:
                cta_placement = "final"
            else:
                cta_placement = "none"

            result.append(
                SectionFourPillars(
                    section_title=section_title,
                    neuroscience=NeuroscienceConfig(
                        cognitive_load=cognitive_load,
                        phase=phase,
                    ),
                    behavioral_economics=BehavioralEconomicsConfig(
                        principles_applied=["損失回避", "社会的証明"] if phase == "1" else ["権威性"],
                    ),
                    llmo=LLMOConfig(
                        token_target=500,
                        question_heading="?" in section_title or "とは" in section_title,
                    ),
                    kgi=KGIConfig(
                        cta_placement=cta_placement,
                    ),
                )
            )

        return result

    def _build_cta_placements(self, target_word_count: int, outline: str) -> CTAPlacements:
        """CTA配置を構築."""
        import re

        h2_pattern = r"^##\s+(.+)$"
        h2_sections = re.findall(h2_pattern, outline, re.MULTILINE)

        early_section = h2_sections[0] if len(h2_sections) > 0 else ""
        mid_index = len(h2_sections) // 2
        mid_section = h2_sections[mid_index] if len(h2_sections) > mid_index else ""
        final_section = h2_sections[-1] if len(h2_sections) > 0 else ""

        return CTAPlacements(
            early=CTAPosition(position=CTA_POSITION_EARLY, section=early_section, cta_type="資料請求"),
            mid=CTAPosition(position=CTA_POSITION_MID, section=mid_section, cta_type="無料相談"),
            final=CTAPosition(
                position=max(0, target_word_count - CTA_POSITION_FINAL_OFFSET),
                section=final_section,
                cta_type="問い合わせ",
            ),
        )

    def _build_word_count_tracking(self, target: int, sections_total: int) -> WordCountTracking:
        """文字数管理を構築."""
        variance = sections_total - target
        variance_percentage = (variance / target * 100) if target > 0 else 0.0
        is_within_tolerance = abs(variance_percentage) <= 10.0

        return WordCountTracking(
            target=target,
            sections_total=sections_total,
            variance=variance,
            variance_percentage=variance_percentage,
            is_within_tolerance=is_within_tolerance,
        )


@activity.defn(name="step4_strategic_outline")
async def step4_strategic_outline(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 4."""
    step = Step4StrategicOutline()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
