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
from apps.worker.helpers.model_config import get_step_model_config
from apps.api.prompts.loader import PromptPackLoader
from apps.worker.activities.schemas.step7a import (
    BehavioralEconomicsImplementation,
    CTAImplementation,
    CTAPosition,
    DraftQuality,
    DraftQualityMetrics,
    FourPillarsImplementation,
    GenerationStats,
    KGIImplementation,
    LLMOImplementation,
    NeuroscienceImplementation,
    SectionWordCount,
    SplitGeneration,
    Step7aOutput,
    WordCountTracking,
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
        step3_5_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step3_5") or {}
        step5_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step5") or {}
        step0_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step0") or {}
        enable_step3_5 = config.get("enable_step3_5", True)

        # Load CTA specification from step0 for URL injection
        cta_spec = step0_data.get("cta_specification", {})
        cta_placements = cta_spec.get("placements", {})
        cta_url = ""
        cta_text = ""
        for phase in ("final", "early", "mid"):
            placement = cta_placements.get(phase, {})
            if isinstance(placement, dict) and placement.get("url"):
                cta_url = placement["url"]
                cta_text = placement.get("text", "")
                break
        if cta_url:
            cta_info = (
                f"\n**重要: 以下のCTA情報を必ず使用してください:**\n"
                f"CTA URL: {cta_url}\n"
                f"CTAテキスト: {cta_text}\n"
                f"上記URLとテキストをCTAリンクのhref属性に必ず設定すること。"
                f"「[リンク先URL]」等のプレースホルダーは禁止。"
            )
        else:
            cta_info = ""

        # Extract and format primary sources for citation embedding
        # Use verified sources first, fallback to invalid_sources if empty
        step5_sources = step5_data.get("sources", [])
        if not step5_sources:
            step5_sources = step5_data.get("invalid_sources", [])
        primary_sources = self._format_primary_sources(step5_sources)

        # === InputValidator統合 ===
        validation = self.input_validator.validate(
            data={"step6_5": step6_5_data, "step3_5": step3_5_data},
            required=["step6_5.integration_package"],
            recommended=["step3_5.emotional_analysis"] if enable_step3_5 else [],
            min_lengths={"step6_5.integration_package": 500},
        )

        if not validation.is_valid:
            raise ActivityError(
                f"Critical inputs missing: {validation.missing_required}",
                category=ErrorCategory.NON_RETRYABLE,
                details={"missing": validation.missing_required},
            )

        integration_package = step6_5_data.get("integration_package", "")
        human_touch_elements = self._extract_human_touch_elements(step3_5_data)

        # モデル設定を取得（Claude Opus for step7a via step defaults）
        llm_provider, llm_model = get_step_model_config(self.step_id, config)

        # === CheckpointManager統合: 部分生成のチェックポイント ===
        draft_checkpoint = await self.checkpoint.load(ctx.tenant_id, ctx.run_id, self.step_id, "draft_progress")

        checkpoint_resumed = False
        continuation_used = False

        if draft_checkpoint and draft_checkpoint.get("needs_continuation"):
            current_draft = draft_checkpoint.get("draft", "")
            checkpoint_resumed = True
            activity.logger.info(f"Resuming from checkpoint: {len(current_draft)} chars done")

            # 続きを生成
            continuation = await self._continue_generation(
                config,
                current_draft,
                integration_package,
                human_touch_elements=human_touch_elements,
            )
            current_draft = current_draft + "\n\n" + continuation
            continuation_used = True
        else:
            # 最初から生成
            current_draft = await self._generate_draft(
                config,
                keyword,
                integration_package,
                prompt_pack,
                human_touch_elements=human_touch_elements,
                primary_sources=primary_sources,
                cta_info=cta_info,
            )

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
                raw_cta_positions = data.get("cta_positions", [])
                # Normalize cta_positions to list[str] (LLM may return list[dict])
                cta_positions = []
                for pos in raw_cta_positions:
                    if isinstance(pos, str):
                        cta_positions.append(pos)
                    elif isinstance(pos, dict):
                        # Extract position string from dict (e.g., {"type": "early", "position": "..."})
                        pos_str = pos.get("type", "") or pos.get("position", "") or pos.get("name", "")
                        if pos_str:
                            cta_positions.append(str(pos_str))
                        else:
                            # Fallback: join all string values
                            cta_positions.append(" ".join(str(v) for v in pos.values() if isinstance(v, str)))

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

            continuation = await self._continue_generation(
                config,
                draft_content,
                integration_package,
                human_touch_elements=human_touch_elements,
            )
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
        token_usage = {
            "input": response.token_usage.input if response else 0,
            "output": response.token_usage.output if response else 0,
        }

        # === blog.System Ver8.3 Extensions ===
        # Get target word count from config (default 5000)
        target_word_count = config.get("target_word_count", 5000)

        # Get parsed data for extraction
        parsed_data = parse_result.data if parse_result.success else {}
        if not isinstance(parsed_data, dict):
            parsed_data = {}

        # Extract section titles for split generation tracking
        section_titles = re.findall(r"^##\s+(.+)$", draft_content, re.MULTILINE)
        section_titles = [t.strip() for t in section_titles]

        # Extract blog.System Ver8.3 fields
        section_word_counts = self._extract_section_word_counts(parsed_data, draft_content, target_word_count)
        four_pillars_impl = self._extract_four_pillars_implementation(parsed_data)
        cta_impl = self._extract_cta_implementation(parsed_data, cta_positions, md_metrics.h2_count or section_count)
        word_count_tracking = self._extract_word_count_tracking(parsed_data, target_word_count, text_metrics.word_count)
        split_gen = self._extract_split_generation(parsed_data, continuation_used, section_titles)

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
            model_config_data={
                "platform": llm_provider,
                "model": llm_model or "",
            },
            token_usage=token_usage,
            # blog.System Ver8.3 extensions
            section_word_counts=[SectionWordCount(**swc) for swc in section_word_counts],
            four_pillars_implementation=[
                FourPillarsImplementation(
                    section_title=fp["section_title"],
                    neuroscience=NeuroscienceImplementation(**fp["neuroscience"]),
                    behavioral_economics=BehavioralEconomicsImplementation(**fp["behavioral_economics"]),
                    llmo=LLMOImplementation(**fp["llmo"]),
                    kgi=KGIImplementation(**fp["kgi"]),
                )
                for fp in four_pillars_impl
            ],
            cta_implementation=CTAImplementation(
                early=CTAPosition(**cta_impl["early"]),
                mid=CTAPosition(**cta_impl["mid"]),
                final=CTAPosition(**cta_impl["final"]),
            ),
            word_count_tracking=WordCountTracking(**word_count_tracking),
            split_generation=SplitGeneration(**split_gen),
        )

        return output.model_dump()

    def _format_primary_sources(self, sources: list[dict[str, Any]]) -> str:
        """Format primary sources for citation embedding in article.

        Converts step5's sources list into a prompt-ready format for LLM
        to embed citations with URLs in the generated draft.
        """
        if not sources:
            return ""

        formatted_sources: list[str] = []
        for i, src in enumerate(sources[:15], start=1):  # Limit to 15 most relevant
            url = src.get("url", "")
            title = src.get("title", "")
            source_type = src.get("source_type", "other")
            excerpt = src.get("excerpt", "")[:200]
            phase = src.get("phase_alignment", "")

            # Format each source with citation ID
            source_entry = f"[{i}] {title}"
            if source_type != "other":
                source_entry += f" ({source_type})"
            source_entry += f"\n    URL: {url}"
            if excerpt:
                source_entry += f"\n    要約: {excerpt}"
            if phase:
                source_entry += f"\n    フェーズ: {phase}"

            # Add data points if available
            data_points = src.get("data_points", [])
            if data_points:
                dp_strs = []
                for dp in data_points[:3]:
                    metric = dp.get("metric", "")
                    value = dp.get("value", "")
                    if metric and value:
                        dp_strs.append(f"{metric}: {value}")
                if dp_strs:
                    source_entry += f"\n    データ: {', '.join(dp_strs)}"

            formatted_sources.append(source_entry)

        if not formatted_sources:
            return ""

        return "## 引用可能な一次資料\n以下の出典を記事内で脚注形式で引用してください。\n\n" + "\n\n".join(formatted_sources)

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

    def _extract_section_word_counts(
        self,
        parsed_data: dict[str, Any],
        draft_content: str,
        target_word_count: int,
    ) -> list[dict[str, Any]]:
        """Extract section-level word count tracking from parsed data or draft.

        Calculates target, actual, variance, and tolerance for each section.
        Default target per section is total target / section count.
        """
        section_word_counts: list[dict[str, Any]] = []

        # Try to extract from parsed data first
        if parsed_data and parsed_data.get("section_word_counts"):
            for item in parsed_data["section_word_counts"]:
                if isinstance(item, dict):
                    section_word_counts.append(
                        {
                            "section_title": item.get("section_title", ""),
                            "target": item.get("target", 0),
                            "actual": item.get("actual", 0),
                            "variance": item.get("variance", 0),
                            "is_within_tolerance": item.get("is_within_tolerance", True),
                        }
                    )
            return section_word_counts

        # Extract from draft content using regex
        sections = re.findall(r"^##\s+(.+)$", draft_content, re.MULTILINE)
        if not sections:
            return section_word_counts

        # Split content by H2 headers
        section_texts = re.split(r"^##\s+.+$", draft_content, flags=re.MULTILINE)
        section_texts = [t.strip() for t in section_texts[1:] if t.strip()]  # Skip before first H2

        # Calculate target per section (equal distribution)
        per_section_target = target_word_count // max(1, len(sections))

        for i, title in enumerate(sections):
            content = section_texts[i] if i < len(section_texts) else ""
            actual = len(content.split())
            variance = actual - per_section_target
            # Within tolerance if within ±20%
            tolerance = per_section_target * 0.2
            is_within = abs(variance) <= tolerance

            section_word_counts.append(
                {
                    "section_title": title.strip(),
                    "target": per_section_target,
                    "actual": actual,
                    "variance": variance,
                    "is_within_tolerance": is_within,
                }
            )

        return section_word_counts

    def _extract_four_pillars_implementation(
        self,
        parsed_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extract four pillars implementation tracking from parsed data.

        Each section tracks: 神経科学, 行動経済学, LLMO, KGI implementation.
        """
        implementations: list[dict[str, Any]] = []

        if not parsed_data:
            return implementations

        raw_impl = parsed_data.get("four_pillars_implementation", [])
        if not isinstance(raw_impl, list):
            return implementations

        for item in raw_impl:
            if not isinstance(item, dict):
                continue

            # Extract neuroscience
            neuro_data = item.get("neuroscience", {})
            if not isinstance(neuro_data, dict):
                neuro_data = {}

            # Extract behavioral economics
            be_data = item.get("behavioral_economics", {})
            if not isinstance(be_data, dict):
                be_data = {}
            principles = be_data.get("principles_used", [])
            if not isinstance(principles, list):
                principles = []

            # Extract LLMO
            llmo_data = item.get("llmo", {})
            if not isinstance(llmo_data, dict):
                llmo_data = {}

            # Extract KGI
            kgi_data = item.get("kgi", {})
            if not isinstance(kgi_data, dict):
                kgi_data = {}

            implementations.append(
                {
                    "section_title": item.get("section_title", ""),
                    "neuroscience": {
                        "applied": bool(neuro_data.get("applied", False)),
                        "details": str(neuro_data.get("details", "")),
                    },
                    "behavioral_economics": {
                        "principles_used": [str(p) for p in principles[:4]],
                    },
                    "llmo": {
                        "token_count": int(llmo_data.get("token_count", 0)),
                        "is_independent": bool(llmo_data.get("is_independent", False)),
                    },
                    "kgi": {
                        "cta_present": bool(kgi_data.get("cta_present", False)),
                        "cta_type": kgi_data.get("cta_type"),
                    },
                }
            )

        return implementations

    def _extract_cta_implementation(
        self,
        parsed_data: dict[str, Any],
        cta_positions: list[str],
        section_count: int,
    ) -> dict[str, Any]:
        """Extract CTA implementation tracking.

        Maps CTA positions to early/mid/final based on section count.
        """
        # Try to extract from parsed data
        if parsed_data and parsed_data.get("cta_implementation"):
            raw = parsed_data["cta_implementation"]
            if isinstance(raw, dict):
                early = raw.get("early", {})
                mid = raw.get("mid", {})
                final = raw.get("final", {})
                return {
                    "early": {
                        "position": int(early.get("position", 0)) if isinstance(early, dict) else 0,
                        "implemented": bool(early.get("implemented", False)) if isinstance(early, dict) else False,
                    },
                    "mid": {
                        "position": int(mid.get("position", 0)) if isinstance(mid, dict) else 0,
                        "implemented": bool(mid.get("implemented", False)) if isinstance(mid, dict) else False,
                    },
                    "final": {
                        "position": int(final.get("position", 0)) if isinstance(final, dict) else 0,
                        "implemented": bool(final.get("implemented", False)) if isinstance(final, dict) else False,
                    },
                }

        # Infer from cta_positions and section_count
        early_pos = 1 if section_count > 0 else 0
        mid_pos = section_count // 2 if section_count > 2 else 1
        final_pos = max(0, section_count - 1)

        # Normalize cta_positions to strings for checking
        def get_position_str(p: Any) -> str:
            if isinstance(p, str):
                return p.lower()
            if isinstance(p, dict):
                # Try common keys for position name/type
                for key in ["position", "name", "type", "location"]:
                    if key in p and isinstance(p[key], str):
                        return p[key].lower()
                # Fallback: join all string values
                return " ".join(str(v).lower() for v in p.values() if isinstance(v, str))
            return str(p).lower()

        position_strs = [get_position_str(p) for p in cta_positions]

        # Check which positions have CTAs
        early_impl = any("early" in ps or "導入" in ps for ps in position_strs)
        mid_impl = any("mid" in ps or "中盤" in ps for ps in position_strs)
        final_impl = any("final" in ps or "まとめ" in ps or "結論" in ps for ps in position_strs)

        return {
            "early": {"position": early_pos, "implemented": early_impl},
            "mid": {"position": mid_pos, "implemented": mid_impl},
            "final": {"position": final_pos, "implemented": final_impl},
        }

    def _extract_word_count_tracking(
        self,
        parsed_data: dict[str, Any],
        target_word_count: int,
        actual_word_count: int,
    ) -> dict[str, Any]:
        """Extract overall word count progress tracking."""
        # Try to extract from parsed data
        if parsed_data and parsed_data.get("word_count_tracking"):
            raw = parsed_data["word_count_tracking"]
            if isinstance(raw, dict):
                return {
                    "target": int(raw.get("target", target_word_count)),
                    "current": int(raw.get("current", actual_word_count)),
                    "remaining": int(raw.get("remaining", max(0, target_word_count - actual_word_count))),
                    "progress_percent": float(raw.get("progress_percent", 0.0)),
                }

        # Calculate from actual values
        remaining = max(0, target_word_count - actual_word_count)
        progress = (actual_word_count / target_word_count * 100) if target_word_count > 0 else 0.0
        progress = min(100.0, progress)  # Cap at 100%

        return {
            "target": target_word_count,
            "current": actual_word_count,
            "remaining": remaining,
            "progress_percent": round(progress, 1),
        }

    def _extract_split_generation(
        self,
        parsed_data: dict[str, Any],
        continuation_used: bool,
        section_titles: list[str],
    ) -> dict[str, Any]:
        """Extract split generation tracking."""
        # Try to extract from parsed data
        if parsed_data and parsed_data.get("split_generation"):
            raw = parsed_data["split_generation"]
            if isinstance(raw, dict):
                total = int(raw.get("total_parts", 1))
                current = int(raw.get("current_part", 1))
                completed = raw.get("completed_sections", [])
                if not isinstance(completed, list):
                    completed = []
                return {
                    "total_parts": max(1, min(5, total)),
                    "current_part": max(1, min(5, current)),
                    "completed_sections": [str(s) for s in completed],
                }

        # Default: single part unless continuation was used
        if continuation_used:
            return {
                "total_parts": 2,
                "current_part": 2,
                "completed_sections": section_titles,
            }

        return {
            "total_parts": 1,
            "current_part": 1,
            "completed_sections": section_titles,
        }

    async def _generate_draft(
        self,
        config: dict[str, Any],
        keyword: str,
        integration_package: str,
        prompt_pack: Any,
        human_touch_elements: str,
        primary_sources: str = "",
        cta_info: str = "",
    ) -> str:
        """Generate draft from scratch."""
        # Render prompt
        try:
            prompt_template = prompt_pack.get_prompt("step7a")
            prompt = prompt_template.render(
                keyword=keyword,
                integration_package=integration_package,
                human_touch_elements=human_touch_elements,
                primary_sources=primary_sources,
                cta_info=cta_info,
            )
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client - uses 3-tier priority: UI per-step > step defaults > global config
        llm_provider, llm_model = get_step_model_config(self.step_id, config)
        llm = get_llm_client(llm_provider, model=llm_model)

        try:
            llm_config = LLMRequestConfig(
                max_tokens=config.get("max_tokens", 24000),  # Extended from 16000 for 30,000+ char articles
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
        human_touch_elements: str,
    ) -> str:
        """Generate continuation of draft."""
        continuation_prompt = f"""
以下は記事ドラフトの途中です。この続きから完成させてください。

## 現在のドラフト（最後の500文字）
{current_draft[-500:]}

## 統合パッケージ（参照用）
{integration_package[:2000]}

## 人間味要素（参考）
{human_touch_elements[:2000] if human_touch_elements else ""}

## 指示
- 既存の内容と自然につながるように続きを書いてください
- 必ず「まとめ」または「結論」セクションで締めくくってください
- JSON形式ではなく、マークダウン形式で出力してください
"""

        # Get LLM client - uses 3-tier priority: UI per-step > step defaults > global config
        llm_provider, llm_model = get_step_model_config(self.step_id, config)
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
