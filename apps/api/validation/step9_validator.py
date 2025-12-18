"""Step9 output validator with deterministic repair support.

Validates the final rewrite output from step9 before processing in step10.
Performs deterministic repairs where possible, logs all actions.
"""

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any

from .schemas import (
    RepairAction,
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
)

logger = logging.getLogger(__name__)


class Step9OutputValidator:
    """Validator for step9 (final rewrite) output.

    Validates:
    - final_content: minimum length, heading structure, required sections
    - meta_description: presence and length constraints
    - internal_link_suggestions: format validation

    Performs deterministic repairs:
    - Trailing whitespace removal
    - Line ending normalization
    - Excessive heading level normalization (#### -> ###)
    - BOM removal

    Non-repairable issues result in VALIDATION_FAIL.
    """

    # Minimum content length in characters (configurable)
    MIN_CONTENT_LENGTH = 3000  # A reasonable article should be at least 3000 chars
    MAX_CONTENT_LENGTH = 100000  # Upper bound for sanity check

    # Meta description constraints (SEO best practice)
    MIN_META_DESCRIPTION_LENGTH = 80
    MAX_META_DESCRIPTION_LENGTH = 160

    # Heading requirements
    MIN_H2_COUNT = 3  # At least 3 H2 headings for proper structure
    MIN_H3_COUNT = 2  # At least 2 H3 headings for depth

    # Repairable issue codes
    REPAIRABLE_ISSUES: set[str] = {
        "STEP9_TRAILING_WHITESPACE",
        "STEP9_MIXED_LINE_ENDINGS",
        "STEP9_EXCESSIVE_HEADING_LEVEL",
        "STEP9_BOM_PRESENT",
    }

    def __init__(
        self,
        min_content_length: int | None = None,
        min_h2_count: int | None = None,
        min_h3_count: int | None = None,
    ):
        """Initialize validator with optional custom thresholds.

        Args:
            min_content_length: Override minimum content length
            min_h2_count: Override minimum H2 heading count
            min_h3_count: Override minimum H3 heading count
        """
        self.min_content_length = min_content_length or self.MIN_CONTENT_LENGTH
        self.min_h2_count = min_h2_count or self.MIN_H2_COUNT
        self.min_h3_count = min_h3_count or self.MIN_H3_COUNT

    def validate(
        self, step9_data: dict[str, Any], auto_repair: bool = True
    ) -> ValidationReport:
        """Validate step9 output data with optional auto-repair.

        Args:
            step9_data: The output dictionary from step9
            auto_repair: Whether to apply deterministic repairs (default: True)

        Returns:
            ValidationReport with validation results and any repairs applied
        """
        issues: list[ValidationIssue] = []
        repairs: list[RepairAction] = []
        original_data = step9_data.copy()

        # Validate and potentially repair final_content
        final_content = step9_data.get("final_content", "")
        content_issues, content_repairs, repaired_content = self._validate_and_repair_content(
            final_content, auto_repair
        )
        issues.extend(content_issues)
        repairs.extend(content_repairs)

        # Update step9_data with repaired content if repairs were made
        if repaired_content != final_content:
            step9_data["final_content"] = repaired_content

        # Validate meta_description (no repairs for this)
        meta_description = step9_data.get("meta_description", "")
        issues.extend(self._validate_meta_description(meta_description))

        # Validate internal_link_suggestions
        suggestions = step9_data.get("internal_link_suggestions", [])
        issues.extend(self._validate_internal_link_suggestions(suggestions))

        # Validate stats consistency (using repaired content)
        stats = step9_data.get("stats", {})
        issues.extend(self._validate_stats_consistency(repaired_content, stats))

        # Build report
        original_hash = hashlib.sha256(str(original_data).encode()).hexdigest()
        repaired_hash = (
            hashlib.sha256(str(step9_data).encode()).hexdigest()
            if repairs
            else None
        )
        has_errors = any(
            i.severity == ValidationSeverity.ERROR and i.code not in self.REPAIRABLE_ISSUES
            for i in issues
        )

        return ValidationReport(
            valid=not has_errors,
            format="step9_output",
            issues=issues,
            repairs=repairs,
            validated_at=datetime.now(timezone.utc),
            original_hash=original_hash,
            repaired_hash=repaired_hash,
        )

    def _validate_and_repair_content(
        self, content: str, auto_repair: bool
    ) -> tuple[list[ValidationIssue], list[RepairAction], str]:
        """Validate and optionally repair the final article content."""
        issues: list[ValidationIssue] = []
        repairs: list[RepairAction] = []
        repaired_content = content

        # Check presence first
        if not content:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="STEP9_CONTENT_MISSING",
                    message="final_content is empty or missing",
                    location="step9_data.final_content",
                )
            )
            return issues, repairs, repaired_content

        # Apply deterministic repairs if enabled
        if auto_repair:
            repaired_content, repair_actions = self._apply_deterministic_repairs(content)
            repairs.extend(repair_actions)

        # Now validate the (potentially repaired) content
        content_length = len(repaired_content)

        # Check minimum length
        if content_length < self.min_content_length:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="STEP9_CONTENT_TOO_SHORT",
                    message=f"final_content is too short: {content_length} chars "
                    f"(minimum: {self.min_content_length})",
                    location="step9_data.final_content",
                )
            )

        # Check maximum length (sanity check)
        if content_length > self.MAX_CONTENT_LENGTH:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="STEP9_CONTENT_TOO_LONG",
                    message=f"final_content exceeds maximum: {content_length} chars "
                    f"(maximum: {self.MAX_CONTENT_LENGTH})",
                    location="step9_data.final_content",
                )
            )

        # Validate heading structure
        issues.extend(self._validate_headings(repaired_content))

        # Validate no placeholder text remains
        issues.extend(self._validate_no_placeholders(repaired_content))

        return issues, repairs, repaired_content

    def _apply_deterministic_repairs(
        self, content: str
    ) -> tuple[str, list[RepairAction]]:
        """Apply deterministic repairs to content.

        All repairs are logged. Only safe, deterministic repairs are applied.
        """
        repairs: list[RepairAction] = []
        repaired = content

        # 1. Remove BOM if present
        if repaired.startswith("\ufeff"):
            repairs.append(
                RepairAction(
                    code="REMOVE_BOM",
                    description="Removed UTF-8 BOM from content",
                    applied_at=datetime.now(timezone.utc),
                    before="\\ufeff (BOM)",
                    after="",
                )
            )
            repaired = repaired[1:]
            logger.info("Repair applied: REMOVE_BOM")

        # 2. Normalize line endings to LF
        if "\r\n" in repaired or "\r" in repaired:
            before_type = "CRLF" if "\r\n" in repaired else "CR"
            repaired = repaired.replace("\r\n", "\n").replace("\r", "\n")
            repairs.append(
                RepairAction(
                    code="NORMALIZE_LINE_ENDINGS",
                    description=f"Normalized {before_type} line endings to LF",
                    applied_at=datetime.now(timezone.utc),
                    before=f"{before_type} mixed",
                    after="LF only",
                )
            )
            logger.info("Repair applied: NORMALIZE_LINE_ENDINGS")

        # 3. Trim trailing whitespace from lines
        lines = repaired.split("\n")
        has_trailing = any(line != line.rstrip() for line in lines)
        if has_trailing:
            repaired_lines = [line.rstrip() for line in lines]
            repaired = "\n".join(repaired_lines)
            repairs.append(
                RepairAction(
                    code="TRIM_TRAILING_WHITESPACE",
                    description="Removed trailing whitespace from lines",
                    applied_at=datetime.now(timezone.utc),
                    before="trailing spaces/tabs",
                    after="trimmed",
                )
            )
            logger.info("Repair applied: TRIM_TRAILING_WHITESPACE")

        # 4. Normalize excessive heading levels (#### or deeper -> ###)
        excessive_heading_pattern = r"^(#{4,})\s+"
        if re.search(excessive_heading_pattern, repaired, re.MULTILINE):
            def normalize_heading(match: re.Match[str]) -> str:
                return "### "

            repaired = re.sub(
                excessive_heading_pattern,
                normalize_heading,
                repaired,
                flags=re.MULTILINE,
            )
            repairs.append(
                RepairAction(
                    code="NORMALIZE_HEADING_LEVELS",
                    description="Normalized excessive heading levels (####+ -> ###)",
                    applied_at=datetime.now(timezone.utc),
                    before="#### or deeper",
                    after="###",
                )
            )
            logger.info("Repair applied: NORMALIZE_HEADING_LEVELS")

        return repaired, repairs

    def _validate_headings(self, content: str) -> list[ValidationIssue]:
        """Validate heading structure in markdown content."""
        issues: list[ValidationIssue] = []

        # Count H2 headings (## in markdown)
        h2_pattern = r"^##\s+[^\n#]+"
        h2_matches = re.findall(h2_pattern, content, re.MULTILINE)
        h2_count = len(h2_matches)

        if h2_count < self.min_h2_count:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="STEP9_INSUFFICIENT_H2",
                    message=f"Insufficient H2 headings: {h2_count} found "
                    f"(minimum: {self.min_h2_count})",
                    location="step9_data.final_content",
                )
            )

        # Count H3 headings (### in markdown)
        h3_pattern = r"^###\s+[^\n#]+"
        h3_matches = re.findall(h3_pattern, content, re.MULTILINE)
        h3_count = len(h3_matches)

        if h3_count < self.min_h3_count:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="STEP9_INSUFFICIENT_H3",
                    message=f"Few H3 headings: {h3_count} found "
                    f"(recommended minimum: {self.min_h3_count})",
                    location="step9_data.final_content",
                )
            )

        return issues

    def _validate_no_placeholders(self, content: str) -> list[ValidationIssue]:
        """Check for placeholder text that should have been replaced."""
        issues: list[ValidationIssue] = []

        # Common placeholder patterns
        placeholder_patterns = [
            (r"\[TODO[:\s].*?\]", "TODO marker"),
            (r"\[INSERT.*?\]", "INSERT placeholder"),
            (r"\[PLACEHOLDER.*?\]", "PLACEHOLDER marker"),
            (r"{{.*?}}", "Template variable"),
            (r"\[\[.*?\]\]", "Double bracket placeholder"),
            (r"<TODO>.*?</TODO>", "TODO tag"),
            (r"〈.*?を入力〉", "Japanese input placeholder"),
            (r"【.*?を記載】", "Japanese description placeholder"),
        ]

        for pattern, description in placeholder_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="STEP9_PLACEHOLDER_FOUND",
                        message=f"Found {description}: {matches[0][:50]}...",
                        location="step9_data.final_content",
                    )
                )

        return issues

    def _validate_meta_description(self, meta_description: str) -> list[ValidationIssue]:
        """Validate the meta description."""
        issues: list[ValidationIssue] = []

        if not meta_description:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="STEP9_META_MISSING",
                    message="meta_description is empty or missing",
                    location="step9_data.meta_description",
                )
            )
            return issues

        length = len(meta_description)

        if length < self.MIN_META_DESCRIPTION_LENGTH:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="STEP9_META_TOO_SHORT",
                    message=f"meta_description is short: {length} chars "
                    f"(recommended minimum: {self.MIN_META_DESCRIPTION_LENGTH})",
                    location="step9_data.meta_description",
                )
            )

        if length > self.MAX_META_DESCRIPTION_LENGTH:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="STEP9_META_TOO_LONG",
                    message=f"meta_description may be truncated: {length} chars "
                    f"(recommended maximum: {self.MAX_META_DESCRIPTION_LENGTH})",
                    location="step9_data.meta_description",
                )
            )

        return issues

    def _validate_internal_link_suggestions(
        self, suggestions: list[Any]
    ) -> list[ValidationIssue]:
        """Validate internal link suggestions format."""
        issues: list[ValidationIssue] = []

        if not isinstance(suggestions, list):
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="STEP9_LINKS_INVALID_TYPE",
                    message="internal_link_suggestions must be a list",
                    location="step9_data.internal_link_suggestions",
                )
            )
            return issues

        # Validate each suggestion is a string
        for i, suggestion in enumerate(suggestions):
            if not isinstance(suggestion, str):
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="STEP9_LINK_INVALID_FORMAT",
                        message=f"Link suggestion at index {i} is not a string",
                        location=f"step9_data.internal_link_suggestions[{i}]",
                    )
                )

        return issues

    def _validate_stats_consistency(
        self, content: str, stats: dict[str, Any]
    ) -> list[ValidationIssue]:
        """Validate that stats are consistent with actual content."""
        issues: list[ValidationIssue] = []

        if not stats or not content:
            return issues

        # Check word count consistency
        reported_word_count = stats.get("word_count", 0)
        actual_word_count = len(content.split())

        # Allow 10% tolerance for word counting differences
        if reported_word_count > 0 and actual_word_count > 0:
            diff_ratio = abs(reported_word_count - actual_word_count) / actual_word_count
            if diff_ratio > 0.1:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="STEP9_STATS_MISMATCH",
                        message=f"Word count mismatch: reported {reported_word_count}, "
                        f"actual {actual_word_count}",
                        location="step9_data.stats.word_count",
                    )
                )

        # Check char count consistency
        reported_char_count = stats.get("char_count", 0)
        actual_char_count = len(content)

        if reported_char_count > 0 and actual_char_count > 0:
            diff_ratio = abs(reported_char_count - actual_char_count) / actual_char_count
            if diff_ratio > 0.1:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="STEP9_STATS_MISMATCH",
                        message=f"Char count mismatch: reported {reported_char_count}, "
                        f"actual {actual_char_count}",
                        location="step9_data.stats.char_count",
                    )
                )

        return issues
