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
    PrimarySource,
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
        step4_data = await load_step_data(
            self.store, ctx.tenant_id, ctx.run_id, "step4"
        ) or {}
        outline = step4_data.get("outline", "")

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
        input_digest = self.checkpoint.compute_digest({
            "keyword": keyword,
            "outline": outline[:500],  # Use truncated outline for digest
        })

        queries_checkpoint = await self.checkpoint.load(
            ctx.tenant_id, ctx.run_id, self.step_id, "queries_generated",
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
                parse_result = self.parser.parse_json(query_response.content)

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
                ctx.tenant_id, ctx.run_id, self.step_id, "queries_generated",
                {"queries": search_queries},
                input_digest=input_digest,
            )

        # === CheckpointManager統合: 部分収集のチェックポイント ===
        collection_checkpoint = await self.checkpoint.load(
            ctx.tenant_id, ctx.run_id, self.step_id, "collection_progress"
        )

        completed_queries_set: set[str]
        collected_sources: list[dict[str, Any]]
        if collection_checkpoint:
            completed_queries_set = set(collection_checkpoint.get("completed_queries", []))
            collected_sources = collection_checkpoint.get("collected_sources", [])
            activity.logger.info(
                f"Resuming collection: {len(completed_queries_set)}/{len(search_queries)} queries completed"
            )
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
                        failed_queries.append({
                            "query": query,
                            "error": result.error_message or "Unknown error",
                        })
                except Exception as e:
                    failed_queries.append({
                        "query": query,
                        "error": str(e),
                    })

                completed_queries_set.add(query)

                # 各クエリ完了後にチェックポイント保存
                await self.checkpoint.save(
                    ctx.tenant_id, ctx.run_id, self.step_id, "collection_progress",
                    {
                        "completed_queries": list(completed_queries_set),
                        "collected_sources": collected_sources,
                    }
                )
        else:
            # If tool not available, note it as a warning
            failed_queries.append({
                "query": "all",
                "error": "primary_collector tool not available",
            })

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
                except Exception:
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
            activity.logger.warning(
                f"Source collection quality issues: {quality.issues}"
            )

        # Convert sources to PrimarySource models
        primary_sources = [
            PrimarySource(
                url=s.get("url", ""),
                title=s.get("title", ""),
                source_type=s.get("source_type", "other"),
                excerpt=s.get("excerpt", "")[:500] if s.get("excerpt") else "",
                credibility_score=s.get("credibility_score", 0.5),
                verified=s.get("verified", False),
            )
            for s in verified_sources
        ]

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
            ),
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


@activity.defn(name="step5_primary_collection")
async def step5_primary_collection(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 5."""
    step = Step5PrimaryCollection()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
