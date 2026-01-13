"""LLM output parser for JSON and Markdown content.

This module provides robust parsing of LLM outputs:
- JSON extraction from code blocks
- Deterministic fixes for common JSON issues
- Format detection (JSON vs Markdown)
"""

import json
import re

from apps.worker.helpers.schemas import ParseResult


class OutputParser:
    """LLM output parser."""

    # Regex patterns for code block extraction
    # Support both with and without newline after ```json
    _JSON_BLOCK_PATTERN = re.compile(
        r"```json\s*(.*?)\s*```",
        re.DOTALL,
    )
    _GENERIC_BLOCK_PATTERN = re.compile(
        r"```\s*(.*?)\s*```",
        re.DOTALL,
    )
    # Pattern for truncated JSON blocks (no closing ```)
    _TRUNCATED_JSON_BLOCK_PATTERN = re.compile(
        r"```json\s*(.*)",
        re.DOTALL,
    )
    _TRUNCATED_GENERIC_BLOCK_PATTERN = re.compile(
        r"```\s*(.*)",
        re.DOTALL,
    )

    # Regex patterns for Markdown detection
    _MARKDOWN_PATTERNS = [
        re.compile(r"^#\s", re.MULTILINE),  # H1
        re.compile(r"^##\s", re.MULTILINE),  # H2
        re.compile(r"^###\s", re.MULTILINE),  # H3
        re.compile(r"^\*\s", re.MULTILINE),  # Unordered list (*)
        re.compile(r"^-\s", re.MULTILINE),  # Unordered list (-)
        re.compile(r"^\d+\.\s", re.MULTILINE),  # Ordered list
    ]

    # Regex for trailing comma fix
    _TRAILING_COMMA_OBJ = re.compile(r",\s*}")
    _TRAILING_COMMA_ARR = re.compile(r",\s*]")

    def parse_json(self, content: str) -> ParseResult:
        """
        Parse JSON (with code block support).

        Processing flow:
        1. Remove code block markers (```json ... ``` or ``` ... ```)
        2. Attempt JSON parse
        3. On failure, apply deterministic fixes and retry
        4. Return ParseResult

        Args:
            content: Raw LLM output content

        Returns:
            ParseResult: Parse result (success/failure, data, applied fixes)
        """
        fixes_applied: list[str] = []

        # Step 1: Extract JSON from code block if present
        extracted, was_extracted = self._extract_from_code_block(content)
        if was_extracted:
            fixes_applied.append("code_block_removed")

        # Step 2: Try to parse directly
        try:
            data = json.loads(extracted)
            return ParseResult(
                success=True,
                data=data,
                raw=content,
                format_detected="json",
                fixes_applied=fixes_applied,
            )
        except json.JSONDecodeError:
            pass

        # Step 3: Apply deterministic fixes and retry
        fixed, fix_names = self.apply_deterministic_fixes(extracted)
        if fixed is not None:
            fixes_applied.extend(fix_names)
            try:
                data = json.loads(fixed)
                return ParseResult(
                    success=True,
                    data=data,
                    raw=content,
                    format_detected="json",
                    fixes_applied=fixes_applied,
                )
            except json.JSONDecodeError:
                pass

        # Step 4: Failed to parse
        format_detected = "unknown"
        if self.looks_like_markdown(content):
            format_detected = "markdown"

        return ParseResult(
            success=False,
            data=None,
            raw=content,
            format_detected=format_detected,
            fixes_applied=fixes_applied,
        )

    def extract_json_block(self, content: str) -> str:
        """
        Extract JSON code block.

        Supported patterns:
        - ```json\\n{...}\\n```
        - ```\\n{...}\\n```
        - {...} (no code block)

        Args:
            content: Raw content possibly containing code blocks

        Returns:
            str: Extracted JSON string
        """
        extracted, _ = self._extract_from_code_block(content)
        return extracted

    def _extract_from_code_block(self, content: str) -> tuple[str, bool]:
        """
        Extract content from code block.

        Handles both complete and truncated code blocks.

        Returns:
            tuple[str, bool]: (extracted content, whether extraction occurred)
        """
        # Try ```json block first (complete)
        match = self._JSON_BLOCK_PATTERN.search(content)
        if match:
            return match.group(1).strip(), True

        # Try generic ``` block (complete)
        match = self._GENERIC_BLOCK_PATTERN.search(content)
        if match:
            return match.group(1).strip(), True

        # Try truncated ```json block (no closing ```)
        match = self._TRUNCATED_JSON_BLOCK_PATTERN.search(content)
        if match:
            return match.group(1).strip(), True

        # Try truncated generic ``` block
        match = self._TRUNCATED_GENERIC_BLOCK_PATTERN.search(content)
        if match:
            return match.group(1).strip(), True

        # Return as-is
        return content.strip(), False

    def apply_deterministic_fixes(self, content: str) -> tuple[str | None, list[str]]:
        """
        Apply deterministic fixes (logging required).

        Allowed fixes:
        - Trailing comma removal: ,} -> }, ,] -> ]
        - Truncated JSON repair: close open brackets/braces

        Prohibited fixes:
        - Value guessing/completion
        - Structure changes
        - Fallback value insertion

        Args:
            content: JSON string to fix

        Returns:
            tuple[str | None, list[str]]: (fixed string or None, list of applied fix names)
        """
        fixes_applied: list[str] = []
        fixed = content

        # Fix trailing commas in objects: ,} -> }
        if self._TRAILING_COMMA_OBJ.search(fixed):
            fixed = self._TRAILING_COMMA_OBJ.sub("}", fixed)
            fixes_applied.append("trailing_comma_removed")

        # Fix trailing commas in arrays: ,] -> ]
        if self._TRAILING_COMMA_ARR.search(fixed):
            fixed = self._TRAILING_COMMA_ARR.sub("]", fixed)
            if "trailing_comma_removed" not in fixes_applied:
                fixes_applied.append("trailing_comma_removed")

        # Try to repair truncated JSON by closing open brackets
        repaired = self._repair_truncated_json(fixed)
        if repaired != fixed:
            fixed = repaired
            fixes_applied.append("truncated_json_repaired")

        if fixes_applied:
            return fixed, fixes_applied

        return None, []

    def _repair_truncated_json(self, content: str) -> str:
        """
        Attempt to repair truncated JSON by closing unclosed brackets.

        This finds the last complete value and closes all open brackets.

        Args:
            content: Potentially truncated JSON string

        Returns:
            str: Repaired JSON string (or original if repair not needed/possible)
        """
        # Only try repair if content starts with { or [ but doesn't end properly
        stripped = content.strip()
        if not stripped:
            return content

        # Check if already valid JSON
        try:
            json.loads(stripped)
            return content  # Already valid
        except json.JSONDecodeError:
            pass

        # Find the last complete value point
        # Look for patterns that indicate a complete value:
        # - "...",
        # - "..."],
        # - ...},
        # - ...}],
        # - ...", (string followed by comma)
        # - ...": (start of value - truncate here)

        # Find the last complete entry point
        last_complete_patterns = [
            (r'"\s*,\s*$', -1),  # "...",
            (r'"\s*]\s*,\s*$', -1),  # "..."],
            (r"}\s*,\s*$", -1),  # ...},
            (r"}\s*]\s*,\s*$", -1),  # ...}],
            (r"]\s*,\s*$", -1),  # ...],
            (r"true\s*,\s*$", -1),  # true,
            (r"false\s*,\s*$", -1),  # false,
            (r"null\s*,\s*$", -1),  # null,
            (r"\d+\s*,\s*$", -1),  # number,
        ]

        # Try to find the last complete value
        best_pos = -1
        for line in stripped.split("\n"):
            line_end = stripped.rfind(line) + len(line)
            for pattern, _ in last_complete_patterns:
                if re.search(pattern, line):
                    best_pos = max(best_pos, line_end)

        # If we found a truncation point, cut there
        if best_pos > len(stripped) // 2:  # Only if we found substantial content
            truncated = stripped[:best_pos]
            # Remove trailing comma if present
            truncated = re.sub(r",\s*$", "", truncated)
        else:
            # Try different approach: find last complete key-value pair
            # Look for "key": "value" or "key": number/bool/null patterns
            truncated = stripped

        # Count open brackets
        open_braces = truncated.count("{") - truncated.count("}")
        open_brackets = truncated.count("[") - truncated.count("]")

        # Close them in reverse order of opening
        # This is a simplification - we close all brackets then all braces
        if open_brackets > 0 or open_braces > 0:
            closing = "]" * open_brackets + "}" * open_braces
            return truncated + closing

        return content

    def looks_like_markdown(self, content: str) -> bool:
        """
        Determine if content is Markdown format.

        Criteria:
        - ^#\\s (H1)
        - ^##\\s (H2)
        - ^###\\s (H3)
        - ^\\*\\s or ^-\\s (list)
        - ^\\d+\\.\\s (numbered list)

        Args:
            content: Content to check

        Returns:
            bool: True if content looks like Markdown
        """
        for pattern in self._MARKDOWN_PATTERNS:
            if pattern.search(content):
                return True
        return False

    def looks_like_json(self, content: str) -> bool:
        """
        Determine if content is JSON format.

        Criteria:
        - Starts with { and ends with }
        - Starts with [ and ends with ]

        Args:
            content: Content to check

        Returns:
            bool: True if content looks like JSON
        """
        stripped = content.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            return True
        if stripped.startswith("[") and stripped.endswith("]"):
            return True
        return False
