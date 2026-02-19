"""Step 7B: Brush Up Activity.

Polishes and improves the draft with natural language and flow.
Uses Gemini for natural language enhancement.

Integrated helpers:
- InputValidator: Validates step7a draft
- QualityValidator: Validates polishing quality
- ContentMetrics: Calculates change metrics
- OutputParser: Parses Markdown response

blog.System Ver8.3 対応:
- 語尾統一、一文長さ、接続詞の調整詳細
- 文字数維持確認（±5%以内）
- 4本柱維持確認
- 可読性改善メトリクス
"""

import logging
import re
from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.worker.helpers.model_config import get_step_llm_client, get_step_model_config
from apps.api.llm.schemas import LLMRequestConfig
from apps.api.prompts.loader import PromptPackLoader
from apps.worker.activities.schemas.step7b import (
    AdjustmentDetails,
    FourPillarsPreservation,
    PolishMetrics,
    ReadabilityImprovements,
    WordCountComparison,
)
from apps.worker.helpers.content_metrics import ContentMetrics
from apps.worker.helpers.input_validator import InputValidator
from apps.worker.helpers.output_parser import OutputParser
from apps.worker.helpers.quality_validator import (
    CompletenessValidator,
    CompositeValidator,
    StructureValidator,
)

from .base import ActivityError, BaseActivity, load_step_data

logger = logging.getLogger(__name__)

# Constants
MIN_DRAFT_LENGTH = 500


def _build_step7b_quality_validator() -> CompositeValidator:
    """Build quality validator for Step7b."""
    return CompositeValidator(
        validators=[
            StructureValidator(min_h2_sections=2),
            CompletenessValidator(check_truncation=True),
        ]
    )


def _validate_polishing_quality(
    original: str,
    polished: str,
) -> tuple[bool, list[str]]:
    """
    Validate polishing quality.

    Checks:
    - Content not reduced by more than 30%
    - Content not inflated by more than 50%
    - Most sections preserved
    - Conclusion preserved
    - Not truncated

    Returns:
        tuple[bool, list[str]]: (is_acceptable, list of issues)
    """
    issues: list[str] = []

    # Word count comparison
    orig_words = len(original.split())
    polished_words = len(polished.split())

    if orig_words > 0:
        # Check not reduced by more than 30%
        if polished_words < orig_words * 0.7:
            issues.append(
                f"not_reduced: polished content significantly reduced ({polished_words}/{orig_words} = {polished_words / orig_words:.1%})"
            )

        # Check not inflated by more than 50%
        if polished_words > orig_words * 1.5:
            issues.append(
                f"not_inflated: polished content significantly inflated ({polished_words}/{orig_words} = {polished_words / orig_words:.1%})"
            )

    # Section preservation check
    orig_sections = len(re.findall(r"^##\s", original, re.MULTILINE))
    polished_sections = len(re.findall(r"^##\s", polished, re.MULTILINE))

    if orig_sections > 0 and polished_sections < orig_sections * 0.8:
        issues.append(f"sections_preserved: sections reduced from {orig_sections} to {polished_sections}")

    # Conclusion preservation check
    conclusion_patterns = ["まとめ", "結論", "おわり"]
    orig_has_conclusion = any(p in original.lower() for p in conclusion_patterns)
    polished_has_conclusion = any(p in polished.lower() for p in conclusion_patterns)

    if orig_has_conclusion and not polished_has_conclusion:
        issues.append("conclusion_preserved: conclusion section missing in polished content")

    # Truncation check
    truncation_indicators = ["...", "…", "、"]
    stripped = polished.rstrip()
    if any(stripped.endswith(ind) for ind in truncation_indicators):
        issues.append("not_truncated: polished content appears to be truncated")

    return len(issues) == 0, issues


class Step7BBrushUp(BaseActivity):
    """Activity for draft polishing and brush up.

    blog.System Ver8.3 対応:
    - V2モード判定と厳格なバリデーション
    - 調整詳細の追跡
    - 文字数維持確認（±5%以内）
    - 4本柱維持確認
    - 可読性改善メトリクス
    """

    # 4本柱のキーワードパターン
    FOUR_PILLARS_PATTERNS = {
        "neuroscience": ["神経科学", "脳科学", "扁桃体", "前頭前野", "線条体", "ドーパミン"],
        "behavioral_economics": [
            "行動経済学",
            "損失回避",
            "社会的証明",
            "権威性",
            "一貫性",
            "好意",
            "希少性",
        ],
        "llmo": ["LLMO", "LLM", "AI最適化", "音声検索", "質問形式"],
        "kgi": ["KGI", "コンバージョン", "目標達成", "成果指標"],
    }

    def __init__(self) -> None:
        """Initialize with helpers."""
        super().__init__()
        self.input_validator = InputValidator()
        self.output_parser = OutputParser()
        self.content_metrics = ContentMetrics()
        self.quality_validator = _build_step7b_quality_validator()

    @property
    def step_id(self) -> str:
        return "step7b"

    def _is_v2_mode(self, pack_id: str) -> bool:
        """V2モード（blog.System対応）かどうかを判定."""
        return pack_id.startswith("v2_") or "blog_system" in pack_id.lower()

    def _calculate_avg_sentence_length(self, text: str) -> float:
        """テキストの平均文長を計算."""
        # 日本語の文末パターンで分割
        sentences = re.split(r"[。！？\n]", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            return 0.0
        total_chars = sum(len(s) for s in sentences)
        return total_chars / len(sentences)

    def _check_four_pillars_preservation(self, original: str, polished: str) -> FourPillarsPreservation:
        """4本柱の維持状況を確認."""
        pillar_status: dict[str, str] = {}
        changes_affecting_pillars: list[str] = []

        for pillar, patterns in self.FOUR_PILLARS_PATTERNS.items():
            orig_has = any(p in original for p in patterns)
            polished_has = any(p in polished for p in patterns)

            if orig_has and polished_has:
                pillar_status[pillar] = "preserved"
            elif orig_has and not polished_has:
                pillar_status[pillar] = "removed"
                changes_affecting_pillars.append(f"{pillar} keywords removed")
            elif not orig_has and polished_has:
                pillar_status[pillar] = "modified"
                changes_affecting_pillars.append(f"{pillar} keywords added")
            else:
                pillar_status[pillar] = "preserved"  # 両方になければ維持

        maintained = all(status in ("preserved", "modified") for status in pillar_status.values())

        return FourPillarsPreservation(
            maintained=maintained,
            changes_affecting_pillars=changes_affecting_pillars,
            pillar_status=pillar_status,  # type: ignore[arg-type]
        )

    def _calculate_word_count_comparison(self, original: str, polished: str) -> WordCountComparison:
        """文字数比較を計算."""
        before = len(original)
        after = len(polished)
        change_percent = ((after - before) / before * 100) if before > 0 else 0.0
        is_within_5_percent = abs(change_percent) <= 5.0

        return WordCountComparison(
            before=before,
            after=after,
            change_percent=round(change_percent, 2),
            is_within_5_percent=is_within_5_percent,
        )

    def _calculate_readability_improvements(self, original: str, polished: str) -> ReadabilityImprovements:
        """可読性改善メトリクスを計算."""
        avg_before = self._calculate_avg_sentence_length(original)
        avg_after = self._calculate_avg_sentence_length(polished)

        target_min = 20
        target_max = 35
        is_within_target = target_min <= avg_after <= target_max

        return ReadabilityImprovements(
            avg_sentence_length_before=round(avg_before, 1),
            avg_sentence_length_after=round(avg_after, 1),
            target_range_min=target_min,
            target_range_max=target_max,
            is_within_target=is_within_target,
        )

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute draft brush up.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with polished content
        """
        config = ctx.config
        pack_id = config.get("pack_id")

        if not pack_id:
            raise ActivityError(
                "pack_id is required",
                category=ErrorCategory.NON_RETRYABLE,
            )

        # V2モード判定
        is_v2 = self._is_v2_mode(pack_id)
        if is_v2:
            logger.info("Step7B running in V2 mode (blog.System)")

        # Load prompt pack
        loader = PromptPackLoader()
        prompt_pack = loader.load(pack_id)

        # Get inputs
        keyword = config.get("keyword")

        # Load step data from storage
        step7a_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step7a") or {}
        draft = step7a_data.get("draft", "")

        # Input validation using InputValidator
        validation_result = self.input_validator.validate(
            data={"keyword": keyword, "draft": draft},
            required=["keyword", "draft"],
            min_lengths={"draft": MIN_DRAFT_LENGTH},
        )

        if not validation_result.is_valid:
            missing = ", ".join(validation_result.missing_required)
            raise ActivityError(
                f"Input validation failed: missing {missing}",
                category=ErrorCategory.NON_RETRYABLE,
            )

        if validation_result.quality_issues:
            logger.warning(f"[STEP7B] Input quality issues: {validation_result.quality_issues}")

        # Render prompt
        try:
            prompt_template = prompt_pack.get_prompt("step7b")
            prompt = prompt_template.render(
                keyword=keyword,
                draft=draft,
            )
        except Exception as e:
            raise ActivityError(
                f"Failed to render prompt: {e}",
                category=ErrorCategory.NON_RETRYABLE,
            ) from e

        # Get LLM client - uses 3-tier priority: UI per-step > step defaults > global config
        llm_provider, llm_model = get_step_model_config(self.step_id, config)
        llm = await get_step_llm_client(self.step_id, config, tenant_id=ctx.tenant_id)

        logger.info(f"[STEP7B] Starting LLM call - provider: {llm_provider}, model: {llm_model}")
        logger.info(f"[STEP7B] Draft length: {len(draft)} chars")

        # Execute LLM call
        try:
            llm_config = LLMRequestConfig(
                max_tokens=config.get("max_tokens", 24000),
                temperature=config.get("temperature", 0.8),
            )
            response = await llm.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are a content polishing expert.",
                config=llm_config,
            )
        except Exception as e:
            logger.error(f"[STEP7B] LLM call exception: {type(e).__name__}: {e}")
            raise ActivityError(
                f"LLM call failed: {e}",
                category=ErrorCategory.RETRYABLE,
            ) from e

        logger.info("[STEP7B] LLM call completed successfully")
        logger.info(f"[STEP7B] Raw response length: {len(response.content)}")

        # Parse response using OutputParser
        polished_content = response.content.strip()

        # Remove code block markers if present
        if polished_content.startswith("```markdown"):
            polished_content = polished_content[11:]
        elif polished_content.startswith("```"):
            polished_content = polished_content[3:]
        if polished_content.endswith("```"):
            polished_content = polished_content[:-3]
        polished_content = polished_content.strip()

        if not polished_content:
            raise ActivityError(
                "Empty response from LLM",
                category=ErrorCategory.RETRYABLE,
            )

        logger.info(f"[STEP7B] Polished content length: {len(polished_content)} chars")

        # Validate polishing quality
        quality_warnings: list[str] = []
        is_quality_ok, quality_issues = _validate_polishing_quality(draft, polished_content)
        if not is_quality_ok:
            quality_warnings.extend(quality_issues)
            logger.warning(f"[STEP7B] Polishing quality issues: {quality_issues}")

        # Additional quality check using CompositeValidator
        structure_result = self.quality_validator.validate(polished_content)
        if not structure_result.is_acceptable:
            quality_warnings.extend(structure_result.issues)
            logger.warning(f"[STEP7B] Structure quality issues: {structure_result.issues}")

        # Calculate metrics using ContentMetrics
        comparison = self.content_metrics.compare_content(draft, polished_content)
        text_metrics = self.content_metrics.text_metrics(polished_content)
        md_metrics = self.content_metrics.markdown_metrics(polished_content)

        # Calculate sections modified (estimate based on h2 diff)
        orig_h2 = self.content_metrics.markdown_metrics(draft).h2_count
        polished_h2 = md_metrics.h2_count
        sections_modified = abs(polished_h2 - orig_h2)

        polish_metrics = PolishMetrics(
            original_word_count=self.content_metrics.text_metrics(draft).word_count,
            polished_word_count=text_metrics.word_count,
            word_diff=int(comparison["word_diff"]),
            word_diff_percent=(
                comparison["word_diff"] / self.content_metrics.text_metrics(draft).word_count * 100
                if self.content_metrics.text_metrics(draft).word_count > 0
                else 0.0
            ),
            sections_preserved=min(orig_h2, polished_h2),
            sections_modified=sections_modified,
        )

        # Build output
        result: dict[str, Any] = {
            "step": self.step_id,
            "keyword": keyword or "",
            "polished": polished_content,
            "changes_summary": "",
            "change_count": 0,
            "polish_metrics": polish_metrics.model_dump(),
            "quality_warnings": quality_warnings,
            "model": response.model,
            "model_config_data": {
                "platform": llm_provider,
                "model": llm_model or "",
            },
            "token_usage": {
                "input": response.token_usage.input,
                "output": response.token_usage.output,
            },
            "is_v2": is_v2,
        }

        # V2モードの場合、追加メトリクスを計算
        if is_v2:
            # 文字数比較
            word_count_comparison = self._calculate_word_count_comparison(draft, polished_content)
            result["word_count_comparison"] = word_count_comparison.model_dump()

            # 文字数が±5%を超えている場合は警告
            if not word_count_comparison.is_within_5_percent:
                quality_warnings.append(f"word_count_exceeded_5_percent: {word_count_comparison.change_percent:.1f}%")
                result["quality_warnings"] = quality_warnings

            # 4本柱維持確認
            four_pillars = self._check_four_pillars_preservation(draft, polished_content)
            result["four_pillars_preservation"] = four_pillars.model_dump()

            # 4本柱が削除されている場合は警告
            if not four_pillars.maintained:
                quality_warnings.append(f"four_pillars_not_maintained: {four_pillars.changes_affecting_pillars}")
                result["quality_warnings"] = quality_warnings

            # 可読性改善メトリクス
            readability = self._calculate_readability_improvements(draft, polished_content)
            result["readability_improvements"] = readability.model_dump()

            # 調整詳細（デフォルト値で初期化、LLMから詳細が返ってくれば上書き可能）
            result["adjustment_details"] = AdjustmentDetails().model_dump()

            logger.info(
                f"[STEP7B] V2 metrics - "
                f"word_change: {word_count_comparison.change_percent:.1f}%, "
                f"pillars_maintained: {four_pillars.maintained}, "
                f"avg_sentence: {readability.avg_sentence_length_after:.1f}"
            )

        return result


@activity.defn(name="step7b_brush_up")
async def step7b_brush_up(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 7B."""
    step = Step7BBrushUp()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
