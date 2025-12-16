"""Deterministic content repairer with mandatory logging.

IMPORTANT: Per project rules, only deterministic repairs are allowed.
Fallback to LLM regeneration is NOT automatic and requires explicit opt-in.
"""

import hashlib
import logging
import re
from collections.abc import Callable
from datetime import UTC, datetime

from .exceptions import RepairError, UnrepairableError
from .schemas import RepairAction, ValidationIssue, ValidationSeverity

logger = logging.getLogger(__name__)


class Repairer:
    """Deterministic content repairer.

    Only performs repairs that are:
    1. Deterministic (same input always produces same output)
    2. Safe (cannot corrupt valid data)
    3. Logged (every repair action is recorded)

    NEVER performs:
    - Fallback to different models/tools
    - Non-deterministic repairs (LLM-based)
    - Silent modifications (all changes logged)
    """

    # Allowed repair operations (all deterministic)
    ALLOWED_REPAIRS: set[str] = {
        "REMOVE_TRAILING_COMMA",  # JSON trailing comma removal
        "FIX_UNESCAPED_QUOTES",  # Escape unescaped quotes in JSON strings
        "NORMALIZE_LINE_ENDINGS",  # Convert all line endings to LF
        "STRIP_BOM",  # Remove UTF-8 BOM
        "TRIM_WHITESPACE",  # Remove trailing whitespace from lines
    }

    # Mapping of issue codes to repair codes
    ISSUE_TO_REPAIR: dict[str, str] = {
        "JSON_TRAILING_COMMA": "REMOVE_TRAILING_COMMA",
        "JSON_INVALID_ESCAPE": "FIX_UNESCAPED_QUOTES",
        "CSV_MIXED_LINE_ENDINGS": "NORMALIZE_LINE_ENDINGS",
        "CSV_UTF8_BOM": "STRIP_BOM",
    }

    def __init__(self) -> None:
        """Initialize the repairer."""
        repair_handler_type = Callable[[str, ValidationIssue], tuple[str, str, str]]
        self._repair_handlers: dict[str, repair_handler_type] = {
            "REMOVE_TRAILING_COMMA": self._repair_trailing_comma,
            "FIX_UNESCAPED_QUOTES": self._repair_unescaped_quotes,
            "NORMALIZE_LINE_ENDINGS": self._repair_line_endings,
            "STRIP_BOM": self._repair_bom,
            "TRIM_WHITESPACE": self._repair_trailing_whitespace,
        }

    def repair(
        self,
        content: str,
        issues: list[ValidationIssue],
    ) -> tuple[str, list[RepairAction]]:
        """Apply deterministic repairs to content.

        Args:
            content: The content to repair.
            issues: List of validation issues to repair.

        Returns:
            Tuple of (repaired_content, applied_repairs).

        Raises:
            UnrepairableError: If any issue cannot be repaired deterministically.
            RepairError: If a repair operation fails.
        """
        # Filter to repairable issues only
        repairable_issues = []
        unrepairable_issues = []

        for issue in issues:
            if issue.severity != ValidationSeverity.ERROR:
                continue

            repair_code = self.ISSUE_TO_REPAIR.get(issue.code)
            if repair_code and repair_code in self.ALLOWED_REPAIRS:
                repairable_issues.append((issue, repair_code))
            else:
                unrepairable_issues.append(issue)

        # Check for unrepairable issues
        if unrepairable_issues:
            codes = [issue.code for issue in unrepairable_issues]
            logger.error(
                "Unrepairable issues found",
                extra={
                    "issue_codes": codes,
                    "issue_count": len(unrepairable_issues),
                },
            )
            raise UnrepairableError(
                f"Cannot repair issues: {', '.join(codes)}",
                issues=unrepairable_issues,
            )

        # Apply repairs
        repaired_content = content
        applied_repairs: list[RepairAction] = []

        for issue, repair_code in repairable_issues:
            handler = self._repair_handlers.get(repair_code)
            if not handler:
                raise RepairError(
                    f"No handler for repair code: {repair_code}",
                    repair_code=repair_code,
                    original_content=content,
                )

            try:
                before_snippet, after_snippet, repaired_content = handler(
                    repaired_content, issue
                )

                action = RepairAction(
                    code=repair_code,
                    description=f"Applied {repair_code} for issue {issue.code}",
                    applied_at=datetime.now(UTC),
                    before=before_snippet,
                    after=after_snippet,
                )
                applied_repairs.append(action)

                # Log the repair
                logger.info(
                    "Repair applied",
                    extra={
                        "repair_code": repair_code,
                        "issue_code": issue.code,
                        "location": issue.location,
                        "before": before_snippet[:100] if before_snippet else "",
                        "after": after_snippet[:100] if after_snippet else "",
                    },
                )

            except Exception as e:
                logger.error(
                    "Repair failed",
                    extra={
                        "repair_code": repair_code,
                        "issue_code": issue.code,
                        "error": str(e),
                    },
                )
                raise RepairError(
                    f"Failed to apply {repair_code}: {e}",
                    repair_code=repair_code,
                    original_content=content,
                ) from e

        return repaired_content, applied_repairs

    def can_repair(self, issues: list[ValidationIssue]) -> bool:
        """Check if all error-level issues can be repaired deterministically.

        Args:
            issues: List of validation issues to check.

        Returns:
            True if all error-level issues can be repaired.
        """
        for issue in issues:
            if issue.severity != ValidationSeverity.ERROR:
                continue

            repair_code = self.ISSUE_TO_REPAIR.get(issue.code)
            if not repair_code or repair_code not in self.ALLOWED_REPAIRS:
                return False

        return True

    def get_unrepairable_issues(
        self, issues: list[ValidationIssue]
    ) -> list[ValidationIssue]:
        """Get list of issues that cannot be repaired deterministically.

        Args:
            issues: List of validation issues to check.

        Returns:
            List of issues that cannot be repaired.
        """
        unrepairable = []
        for issue in issues:
            if issue.severity != ValidationSeverity.ERROR:
                continue

            repair_code = self.ISSUE_TO_REPAIR.get(issue.code)
            if not repair_code or repair_code not in self.ALLOWED_REPAIRS:
                unrepairable.append(issue)

        return unrepairable

    # --- Repair handlers ---

    def _repair_trailing_comma(
        self,
        content: str,
        issue: ValidationIssue,
    ) -> tuple[str, str, str]:
        """Remove trailing commas before closing brackets in JSON."""
        pattern = re.compile(r",(\s*[}\]])")

        def replacer(match: re.Match[str]) -> str:
            return match.group(1)

        # Find the first match to get before/after snippets
        match = pattern.search(content)
        if not match:
            return "", "", content

        before = match.group(0)
        after = match.group(1)

        repaired = pattern.sub(replacer, content)
        return before, after, repaired

    def _repair_unescaped_quotes(
        self,
        content: str,
        issue: ValidationIssue,
    ) -> tuple[str, str, str]:
        """Escape unescaped quotes within JSON strings.

        This is a conservative repair that only handles obvious cases.
        """
        # This is a simplified implementation - real JSON string parsing
        # would need a proper state machine

        # Pattern to find strings with unescaped quotes inside
        # This is conservative and may not catch all cases
        before_examples: list[str] = []
        after_examples: list[str] = []

        lines = content.split("\n")
        repaired_lines = []

        for line in lines:
            # Look for patterns like: "key": "value with "unescaped" quotes"
            # This is a simplified heuristic
            repaired_line = line
            in_string = False
            escape_next = False
            new_chars: list[str] = []

            for i, char in enumerate(line):
                if escape_next:
                    new_chars.append(char)
                    escape_next = False
                    continue

                if char == "\\":
                    new_chars.append(char)
                    escape_next = True
                    continue

                if char == '"':
                    if in_string:
                        # Check if this looks like an unescaped internal quote
                        # by seeing if the next non-whitespace is not : or , or }
                        rest = line[i + 1 :].lstrip()
                        if rest and rest[0] not in [":", ",", "}", "]", "\n"]:
                            # Likely an unescaped quote, escape it
                            new_chars.append('\\"')
                            before_examples.append('"')
                            after_examples.append('\\"')
                            continue
                    in_string = not in_string

                new_chars.append(char)

            repaired_line = "".join(new_chars)
            repaired_lines.append(repaired_line)

        before = before_examples[0] if before_examples else ""
        after = after_examples[0] if after_examples else ""
        repaired = "\n".join(repaired_lines)

        return before, after, repaired

    def _repair_line_endings(
        self,
        content: str,
        issue: ValidationIssue,
    ) -> tuple[str, str, str]:
        """Normalize all line endings to LF."""
        # First, convert CRLF to LF
        repaired = content.replace("\r\n", "\n")
        # Then, convert any remaining CR to LF
        repaired = repaired.replace("\r", "\n")

        before = "CRLF/CR mixed"
        after = "LF only"

        return before, after, repaired

    def _repair_bom(
        self,
        content: str,
        issue: ValidationIssue,
    ) -> tuple[str, str, str]:
        """Remove UTF-8 BOM from content."""
        if content.startswith("\ufeff"):
            return "\\ufeff (BOM)", "", content[1:]
        return "", "", content

    def _repair_trailing_whitespace(
        self,
        content: str,
        issue: ValidationIssue,
    ) -> tuple[str, str, str]:
        """Remove trailing whitespace from each line."""
        lines = content.split("\n")
        repaired_lines = [line.rstrip() for line in lines]
        repaired = "\n".join(repaired_lines)

        return "trailing spaces", "trimmed", repaired


def compute_hash(content: str | bytes) -> str:
    """Compute SHA256 hash of content."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()
