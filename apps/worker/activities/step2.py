"""Step 2: CSV Validation Activity.

Validates the competitor data from step 1 and prepares it for analysis.
Uses Validation module for data integrity checks.

ヘルパー統合:
- InputValidator: 入力データの検証（必須フィールド、最低件数）
- CheckpointManager: バッチ処理の途中保存
- 自動修復機能: URL正規化、コンテンツ正規化、空白トリム
- 閾値チェック: 最低有効レコード数、最大エラー率
"""

import hashlib
import logging
import re
import statistics
from collections import Counter
from typing import Any

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory
from apps.api.core.state import GraphState
from apps.api.validation.schemas import ValidationSeverity
from apps.worker.helpers import CheckpointManager, ContentMetrics, InputValidator

from .base import ActivityError, BaseActivity, load_step_data

logger = logging.getLogger(__name__)


class Step2CSVValidation(BaseActivity):
    """Activity for CSV validation of competitor data.

    ヘルパー統合:
    - InputValidator: 入力データの検証
    - CheckpointManager: バッチ処理の中間チェックポイント
    - 自動修復機能: URL正規化、コンテンツ正規化
    - 閾値チェック: 最低有効レコード数、最大エラー率
    """

    MAX_ERROR_RATE = 0.3
    MIN_VALID_RECORDS = 2
    BATCH_SIZE = 10

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.checkpoint = CheckpointManager(self.store)
        self.metrics = ContentMetrics()
        self.input_validator = InputValidator()

    @property
    def step_id(self) -> str:
        return "step2"

    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute CSV validation.

        Args:
            ctx: Execution context
            state: Current workflow state

        Returns:
            dict with validation results
        """
        logger.info(f"[STEP2] execute called: tenant_id={ctx.tenant_id}, run_id={ctx.run_id}")

        # Load step1 data from storage
        logger.info("[STEP2] Loading step1 data")
        step1_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step1")

        # Load step1_5 data (optional - related keyword competitor data)
        step1_5_data = await load_step_data(self.store, ctx.tenant_id, ctx.run_id, "step1_5")
        if step1_5_data and not step1_5_data.get("skipped"):
            logger.info(f"[STEP2] Loaded step1_5 data: {step1_5_data.get('related_keywords_analyzed', 0)} keywords")

        # Input validation using InputValidator
        validation_result = self.input_validator.validate(
            data={"step1": step1_data} if step1_data else {},
            required=["step1.competitors"],
            min_counts={"step1.competitors": self.MIN_VALID_RECORDS},
        )

        if not validation_result.is_valid:
            raise ActivityError(
                f"Input validation failed: {validation_result.missing_required}",
                category=ErrorCategory.NON_RETRYABLE,
            )

        competitors = list(step1_data.get("competitors", []))  # type: ignore
        step1_competitor_count = len(competitors)

        # Integrate step1_5 competitors into validation
        step1_5_competitor_count = 0
        if step1_5_data and not step1_5_data.get("skipped"):
            for kw_data in step1_5_data.get("related_competitor_data", []):
                for comp in kw_data.get("competitors", []):
                    # Map step1_5 fields to step1 format for unified validation
                    competitors.append(
                        {
                            "url": comp.get("url", ""),
                            "title": comp.get("title", ""),
                            "content": comp.get("content_summary", ""),  # content_summary -> content
                            "word_count": comp.get("word_count", 0),
                            "headings": comp.get("headings", []),
                            "source": "step1_5",  # Identify source for tracking
                            "related_keyword": comp.get("related_keyword", ""),
                        }
                    )
                    step1_5_competitor_count += 1

            if step1_5_competitor_count > 0:
                logger.info(f"[STEP2] Integrated {step1_5_competitor_count} competitors from step1_5")

        logger.info(
            f"[STEP2] Processing {len(competitors)} competitors (step1: {step1_competitor_count}, step1_5: {step1_5_competitor_count})"
        )

        # === Validation Progress Checkpoint ===
        progress_checkpoint = await self.checkpoint.load(ctx.tenant_id, ctx.run_id, self.step_id, "validation_progress")

        validated_records: list[dict[str, Any]]
        validation_issues: list[dict[str, Any]]

        if progress_checkpoint:
            start_index = progress_checkpoint.get("last_processed_index", -1) + 1
            validated_records = progress_checkpoint.get("validated_records", [])
            validation_issues = progress_checkpoint.get("validation_issues", [])
            auto_fix_count = progress_checkpoint.get("auto_fix_count", 0)
            logger.info(f"[STEP2] Loaded checkpoint: start_index={start_index}, validated={len(validated_records)}")
        else:
            start_index = 0
            validated_records = []
            validation_issues = []
            auto_fix_count = 0

        # Process in batches
        for batch_start in range(start_index, len(competitors), self.BATCH_SIZE):
            batch_end = min(batch_start + self.BATCH_SIZE, len(competitors))
            batch = competitors[batch_start:batch_end]

            for idx, competitor in enumerate(batch, start=batch_start):
                # Auto-fix record
                fixed_record, fixes = self._auto_fix(competitor)

                if fixes:
                    auto_fix_count += 1
                    logger.info(f"[STEP2] Auto-fixed record {idx}: {fixes}")

                # Validate fixed record
                issues = self._validate_record(fixed_record, idx)

                if self._has_critical_errors(issues):
                    validation_issues.append(
                        {
                            "index": idx,
                            "url": competitor.get("url", "unknown"),
                            "issues": issues,
                        }
                    )
                else:
                    # Add content hash and quality score
                    fixed_record["content_hash"] = self._compute_content_hash(fixed_record.get("content", ""))
                    fixed_record["quality_score"] = self._compute_quality_score(fixed_record)
                    fixed_record["auto_fixes_applied"] = fixes
                    validated_records.append(fixed_record)

            # Save checkpoint after each batch
            await self.checkpoint.save(
                ctx.tenant_id,
                ctx.run_id,
                self.step_id,
                "validation_progress",
                {
                    "last_processed_index": batch_end - 1,
                    "validated_records": validated_records,
                    "validation_issues": validation_issues,
                    "auto_fix_count": auto_fix_count,
                },
            )
            activity.heartbeat(f"Validated {batch_end}/{len(competitors)}")

        # Calculate error rate
        error_rate = 1 - (len(validated_records) / max(len(competitors), 1))

        # Threshold checks
        if len(validated_records) < self.MIN_VALID_RECORDS:
            raise ActivityError(
                f"Too few valid records: {len(validated_records)} (minimum: {self.MIN_VALID_RECORDS})",
                category=ErrorCategory.NON_RETRYABLE,
            )

        if error_rate > self.MAX_ERROR_RATE:
            raise ActivityError(
                f"Error rate too high: {error_rate:.1%} (maximum: {self.MAX_ERROR_RATE:.0%})",
                category=ErrorCategory.RETRYABLE,
            )

        # Build validation summary
        validation_summary = {
            "total_records": len(competitors),
            "valid_records": len(validated_records),
            "rejected_records": len(validation_issues),
            "auto_fixed_count": auto_fix_count,
            "error_rate": error_rate,
        }

        logger.info(f"[STEP2] Completed: {len(validated_records)} valid, {len(validation_issues)} rejected, {auto_fix_count} auto-fixed")

        # Compute aggregate analysis for blog.System integration
        word_count_analysis = self._compute_word_count_analysis(validated_records)
        structure_analysis = self._compute_structure_analysis(validated_records)

        if word_count_analysis:
            logger.info(
                f"[STEP2] Word count analysis: min={word_count_analysis['min']}, "
                f"max={word_count_analysis['max']}, avg={word_count_analysis['average']}"
            )
        if structure_analysis:
            logger.info(
                f"[STEP2] Structure analysis: avg_h2={structure_analysis['avg_h2_count']}, "
                f"avg_h3={structure_analysis['avg_h3_count']}, "
                f"patterns={len(structure_analysis['common_patterns'])}"
            )

        return {
            "step": self.step_id,
            "is_valid": True,
            "validation_summary": validation_summary,
            "validated_data": validated_records,
            "rejected_data": [{"url": v["url"], "issues": v["issues"]} for v in validation_issues],
            "validation_issues": validation_issues,
            "word_count_analysis": word_count_analysis,
            "structure_analysis": structure_analysis,
        }

    def _auto_fix(self, record: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        """Auto-fix record issues.

        Args:
            record: Original record

        Returns:
            Tuple of (fixed record, list of applied fixes)
        """
        fixed = record.copy()
        fixes: list[str] = []

        # URL normalization
        if "url" in fixed:
            original_url = fixed["url"]
            fixed["url"] = self._normalize_url(original_url)
            if fixed["url"] != original_url:
                fixes.append("url_normalized")

        # Content normalization
        if "content" in fixed:
            original_len = len(fixed["content"])
            fixed["content"] = self._normalize_content(fixed["content"])
            if len(fixed["content"]) != original_len:
                fixes.append("content_normalized")

        # Trim whitespace from string fields
        for key in ["title", "content"]:
            if key in fixed and isinstance(fixed[key], str):
                stripped = fixed[key].strip()
                if stripped != fixed[key]:
                    fixed[key] = stripped
                    fixes.append(f"{key}_trimmed")

        return fixed, fixes

    def _normalize_url(self, url: str) -> str:
        """Normalize URL.

        Args:
            url: Original URL

        Returns:
            Normalized URL
        """
        url = url.strip()

        # Remove trailing slash
        if url.endswith("/"):
            url = url.rstrip("/")

        # Remove tracking parameters
        tracking_params = ["utm_", "ref=", "fbclid", "gclid"]
        for param in tracking_params:
            if param in url:
                # Simple removal - could be more sophisticated
                if "?" in url:
                    base, query = url.split("?", 1)
                    params = query.split("&")
                    params = [p for p in params if not any(t in p for t in tracking_params)]
                    if params:
                        url = base + "?" + "&".join(params)
                    else:
                        url = base

        return url

    def _normalize_content(self, content: str) -> str:
        """Normalize content text.

        Args:
            content: Original content

        Returns:
            Normalized content
        """
        # Replace multiple spaces/tabs with single space
        content = re.sub(r"[ \t]+", " ", content)

        # Replace 3+ newlines with 2 newlines
        content = re.sub(r"\n{3,}", "\n\n", content)

        # Remove control characters
        content = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", content)

        return content.strip()

    def _validate_record(
        self,
        record: dict[str, Any],
        idx: int,
    ) -> list[dict[str, Any]]:
        """Validate a single record.

        Args:
            record: Record to validate
            idx: Record index

        Returns:
            List of validation issues
        """
        issues: list[dict[str, Any]] = []
        required_fields = ["url", "title", "content"]

        # Check required fields
        for field in required_fields:
            if field not in record or not record[field]:
                issues.append(
                    {
                        "field": field,
                        "issue": "missing_or_empty",
                        "severity": ValidationSeverity.ERROR.value,
                    }
                )

        # Check content length
        content = record.get("content", "")
        if len(content) < 100:
            issues.append(
                {
                    "field": "content",
                    "issue": "content_too_short",
                    "severity": ValidationSeverity.WARNING.value,
                    "value": len(content),
                }
            )

        # Check URL format
        url = record.get("url", "")
        if url and not url.startswith(("http://", "https://")):
            issues.append(
                {
                    "field": "url",
                    "issue": "invalid_url_format",
                    "severity": ValidationSeverity.ERROR.value,
                }
            )

        return issues

    def _has_critical_errors(self, issues: list[dict[str, Any]]) -> bool:
        """Check if issues contain critical errors.

        Args:
            issues: List of validation issues

        Returns:
            True if any critical error exists
        """
        return any(i.get("severity") == ValidationSeverity.ERROR.value for i in issues)

    def _compute_content_hash(self, content: str) -> str:
        """Compute SHA256 hash of content.

        Args:
            content: Content text

        Returns:
            SHA256 hash (hex)
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _compute_quality_score(self, record: dict[str, Any]) -> float:
        """Compute quality score for a record.

        Args:
            record: Validated record

        Returns:
            Quality score (0.0 to 1.0)
        """
        score = 0.5  # Base score

        content = record.get("content", "")
        text_metrics = self.metrics.text_metrics(content, lang="ja")

        # Bonus for longer content
        if text_metrics.word_count > 500:
            score += 0.1
        if text_metrics.word_count > 1000:
            score += 0.1

        # Bonus for structured content
        if record.get("headings"):
            score += 0.1

        # Bonus for title
        title = record.get("title", "")
        if len(title) > 10:
            score += 0.1

        # Penalty for truncated content
        if "[truncated]" in content:
            score -= 0.1

        return min(max(score, 0.0), 1.0)

    def _compute_word_count_analysis(self, validated_records: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Compute word count analysis for validated records.

        Args:
            validated_records: List of validated competitor records

        Returns:
            Word count analysis dict or None if no records
        """
        if not validated_records:
            return None

        word_counts = []
        for record in validated_records:
            content = record.get("content", "")
            text_metrics = self.metrics.text_metrics(content, lang="ja")
            word_counts.append(text_metrics.word_count)

        if not word_counts:
            return None

        return {
            "min": min(word_counts),
            "max": max(word_counts),
            "average": round(statistics.mean(word_counts), 1),
            "median": round(statistics.median(word_counts), 1),
        }

    def _compute_structure_analysis(self, validated_records: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Compute structure analysis for validated records.

        Args:
            validated_records: List of validated competitor records

        Returns:
            Structure analysis dict or None if no records
        """
        if not validated_records:
            return None

        h2_counts: list[int] = []
        h3_counts: list[int] = []
        all_headings: list[str] = []

        for record in validated_records:
            headings = record.get("headings", [])
            h2_count = 0
            h3_count = 0

            for heading in headings:
                # Markdown style or HTML style
                if heading.startswith("## ") or heading.lower().startswith("<h2"):
                    h2_count += 1
                elif heading.startswith("### ") or heading.lower().startswith("<h3"):
                    h3_count += 1

                # Extract heading text for pattern analysis
                text = self._extract_heading_text(heading)
                if text:
                    all_headings.append(text.lower())

            h2_counts.append(h2_count)
            h3_counts.append(h3_count)

        # Find common patterns (headings appearing in 50%+ of articles)
        threshold = max(len(validated_records) // 2, 1)
        heading_counter = Counter(all_headings)
        common_patterns = [heading for heading, count in heading_counter.most_common(10) if count >= threshold]

        return {
            "avg_h2_count": round(statistics.mean(h2_counts), 1) if h2_counts else 0.0,
            "avg_h3_count": round(statistics.mean(h3_counts), 1) if h3_counts else 0.0,
            "common_patterns": common_patterns[:5],  # Top 5 patterns
        }

    def _extract_heading_text(self, heading: str) -> str:
        """Extract plain text from heading.

        Args:
            heading: Heading with markdown or HTML formatting

        Returns:
            Plain text heading
        """
        # Remove markdown prefix
        if heading.startswith("### "):
            return heading[4:].strip()
        if heading.startswith("## "):
            return heading[3:].strip()
        if heading.startswith("# "):
            return heading[2:].strip()

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", heading)
        return text.strip()


@activity.defn(name="step2_csv_validation")
async def step2_csv_validation(args: dict[str, Any]) -> dict[str, Any]:
    """Temporal activity wrapper for step 2."""
    step = Step2CSVValidation()
    return await step.run(
        tenant_id=args["tenant_id"],
        run_id=args["run_id"],
        config=args["config"],
    )
