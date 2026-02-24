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
from apps.api.llm.schemas import LLMRequestConfig
from apps.worker.helpers.model_config import get_step_llm_client, get_step_model_config
from apps.api.prompts.loader import PromptPackLoader
from apps.worker.activities.schemas.step6_5 import (
    ComprehensiveBlueprint,
    FourPillarsFinalCheck,
    InputSummary,
    PackageQuality,
    ReferenceData,
    SectionExecutionInstruction,
    Step6_5Output,
    VisualElementInstruction,
)
from apps.worker.helpers import (
    CheckpointManager,
    InputValidator,
    OutputParser,
    QualityResult,
)

from apps.api.llm.exceptions import LLMRateLimitError, LLMTimeoutError
from apps.worker.helpers.truncation_limits import (
    MAX_DATA_PLACEMENTS,
    MAX_EPISODES,
    MAX_HOOKS,
    MAX_PATTERNS,
    MAX_SOURCES_IN_PROMPT,
    PROMPT_OUTLINE_LIMIT,
    PROMPT_RAW_OUTPUT_LIMIT,
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

        # Get LLM client (Claude Opus for step6.5 via step defaults)
        llm = await get_step_llm_client(self.step_id, config, tenant_id=ctx.tenant_id)
        llm_provider, llm_model = get_step_model_config(self.step_id, config)

        # Execute LLM call
        try:
            llm_config = LLMRequestConfig(
                max_tokens=config.get("max_tokens", 8000),
                temperature=config.get("temperature", 0.5),
            )
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an SEO content integration specialist.",
                config=llm_config,
            )
        except (LLMRateLimitError, LLMTimeoutError) as e:
            raise ActivityError(
                f"LLM temporary failure: {e}",
                category=ErrorCategory.RETRYABLE,
                details={"llm_error": str(e)},
            ) from e
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

        # V2モード検出: pack_idがv2_blog_systemの場合
        is_v2_mode = pack_id == "v2_blog_system" or config.get("v2_mode", False)

        # V2フィールドの構築
        comprehensive_blueprint = None
        section_execution_instructions: list[SectionExecutionInstruction] = []
        visual_element_instructions: list[VisualElementInstruction] = []
        four_pillars_final_check = None

        if is_v2_mode:
            # 包括的構成案の構築
            comprehensive_blueprint = self._build_comprehensive_blueprint(all_data, integration_input)

            # セクション別執筆指示の構築
            section_execution_instructions = self._build_section_execution_instructions(all_data, integration_input)

            # 視覚要素配置指示の構築
            visual_element_instructions = self._build_visual_element_instructions(all_data)

            # 4本柱最終チェックの構築
            four_pillars_final_check = self._check_four_pillars_compliance(all_data)

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
            model_config_data={
                "platform": llm_provider,
                "model": llm_model or "",
            },
            token_usage={
                "input": response.token_usage.input,
                "output": response.token_usage.output,
            },
            # V2フィールド
            comprehensive_blueprint=comprehensive_blueprint,
            section_execution_instructions=section_execution_instructions,
            visual_element_instructions=visual_element_instructions,
            four_pillars_final_check=four_pillars_final_check,
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
            for p in patterns[:MAX_PATTERNS]:
                if isinstance(p, dict) and p.get("content"):
                    pattern_strs.append(f"- {p.get('type', 'general')}: {p['content']}")
            if pattern_strs:
                parts.append("人間味パターン:\n" + "\n".join(pattern_strs))

        # Extract experience_episodes (list of {scenario, narrative, lesson})
        episodes = step3_5_data.get("experience_episodes", [])
        if episodes and isinstance(episodes, list):
            episode_strs = []
            for ep in episodes[:MAX_EPISODES]:
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

    # ==========================================================================
    # blog.System Ver8.3 対応メソッド
    # ==========================================================================

    def _build_comprehensive_blueprint(self, all_data: dict[str, Any], integration_input: dict[str, Any]) -> ComprehensiveBlueprint:
        """包括的構成案を構築."""
        # パート1: 構成案概要
        outline = integration_input.get("enhanced_outline", "")
        part1_outline = f"# 構成案概要\n\n{outline[:PROMPT_OUTLINE_LIMIT]}" if outline else ""

        # パート2: 参照データ集
        keywords: list[str] = []
        sources: list[str] = []
        human_touch_elements: list[str] = []
        cta_placements: list[str] = []

        # キーワード収集
        step3b_data = all_data.get("step3b", {})
        cooccurrence = step3b_data.get("cooccurrence_analysis", "")
        if cooccurrence:
            # 共起語から主要キーワードを抽出（簡易版）
            keywords = [kw.strip() for kw in cooccurrence.split(",")[:MAX_SOURCES_IN_PROMPT] if kw.strip()]

        # ソース収集
        step5_data = all_data.get("step5", {})
        raw_sources = step5_data.get("sources", [])
        if isinstance(raw_sources, list):
            for src in raw_sources[:MAX_SOURCES_IN_PROMPT]:
                if isinstance(src, dict):
                    sources.append(src.get("title", src.get("url", "")))
                elif isinstance(src, str):
                    sources.append(src)

        # 人間味要素収集
        step3_5_data = all_data.get("step3_5", {})
        patterns = step3_5_data.get("human_touch_patterns", [])
        if isinstance(patterns, list):
            for p in patterns[:MAX_PATTERNS]:
                if isinstance(p, dict) and p.get("content"):
                    human_touch_elements.append(p["content"])

        # CTA配置収集
        step4_data = all_data.get("step4", {})
        cta_data = step4_data.get("cta_placements", {})
        if isinstance(cta_data, dict):
            for pos in ["early", "mid", "final"]:
                if cta_data.get(pos):
                    cta_placements.append(f"{pos}: {cta_data[pos].get('section', '')}")

        return ComprehensiveBlueprint(
            part1_outline=part1_outline,
            part2_reference_data=ReferenceData(
                keywords=keywords,
                sources=sources,
                human_touch_elements=human_touch_elements,
                cta_placements=cta_placements,
            ),
        )

    def _build_section_execution_instructions(
        self, all_data: dict[str, Any], integration_input: dict[str, Any]
    ) -> list[SectionExecutionInstruction]:
        """セクション別執筆指示を構築."""
        import re

        instructions: list[SectionExecutionInstruction] = []

        # アウトラインからH2セクションを抽出
        outline = integration_input.get("enhanced_outline", "")
        h2_pattern = r"^##\s+(.+)$"
        h2_sections = re.findall(h2_pattern, outline, re.MULTILINE)

        # キーワード収集
        step3b_data = all_data.get("step3b", {})
        cooccurrence = step3b_data.get("cooccurrence_analysis", "")
        all_keywords = [kw.strip() for kw in cooccurrence.split(",")[:MAX_DATA_PLACEMENTS] if kw.strip()]

        # ソース収集
        step5_data = all_data.get("step5", {})
        raw_sources = step5_data.get("sources", [])
        all_sources: list[str] = []
        for src in raw_sources[:MAX_SOURCES_IN_PROMPT]:
            if isinstance(src, dict):
                all_sources.append(src.get("title", src.get("url", "")))
            elif isinstance(src, str):
                all_sources.append(src)

        # 人間味要素収集
        step3_5_data = all_data.get("step3_5", {})
        patterns = step3_5_data.get("human_touch_patterns", [])
        all_human_touch: list[str] = []
        for p in patterns[:MAX_SOURCES_IN_PROMPT]:
            if isinstance(p, dict) and p.get("content"):
                all_human_touch.append(p["content"])

        # 目標文字数計算（総文字数をセクション数で分割）
        target_word_count = all_data.get("step0", {}).get("target_word_count", 5000)
        words_per_section = target_word_count // max(1, len(h2_sections))

        for i, section_title in enumerate(h2_sections):
            # キーワード割り当て（ラウンドロビン）
            section_keywords = all_keywords[i * 2 : (i + 1) * 2] if all_keywords else []

            # ソース割り当て
            section_sources = all_sources[i : i + 1] if all_sources else []

            # 人間味要素割り当て
            section_human_touch = all_human_touch[i : i + 1] if all_human_touch else []

            # 論理展開（PREP法ベース）
            logic_flow = (
                f"Point: {section_title}の要点を明確に述べる\n"
                f"Reason: その理由・根拠を説明\n"
                f"Example: 具体例やデータで裏付け\n"
                f"Point: 結論として再度要点を強調"
            )

            instructions.append(
                SectionExecutionInstruction(
                    section_title=section_title,
                    logic_flow=logic_flow,
                    key_points=[f"{section_title}の重要ポイント"],
                    sources_to_cite=section_sources,
                    keywords_to_include=section_keywords,
                    human_touch_to_apply=section_human_touch,
                    word_count_target=words_per_section,
                )
            )

        return instructions

    def _build_visual_element_instructions(self, all_data: dict[str, Any]) -> list[VisualElementInstruction]:
        """視覚要素配置指示を構築."""
        import re

        instructions: list[VisualElementInstruction] = []

        # アウトラインからH2セクションを抽出
        step6_data = all_data.get("step6", {})
        outline = step6_data.get("enhanced_outline", "")
        h2_pattern = r"^##\s+(.+)$"
        h2_sections = re.findall(h2_pattern, outline, re.MULTILINE)

        # 視覚要素タイプの決定ロジック
        for i, section_title in enumerate(h2_sections):
            # 比較・対比を含むセクションには表
            if any(word in section_title for word in ["比較", "違い", "選び方", "メリット"]):
                instructions.append(
                    VisualElementInstruction(
                        element_type="table",
                        placement_section=section_title,
                        content_description=f"{section_title}の比較表",
                        purpose="情報を視覚的に整理し、読者の理解を促進",
                    )
                )

            # 数値・データを含むセクションにはグラフ
            elif any(word in section_title for word in ["効果", "結果", "統計", "推移"]):
                instructions.append(
                    VisualElementInstruction(
                        element_type="chart",
                        placement_section=section_title,
                        content_description=f"{section_title}のデータ可視化",
                        purpose="数値データを視覚的に表現し、説得力を向上",
                    )
                )

            # 手順・フローを含むセクションには図解
            elif any(word in section_title for word in ["手順", "ステップ", "方法", "流れ"]):
                instructions.append(
                    VisualElementInstruction(
                        element_type="diagram",
                        placement_section=section_title,
                        content_description=f"{section_title}のフロー図",
                        purpose="プロセスを視覚化し、手順の理解を容易に",
                    )
                )

        return instructions

    def _check_four_pillars_compliance(self, all_data: dict[str, Any]) -> FourPillarsFinalCheck:
        """4本柱の適合チェックを実行."""
        issues: list[str] = []
        recommendations: list[str] = []

        # step4から4本柱データを取得
        step4_data = all_data.get("step4", {})
        four_pillars = step4_data.get("four_pillars_per_section", [])

        if not four_pillars:
            # 4本柱データがない場合は基本的なカバー率を返す
            return FourPillarsFinalCheck(
                all_sections_compliant=False,
                neuroscience_coverage=0.0,
                behavioral_economics_coverage=0.0,
                llmo_coverage=0.0,
                kgi_coverage=0.0,
                issues=["four_pillars_data_not_available"],
                recommendations=["step4でV2モードを有効にしてください"],
            )

        # 各柱のカバー率を計算
        total_sections = len(four_pillars)
        neuroscience_count = 0
        behavioral_count = 0
        llmo_count = 0
        kgi_count = 0

        for pillar in four_pillars:
            if isinstance(pillar, dict):
                ns = pillar.get("neuroscience", {})
                if ns.get("cognitive_load") or ns.get("attention_hooks"):
                    neuroscience_count += 1

                be = pillar.get("behavioral_economics", {})
                if be.get("principles_applied"):
                    behavioral_count += 1

                llmo = pillar.get("llmo", {})
                if llmo.get("token_target") or llmo.get("question_heading"):
                    llmo_count += 1

                kgi = pillar.get("kgi", {})
                if kgi.get("cta_placement") and kgi.get("cta_placement") != "none":
                    kgi_count += 1

        neuroscience_coverage = neuroscience_count / max(1, total_sections)
        behavioral_coverage = behavioral_count / max(1, total_sections)
        llmo_coverage = llmo_count / max(1, total_sections)
        kgi_coverage = kgi_count / max(1, total_sections)

        # 適合チェック
        FOUR_PILLARS_COVERAGE_THRESHOLD = 0.8
        KGI_COVERAGE_THRESHOLD = 0.3

        if neuroscience_coverage < FOUR_PILLARS_COVERAGE_THRESHOLD:
            issues.append(f"神経科学カバー率不足: {neuroscience_coverage:.0%}")
            recommendations.append("各セクションに認知負荷設定を追加")

        if behavioral_coverage < FOUR_PILLARS_COVERAGE_THRESHOLD:
            issues.append(f"行動経済学カバー率不足: {behavioral_coverage:.0%}")
            recommendations.append("各セクションに行動経済学原則を追加")

        if llmo_coverage < FOUR_PILLARS_COVERAGE_THRESHOLD:
            issues.append(f"LLMOカバー率不足: {llmo_coverage:.0%}")
            recommendations.append("各セクションにLLMO設定を追加")

        # KGIは全セクションに必要ではない（CTA配置は特定位置のみ）
        if kgi_coverage < KGI_COVERAGE_THRESHOLD:
            issues.append(f"KGI/CTAカバー率低: {kgi_coverage:.0%}")
            recommendations.append("Early/Mid/FinalのCTA配置を確認")

        all_compliant = len(issues) == 0

        return FourPillarsFinalCheck(
            all_sections_compliant=all_compliant,
            neuroscience_coverage=neuroscience_coverage,
            behavioral_economics_coverage=behavioral_coverage,
            llmo_coverage=llmo_coverage,
            kgi_coverage=kgi_coverage,
            issues=issues,
            recommendations=recommendations,
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
