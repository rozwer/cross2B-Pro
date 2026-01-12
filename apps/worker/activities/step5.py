"""Step 5: Primary Source Collection Activity.

Collects primary sources (academic papers, official documents, statistics)
to support article claims with credible evidence.
Uses Tools (Web search, PDF extraction) and Gemini.

Integrated helpers:
- InputValidator: Validates required inputs from previous steps
- OutputParser: Parses JSON responses from LLM (NO FALLBACK on parse failure)
- QualityValidator: Validates source collection quality
- CheckpointManager: Manages intermediate checkpoints for idempotency

IMPORTANT: フォールバック禁止 - パース失敗時はエラーを投げる
"""

import logging
from datetime import datetime
from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.llm.base import get_llm_client
from apps.api.llm.schemas import LLMRequestConfig
from apps.api.prompts.loader import PromptPackLoader
from apps.api.tools.registry import ToolRegistry
from apps.worker.activities.schemas.step5 import (
    CollectionStats,
    KnowledgeGap,
    PhaseData,
    PhaseSpecificData,
    PrimarySource,
    SectionSourceMapping,
    Step5Output,
)
from apps.worker.helpers import (
    CheckpointManager,
    InputValidator,
    OutputParser,
    QualityResult,
)

from .base import ActivityError, BaseActivity, load_step_data

logger = logging.getLogger(__name__)


class Step5PrimaryCollection(BaseActivity):
    """Activity for primary source collection."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.input_validator = InputValidator()
        self.parser = OutputParser()
        self.checkpoint = CheckpointManager(self.store)

    @property
    def step_id(self) -> str:
        return "step5"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute primary source collection.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with collected primary sources
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
        step4_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step4") or {}
        outline = step4_data.get("outline", "")
        sections = step4_data.get("sections", [])

        # Load step3c for knowledge gap discovery (optional)
        step3c_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step3c")

        # === InputValidator統合 ===
        validation = self.input_validator.validate(
            data={"step4": step4_data},
            required=["step4.outline"],
            recommended=[],
        )

        if not validation.is_valid:
            raise ActivityError(
                f"Input validation failed: {validation.missing_required}",
                category=ErrorCategory.NON_RETRYABLE,
                details={"missing": validation.missing_required},
            )

        # === CheckpointManager統合: クエリ生成のチェックポイント ===
        # Use full outline hash for proper cache invalidation when outline changes
        input_digest = self.checkpoint.compute_digest(
            {
                "keyword": keyword,
                "outline": outline,  # Full outline for accurate cache invalidation
            }
        )

        queries_checkpoint = await self.checkpoint.load(
            ctx.tenant_id,
            ctx.run_id,
            self.step_id,
            "queries_generated",
            input_digest=input_digest,
        )

        search_queries: list[str]
        if queries_checkpoint:
            search_queries = queries_checkpoint.get("queries", [])
            activity.logger.info(f"Loaded {len(search_queries)} queries from checkpoint")
        else:
            # Step 5.1: Generate search queries using LLM
            model_config = config.get("model_config", {})
            llm_provider = model_config.get("platform", config.get("llm_provider", "gemini"))
            llm_model = model_config.get("model", config.get("llm_model"))
            llm = get_llm_client(llm_provider, model=llm_model)

            try:
                query_prompt = prompt_pack.get_prompt("step5_queries")
                query_request = query_prompt.render(
                    keyword=keyword,
                    outline=outline,
                )
                llm_config = LLMRequestConfig(max_tokens=1000, temperature=0.5)
                query_response = await llm.generate(
                    messages=[{"role": "user", "content": query_request}],
                    system_prompt="Generate search queries for primary source collection.",
                    config=llm_config,
                )

                # === OutputParser統合 (フォールバック禁止) ===
                activity.logger.info(f"LLM response content: {query_response.content[:1000]}")
                parse_result = self.parser.parse_json(query_response.content)
                activity.logger.info(f"Parse result: success={parse_result.success}, format={parse_result.format_detected}")

                search_queries = []
                if parse_result.success and parse_result.data:
                    data = parse_result.data
                    if isinstance(data, dict):
                        search_queries = data.get("queries", [])
                    if parse_result.fixes_applied:
                        activity.logger.info(f"JSON fixes applied: {parse_result.fixes_applied}")
                else:
                    # Try parsing as newline-separated list
                    search_queries = self._parse_queries(query_response.content)

                if not search_queries:
                    # フォールバック禁止: エラーを投げる
                    raise ActivityError(
                        f"Failed to parse queries: format={parse_result.format_detected}",
                        category=ErrorCategory.RETRYABLE,
                        details={
                            "raw": query_response.content[:500],
                            "format_detected": parse_result.format_detected,
                        },
                    )

            except ActivityError:
                raise
            except Exception as e:
                # フォールバック禁止: エラーを投げる
                raise ActivityError(
                    f"Query generation failed: {e}",
                    category=ErrorCategory.RETRYABLE,
                    details={"error": str(e)},
                ) from e

            # Save queries to checkpoint
            await self.checkpoint.save(
                ctx.tenant_id,
                ctx.run_id,
                self.step_id,
                "queries_generated",
                {"queries": search_queries},
                input_digest=input_digest,
            )

        # === CheckpointManager統合: 部分収集のチェックポイント ===
        collection_checkpoint = await self.checkpoint.load(ctx.tenant_id, ctx.run_id, self.step_id, "collection_progress")

        completed_queries_set: set[str]
        collected_sources: list[dict[str, Any]]
        if collection_checkpoint:
            completed_queries_set = set(collection_checkpoint.get("completed_queries", []))
            collected_sources = collection_checkpoint.get("collected_sources", [])
            activity.logger.info(f"Resuming collection: {len(completed_queries_set)}/{len(search_queries)} queries completed")
        else:
            completed_queries_set = set()
            collected_sources = []

        # Step 5.2: Execute searches using primary_collector tool
        registry = ToolRegistry()
        primary_collector = registry.get("primary_collector")
        failed_queries: list[dict[str, Any]] = []

        if primary_collector:
            for query in search_queries[:5]:  # Limit to 5 queries
                if query in completed_queries_set:
                    continue

                try:
                    result = await primary_collector.execute(query=query)

                    if result.success:
                        # primary_collector returns {"query": str, "sources": list, "total": int}
                        sources = result.data.get("sources", []) if result.data else []
                        collected_sources.extend(sources)
                    else:
                        failed_queries.append(
                            {
                                "query": query,
                                "error": result.error_message or "Unknown error",
                            }
                        )
                except Exception as e:
                    failed_queries.append(
                        {
                            "query": query,
                            "error": str(e),
                        }
                    )

                completed_queries_set.add(query)

                # 各クエリ完了後にチェックポイント保存
                await self.checkpoint.save(
                    ctx.tenant_id,
                    ctx.run_id,
                    self.step_id,
                    "collection_progress",
                    {
                        "completed_queries": list(completed_queries_set),
                        "collected_sources": collected_sources,
                    },
                )
        else:
            # If tool not available, note it as a warning
            failed_queries.append(
                {
                    "query": "all",
                    "error": "primary_collector tool not available",
                }
            )

        # Step 5.3: Verify URLs
        url_verify = registry.get("url_verify")
        verified_sources: list[dict[str, Any]] = []
        invalid_sources: list[dict[str, Any]] = []

        if url_verify:
            for source in collected_sources:
                try:
                    verify_result = await url_verify.execute(url=source.get("url", ""))

                    data = verify_result.data or {}
                    if verify_result.success and data.get("status") == 200:
                        source["verified"] = True
                        verified_sources.append(source)
                    else:
                        source["verified"] = False
                        invalid_sources.append(source)
                except Exception as e:
                    activity.logger.warning(f"URL verification failed for {source.get('url', '')}: {e}")
                    source["verified"] = False
                    invalid_sources.append(source)
        else:
            # If no verification tool, mark all as unverified
            for source in collected_sources:
                source["verified"] = False
            verified_sources = collected_sources

        # === QualityValidator統合 ===
        quality = self._validate_collection_quality(
            sources=verified_sources,
            queries=search_queries,
            failed=failed_queries,
        )

        if not quality.is_acceptable:
            activity.logger.warning(f"Source collection quality issues: {quality.issues}")

        # Convert sources to PrimarySource models with blog.System extensions
        primary_sources: list[PrimarySource] = []
        for s in verified_sources:
            pub_date = s.get("publication_date")
            phase = self._classify_phase(s)
            freshness = self._calculate_freshness_score(pub_date)

            primary_sources.append(
                PrimarySource(
                    url=s.get("url", ""),
                    title=s.get("title", ""),
                    source_type=s.get("source_type", "other"),
                    excerpt=s.get("excerpt", "")[:500] if s.get("excerpt") else "",
                    credibility_score=s.get("credibility_score", 0.5),
                    verified=s.get("verified", False),
                    phase_alignment=phase,
                    freshness_score=freshness,
                    publication_date=pub_date,
                )
            )

        invalid_primary_sources = [
            PrimarySource(
                url=s.get("url", ""),
                title=s.get("title", ""),
                source_type=s.get("source_type", "other"),
                excerpt=s.get("excerpt", "")[:500] if s.get("excerpt") else "",
                credibility_score=s.get("credibility_score", 0.5),
                verified=False,
            )
            for s in invalid_sources
        ]

        # === blog.System Ver8.3 拡張 ===
        # 3フェーズ別データ集計
        phase_specific_data = self._build_phase_specific_data(primary_sources)

        # 知識ギャップ発見
        knowledge_gaps = self._find_knowledge_gaps(step3c_data, primary_sources)

        # セクション配置マッピング
        section_mapping = self._map_sources_to_sections(primary_sources, sections)

        # フェーズ別カウント
        phase1_count = sum(1 for s in primary_sources if s.phase_alignment == "phase1_anxiety")
        phase2_count = sum(1 for s in primary_sources if s.phase_alignment == "phase2_understanding")
        phase3_count = sum(1 for s in primary_sources if s.phase_alignment == "phase3_action")

        activity.logger.info(f"Phase distribution: phase1={phase1_count}, phase2={phase2_count}, phase3={phase3_count}")

        # Build structured output
        output = Step5Output(
            step=self.step_id,
            keyword=keyword,
            search_queries=search_queries[:5],
            sources=primary_sources,
            invalid_sources=invalid_primary_sources,
            failed_queries=failed_queries,
            collection_stats=CollectionStats(
                total_collected=len(collected_sources),
                total_verified=len(verified_sources),
                failed_queries=len(failed_queries),
                phase1_count=phase1_count,
                phase2_count=phase2_count,
                phase3_count=phase3_count,
            ),
            phase_specific_data=phase_specific_data,
            knowledge_gaps_filled=knowledge_gaps,
            section_source_mapping=section_mapping,
        )

        return output.model_dump()

    def _parse_queries(self, content: str) -> list[str]:
        """Parse search queries from LLM response (newline-separated format)."""
        queries = []
        for line in content.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                # Remove numbering like "1. " or "- "
                if line[0].isdigit():
                    line = line.split(".", 1)[-1].strip()
                elif line.startswith("-"):
                    line = line[1:].strip()
                if line:
                    queries.append(line)
        return queries[:5]  # Max 5 queries

    def _validate_collection_quality(
        self,
        sources: list[dict[str, Any]],
        queries: list[str],
        failed: list[dict[str, Any]],
    ) -> QualityResult:
        """Validate source collection quality."""
        issues: list[str] = []
        warnings: list[str] = []
        scores: dict[str, float] = {}

        # Minimum source count
        min_sources = 2
        if len(sources) < min_sources:
            issues.append(f"too_few_sources: {len(sources)} < {min_sources}")

        # Failed query ratio
        if queries:
            fail_ratio = len(failed) / len(queries)
            scores["fail_ratio"] = fail_ratio
            if fail_ratio > 0.5:
                warnings.append(f"high_fail_ratio: {fail_ratio:.2%}")

        # Verified ratio
        if sources:
            verified_count = sum(1 for s in sources if s.get("verified", False))
            verified_ratio = verified_count / len(sources)
            scores["verified_ratio"] = verified_ratio
            if verified_ratio < 0.5:
                warnings.append(f"low_verification_rate: {verified_ratio:.2%}")

        scores["source_count"] = float(len(sources))

        return QualityResult(
            is_acceptable=len(issues) == 0,
            issues=issues,
            warnings=warnings,
            scores=scores,
        )

    # === blog.System Ver8.3 拡張メソッド ===

    def _classify_phase(self, source: dict[str, Any]) -> str:
        """ソースを3フェーズに分類.

        Phase 1 (不安喚起): 問題の深刻さ、リスク、損失
        Phase 2 (理解納得): 解決策、方法、効果
        Phase 3 (行動決定): 成功事例、導入実績、費用対効果
        """
        excerpt = source.get("excerpt", "").lower()
        title = source.get("title", "").lower()
        combined_text = f"{title} {excerpt}"

        # Phase 1 indicators (不安喚起)
        phase1_indicators = [
            "リスク",
            "問題",
            "損失",
            "減少",
            "危険",
            "失敗",
            "課題",
            "深刻",
            "悪化",
            "低下",
            "不足",
            "欠如",
            "脅威",
            "警告",
        ]

        # Phase 2 indicators (理解納得)
        phase2_indicators = [
            "方法",
            "解決",
            "効果",
            "改善",
            "手順",
            "ステップ",
            "対策",
            "施策",
            "アプローチ",
            "戦略",
            "テクニック",
            "ノウハウ",
        ]

        # Phase 3 indicators (行動決定)
        phase3_indicators = [
            "成功",
            "事例",
            "導入",
            "実績",
            "満足",
            "達成",
            "ROI",
            "費用対効果",
            "コスト削減",
            "売上",
            "利益",
            "成果",
        ]

        # Score by keyword matching
        phase1_score = sum(1 for ind in phase1_indicators if ind in combined_text)
        phase2_score = sum(1 for ind in phase2_indicators if ind in combined_text)
        phase3_score = sum(1 for ind in phase3_indicators if ind in combined_text)

        if phase1_score > phase2_score and phase1_score > phase3_score:
            return "phase1_anxiety"
        elif phase3_score > phase1_score and phase3_score > phase2_score:
            return "phase3_action"
        else:
            return "phase2_understanding"

    def _calculate_freshness_score(self, publication_date: str | None) -> float:
        """ソースの鮮度スコアを計算（0.0-1.0）."""
        if not publication_date:
            return 0.5  # 不明な場合は中間値

        try:
            # 年のみの場合
            if len(publication_date) == 4:
                pub_year = int(publication_date)
            else:
                pub_year = datetime.fromisoformat(publication_date.replace("Z", "+00:00")).year

            current_year = datetime.now().year
            age = current_year - pub_year

            if age <= 0:
                return 1.0
            elif age == 1:
                return 0.9
            elif age == 2:
                return 0.7
            elif age == 3:
                return 0.5
            else:
                return max(0.1, 0.5 - (age - 3) * 0.1)
        except (ValueError, TypeError):
            return 0.5

    def _build_phase_specific_data(self, sources: list[PrimarySource]) -> PhaseSpecificData:
        """3フェーズ別のソースデータを集計."""
        phase_data = PhaseSpecificData()

        # Group sources by phase
        phase_groups: dict[str, list[PrimarySource]] = {
            "phase1_anxiety": [],
            "phase2_understanding": [],
            "phase3_action": [],
        }

        for source in sources:
            if source.phase_alignment in phase_groups:
                phase_groups[source.phase_alignment].append(source)

        # Build PhaseData for each phase
        phase_data.phase1_anxiety = PhaseData(
            description="不安喚起：問題の深刻さ、リスク、損失",
            source_urls=[s.url for s in phase_groups["phase1_anxiety"]],
            total_count=len(phase_groups["phase1_anxiety"]),
            key_data_summary=[s.excerpt[:100] for s in phase_groups["phase1_anxiety"][:3]],
            usage_sections=["introduction", "H2-1", "H2-2"],
        )

        phase_data.phase2_understanding = PhaseData(
            description="理解納得：解決策、方法、効果",
            source_urls=[s.url for s in phase_groups["phase2_understanding"]],
            total_count=len(phase_groups["phase2_understanding"]),
            key_data_summary=[s.excerpt[:100] for s in phase_groups["phase2_understanding"][:3]],
            usage_sections=["H2-3", "H2-4", "H2-5", "H2-6", "H2-7", "H2-8", "H2-9", "H2-10"],
        )

        phase_data.phase3_action = PhaseData(
            description="行動決定：成功事例、導入実績、費用対効果",
            source_urls=[s.url for s in phase_groups["phase3_action"]],
            total_count=len(phase_groups["phase3_action"]),
            key_data_summary=[s.excerpt[:100] for s in phase_groups["phase3_action"][:3]],
            usage_sections=["H2-11", "H2-12", "conclusion"],
        )

        return phase_data

    def _find_knowledge_gaps(
        self,
        step3c_data: dict[str, Any] | None,
        sources: list[PrimarySource],
    ) -> list[KnowledgeGap]:
        """step3c競合分析から知識ギャップを発見."""
        gaps: list[KnowledgeGap] = []

        if not step3c_data:
            return gaps

        # 競合カバレッジの低いトピックを抽出
        weak_topics = step3c_data.get("differentiation_angles", [])

        for i, topic in enumerate(weak_topics[:10]):  # 最大10個
            if not isinstance(topic, dict):
                continue

            topic_keyword = topic.get("keyword", topic.get("angle", ""))
            topic_desc = topic.get("description", topic.get("reason", ""))

            # 収集したソースで対応可能か確認
            matching_source_url: str | None = None
            for source in sources:
                if topic_keyword and topic_keyword.lower() in source.excerpt.lower():
                    matching_source_url = source.url
                    break

            # カバレッジ判定
            coverage = topic.get("coverage", topic.get("competitor_count", "不明"))
            if isinstance(coverage, int):
                coverage = f"{coverage}/10記事"

            # 差別化価値判定
            diff_value: str = "medium"
            if isinstance(coverage, str) and coverage.startswith("0"):
                diff_value = "high"
            elif topic.get("importance", "") == "high":
                diff_value = "high"

            gaps.append(
                KnowledgeGap(
                    gap_id=f"KG{i + 1:03d}",
                    gap_description=topic_desc or topic_keyword,
                    competitor_coverage=str(coverage),
                    primary_source_url=matching_source_url,
                    implementation_section=topic.get("recommended_section", ""),
                    differentiation_value=diff_value,  # type: ignore[arg-type]
                )
            )

        return gaps

    def _map_sources_to_sections(
        self,
        sources: list[PrimarySource],
        sections: list[dict[str, Any]],
    ) -> list[SectionSourceMapping]:
        """ソースを各セクションに割り当て."""
        mappings: list[SectionSourceMapping] = []

        if not sections:
            return mappings

        for section in sections:
            section_id = section.get("id", section.get("section_id", ""))
            section_title = section.get("title", section.get("heading", ""))

            # セクション位置からフェーズを推定
            if section_id in ["introduction", "H2-1", "H2-2"]:
                target_phase = "phase1_anxiety"
            elif section_id in ["H2-11", "H2-12", "conclusion"]:
                target_phase = "phase3_action"
            else:
                target_phase = "phase2_understanding"

            # 該当フェーズのソースを優先的に割り当て
            assigned = [s.url for s in sources if s.phase_alignment == target_phase][:3]  # 最大3ソース

            # 優先ソースタイプ
            type_priority = ["statistics", "government_report", "academic_paper"]

            mappings.append(
                SectionSourceMapping(
                    section_id=section_id,
                    section_title=section_title,
                    assigned_sources=assigned,
                    source_type_priority=type_priority,
                    enhancement_notes=f"{target_phase}向けデータ配置",
                )
            )

        return mappings


@activity.defn(name="step5_primary_collection")
async def step5_primary_collection(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 5."""
    step = Step5PrimaryCollection()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
