"""Step 3C: Competitor Analysis & Differentiation Activity.

Analyzes competitors to find differentiation opportunities.
Runs in parallel with step3a and step3b.
Uses Gemini for analysis.

blog.System統合版:
- word_count_analysis: 競合文字数分析とtarget_word_count算出
- ranking_factor_analysis: 5 Whys深層分析
- four_pillars_differentiation: 4本柱差別化設計
- three_phase_differentiation_strategy: 3フェーズ差別化戦略
- competitor_cta_analysis: 競合CTA分析
"""

import logging
import statistics
from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.llm.base import get_llm_client
from apps.api.llm.exceptions import (
    LLMAuthenticationError,
    LLMInvalidRequestError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from apps.api.llm.schemas import LLMCallMetadata, LLMRequestConfig
from apps.api.prompts.loader import PromptPackLoader
from apps.worker.helpers import (
    CheckpointManager,
    ContentMetrics,
    InputValidator,
    OutputParser,
    QualityResult,
    QualityRetryLoop,
)

from .base import ActivityError, BaseActivity, load_step_data

logger = logging.getLogger(__name__)


# =============================================================================
# Word Count Mode Constants
# =============================================================================

WORD_COUNT_MODES = {
    "ai_seo_optimized": 1.2,  # 平均+20%
    "ai_readability": 0.9,  # 平均-10%
    "ai_balanced": 1.05,  # 平均+5%（±5%の上限）
    "manual": None,  # スキップ
}


class Step3CQualityValidator:
    """Quality validator for competitor analysis."""

    # 最小出力サイズ（バイト）- これ以下は明らかに不完全
    MIN_OUTPUT_SIZE = 3000

    def validate(self, content: str, **kwargs: str) -> QualityResult:
        """Validate competitor analysis quality.

        Checks:
        1. Minimum output size (truncation detection)
        2. Truncation indicators
        3. Differentiation analysis keywords
        4. Presence of recommendations
        5. 4本柱キーワード（blog.System統合）
        6. 5 Whys構造（blog.System統合）
        """
        issues: list[str] = []
        content_lower = content.lower()

        # Check for minimum output size (truncation detection)
        content_size = len(content.encode("utf-8"))
        if content_size < self.MIN_OUTPUT_SIZE:
            issues.append("output_too_small")
            logger.warning(f"step3c output too small: {content_size} bytes < {self.MIN_OUTPUT_SIZE} bytes")

        # Check for truncation indicators (incomplete JSON)
        truncation_indicators = [
            '",',  # JSON途中で切れた
            '":',  # JSONキー途中で切れた
            "\\n",  # エスケープシーケンス途中
        ]
        stripped = content.rstrip()
        if stripped and not stripped.endswith(("}", "}", "]", '"')):
            # JSON/テキストが正常に終了していない
            for indicator in truncation_indicators:
                if stripped.endswith(indicator):
                    issues.append("appears_truncated")
                    logger.warning("step3c output appears truncated")
                    break

        # Check for differentiation keywords
        differentiation_keywords = [
            "差別化",
            "differentiation",
            "独自",
            "unique",
            "強み",
            "strength",
            "弱み",
            "weakness",
        ]
        found = sum(1 for kw in differentiation_keywords if kw in content_lower)
        if found < 2:
            issues.append("insufficient_differentiation_analysis")

        # Check for recommendation keywords
        recommendation_indicators = [
            "推奨",
            "recommend",
            "すべき",
            "should",
            "提案",
            "suggest",
            "戦略",
            "strategy",
        ]
        found_rec = sum(1 for kw in recommendation_indicators if kw in content_lower)
        if found_rec < 1:
            issues.append("no_recommendations")

        # Check for 4本柱 keywords (blog.System integration)
        four_pillars_keywords = [
            "neuroscience",
            "神経科学",
            "behavioral_economics",
            "行動経済学",
            "llmo",
            "kgi",
            "cvr",
        ]
        found_pillars = sum(1 for kw in four_pillars_keywords if kw in content_lower)
        if found_pillars < 2:
            issues.append("insufficient_four_pillars")

        # Check for word_count_analysis (blog.System integration)
        word_count_keywords = [
            "word_count",
            "文字数",
            "average",
            "平均",
            "target",
            "目標",
        ]
        found_wc = sum(1 for kw in word_count_keywords if kw in content_lower)
        if found_wc < 2:
            issues.append("insufficient_word_count_analysis")

        # Critical issues that should not be acceptable regardless of count
        critical_issues = {"output_too_small", "appears_truncated"}
        has_critical = bool(set(issues) & critical_issues)

        return QualityResult(
            is_acceptable=not has_critical and len(issues) <= 2,  # criticalなら不許容
            issues=issues,
        )


class Step3CCompetitorAnalysis(BaseActivity):
    """Activity for competitor analysis and differentiation."""

    # Quality thresholds
    MIN_COMPETITORS = 2
    MIN_CONTENT_PER_COMPETITOR = 200

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.parser = OutputParser()
        self.checkpoint = CheckpointManager(self.store)
        self.metrics = ContentMetrics()
        self.input_validator = InputValidator()
        self.quality_validator = Step3CQualityValidator()

    @property
    def step_id(self) -> str:
        return "step3c"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute competitor analysis.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with competitor analysis and differentiation strategy
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
        word_count_mode = config.get("word_count_mode", "ai_balanced")

        # Load step data from storage (not from config to avoid gRPC size limits)
        step1_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step1") or {}
        competitors = step1_data.get("competitors", [])

        if not keyword:
            raise ActivityError(
                "keyword is required in config",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Input validation
        validation = self.input_validator.validate(
            data={"step1": step1_data},
            required=["step1.competitors"],
        )

        if not validation.is_valid:
            raise ActivityError(
                f"Input validation failed: {validation.missing_required}",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Filter quality competitors (minimum content length)
        quality_competitors = [c for c in competitors if len(c.get("content", "")) >= self.MIN_CONTENT_PER_COMPETITOR]

        if len(quality_competitors) < self.MIN_COMPETITORS:
            raise ActivityError(
                f"Insufficient quality competitors: {len(quality_competitors)} (minimum: {self.MIN_COMPETITORS})",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # Checkpoint: analysis data
        analysis_checkpoint = await self.checkpoint.load(ctx.tenant_id, ctx.run_id, self.step_id, "analysis_data")

        if analysis_checkpoint:
            competitor_analysis = analysis_checkpoint["competitor_analysis"]
        else:
            competitor_analysis = self._prepare_competitor_analysis(quality_competitors)
            await self.checkpoint.save(
                ctx.tenant_id,
                ctx.run_id,
                self.step_id,
                "analysis_data",
                {"competitor_analysis": competitor_analysis},
            )

        # Compute word count statistics (before LLM call)
        word_count_stats = self._compute_word_count_statistics(quality_competitors, word_count_mode, keyword)

        # Render prompt with word_count_mode
        try:
            prompt_template = prompt_pack.get_prompt("step3c")
            initial_prompt = prompt_template.render(
                keyword=keyword,
                word_count_mode=word_count_mode,
                competitors=competitor_analysis,
            )
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client (Gemini for step3c)
        llm_provider = config.get("llm_provider", "gemini")
        llm_model = config.get("llm_model")
        llm = get_llm_client(llm_provider, model=llm_model)

        # LLM config - increased max_tokens for blog.System integration
        llm_config = LLMRequestConfig(
            max_tokens=config.get("max_tokens", 8000),  # Increased for detailed output
            temperature=config.get("temperature", 0.7),
        )
        metadata = LLMCallMetadata(
            run_id=ctx.run_id,
            step_id=self.step_id,
            attempt=ctx.attempt,
            tenant_id=ctx.tenant_id,
        )

        # Define LLM call function for retry loop
        async def llm_call(prompt: str) -> Any:
            try:
                return await llm.generate(
                    messages=[{"role": "user", "content": prompt}],
                    system_prompt=(
                        "You are a competitor analysis expert specializing in SEO content "
                        "strategy with expertise in neuroscience, behavioral economics, "
                        "LLMO, and KGI optimization."
                    ),
                    config=llm_config,
                    metadata=metadata,
                )
            except (LLMRateLimitError, LLMTimeoutError) as e:
                raise ActivityError(
                    f"LLM temporary failure: {e}",
                    category=ErrorCategory.RETRYABLE,
                    details={"llm_error": str(e)},
                ) from e
            except (LLMAuthenticationError, LLMInvalidRequestError) as e:
                raise ActivityError(
                    f"LLM permanent failure: {e}",
                    category=ErrorCategory.NON_RETRYABLE,
                    details={"llm_error": str(e)},
                ) from e
            except Exception as e:
                raise ActivityError(
                    f"LLM call failed: {e}",
                    category=ErrorCategory.RETRYABLE,
                ) from e

        # Define prompt enhancement function
        def enhance_prompt(prompt: str, issues: list[str]) -> str:
            enhancement = "\n\n【追加指示】以下を必ず含めてください：\n"
            for issue in issues:
                if issue == "insufficient_differentiation_analysis":
                    enhancement += "- 各競合の強み・弱みの分析\n"
                    enhancement += "- 差別化ポイントの明示\n"
                elif issue == "no_recommendations":
                    enhancement += "- 具体的な戦略・提案\n"
                elif issue == "insufficient_four_pillars":
                    enhancement += "- 4本柱（神経科学・行動経済学・LLMO・KGI）での差別化設計\n"
                elif issue == "insufficient_word_count_analysis":
                    enhancement += "- word_count_analysis（競合文字数分析とtarget_word_count）\n"
            return prompt + enhancement

        # Quality retry loop
        retry_loop = QualityRetryLoop(max_retries=1, accept_on_final=True)

        loop_result = await retry_loop.execute(
            llm_call=llm_call,
            initial_prompt=initial_prompt,
            validator=self.quality_validator,
            enhance_prompt=enhance_prompt,
            extract_content=lambda r: r.content,
        )

        if not loop_result.success or loop_result.result is None:
            quality_issues = loop_result.quality.issues if loop_result.quality else "unknown"
            raise ActivityError(
                f"Quality validation failed after retries: {quality_issues}",
                category=ErrorCategory.RETRYABLE,
            )

        response = loop_result.result
        content: str = response.content

        # Parse output
        parse_result = self.parser.parse_json(content)

        parsed_data = parse_result.data if parse_result.success else None

        # Log warning if parsed_data is null (potential truncation or format issue)
        if parsed_data is None:
            logger.warning(
                "step3c parsed_data is null - output may be truncated or malformed",
                extra={
                    "content_length": len(content),
                    "format_detected": parse_result.format_detected,
                    "parse_error": getattr(parse_result, "error", None),
                },
            )

        # Extract target_word_count from parsed data or use computed value
        target_word_count = None
        if parsed_data and isinstance(parsed_data, dict):
            logger.info(f"Parsed JSON output: {list(parsed_data.keys())}")
            target_word_count = parsed_data.get("target_word_count")

        # Fallback to computed value if not in parsed data
        if target_word_count is None and word_count_stats.get("ai_suggested_word_count"):
            target_word_count = word_count_stats["ai_suggested_word_count"]

        # Calculate content metrics
        text_metrics = self.metrics.text_metrics(content)

        return {
            "step": self.step_id,
            "keyword": keyword,
            "word_count_mode": word_count_mode,
            "competitor_analysis": content,
            "parsed_data": parsed_data,
            "format_detected": parse_result.format_detected,
            "competitor_count": len(competitors),
            "quality_competitor_count": len(quality_competitors),
            # blog.System integration: word count analysis
            "word_count_statistics": word_count_stats,
            "target_word_count": target_word_count,
            "model": response.model,
            "token_usage": {
                "input": response.token_usage.input,
                "output": response.token_usage.output,
            },
            "metrics": {
                "char_count": text_metrics.char_count,
                "word_count": text_metrics.word_count,
            },
            "quality": {
                "attempts": loop_result.attempts,
                "issues": loop_result.quality.issues if loop_result.quality else [],
            },
        }

    def _prepare_competitor_analysis(self, competitors: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Prepare competitor analysis data for prompt."""
        analysis = []
        for i, comp in enumerate(competitors):
            content = comp.get("content", "")
            analysis.append(
                {
                    "rank": i + 1,
                    "url": comp.get("url", ""),
                    "title": comp.get("title", ""),
                    "word_count": len(content),
                    "content_length": len(content),
                    "content_preview": content[:500],  # Increased for better analysis
                }
            )
        return analysis

    def _compute_word_count_statistics(
        self,
        competitors: list[dict[str, Any]],
        word_count_mode: str,
        keyword: str,
    ) -> dict[str, Any]:
        """Compute word count statistics from competitors.

        Args:
            competitors: List of competitor data
            word_count_mode: Mode for target calculation
            keyword: Target keyword

        Returns:
            dict with word count statistics and AI suggestion
        """
        # Extract word counts
        word_counts = []
        article_details = []

        for i, comp in enumerate(competitors):
            content = comp.get("content", "")
            wc = len(content)
            word_counts.append(wc)
            article_details.append(
                {
                    "rank": i + 1,
                    "title": comp.get("title", ""),
                    "url": comp.get("url", ""),
                    "word_count": wc,
                    "notes": "" if wc > 0 else "コンテンツ取得失敗",
                }
            )

        # Filter out zero word counts for statistics
        valid_word_counts = [wc for wc in word_counts if wc > 0]

        if not valid_word_counts:
            return {
                "mode": word_count_mode,
                "analysis_skipped": True,
                "skip_reason": "有効な競合コンテンツがありません",
                "target_keyword": keyword,
            }

        # Calculate statistics
        avg = statistics.mean(valid_word_counts)
        median = statistics.median(valid_word_counts)
        max_wc = max(valid_word_counts)
        min_wc = min(valid_word_counts)
        std_dev = statistics.stdev(valid_word_counts) if len(valid_word_counts) > 1 else 0

        result = {
            "mode": word_count_mode,
            "analysis_skipped": word_count_mode == "manual",
            "skip_reason": "manualモードのため算出スキップ" if word_count_mode == "manual" else "",
            "target_keyword": keyword,
            "competitor_statistics": {
                "average_word_count": round(avg, 1),
                "median_word_count": round(median, 1),
                "max_word_count": max_wc,
                "min_word_count": min_wc,
                "standard_deviation": round(std_dev, 1),
                "data_points": len(valid_word_counts),
            },
            "article_details": article_details,
        }

        # Calculate AI suggestion if not manual mode
        if word_count_mode != "manual":
            multiplier = WORD_COUNT_MODES.get(word_count_mode, 1.05)
            if multiplier is not None:
                ai_suggested = int(avg * multiplier)

                # Mode-specific logic explanation
                mode_logic = {
                    "ai_seo_optimized": f"平均{int(avg)}字 × 1.2（SEO最適化）= {ai_suggested}字",
                    "ai_readability": f"平均{int(avg)}字 × 0.9（読みやすさ重視）= {ai_suggested}字",
                    "ai_balanced": f"平均{int(avg)}字 × 1.05（バランス）= {ai_suggested}字",
                }

                result["ai_suggestion"] = {
                    "ai_suggested_word_count": ai_suggested,
                    "suggestion_logic": mode_logic.get(word_count_mode, f"平均{int(avg)}字から算出"),
                    "note": "",
                }
                result["ai_suggested_word_count"] = ai_suggested
                result["rationale"] = mode_logic.get(word_count_mode, "")
                result["target_word_count_range"] = {
                    "min": ai_suggested - 300,
                    "min_relaxed": ai_suggested - 500,
                    "max": ai_suggested + 300,
                    "target": ai_suggested,
                }
                result["note"] = (
                    "この文字数は達成すべき目標値です。"
                    "目標範囲は±300字です。"
                    "内容が不足し冗長になる場合のみ-500字まで許容します。"
                    "上限+300字は厳格に守ってください。"
                )

        return result


@activity.defn(name="step3c_competitor_analysis")
async def step3c_competitor_analysis(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 3C."""
    step = Step3CCompetitorAnalysis()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
