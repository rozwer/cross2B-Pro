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

    # Regex patterns for code block extraction (case-insensitive for ```JSON, ```Json, etc.)
    _JSON_BLOCK_PATTERN = re.compile(
        r"```json\s*(.*?)\s*```",
        re.DOTALL | re.IGNORECASE,
    )
    _GENERIC_BLOCK_PATTERN = re.compile(
        r"```\s*(.*?)\s*```",
        re.DOTALL,
    )
    # Greedy variants: match outermost code block (handles nested ``` in JSON values)
    _JSON_BLOCK_PATTERN_GREEDY = re.compile(
        r"```json\s*(.*)\s*```",
        re.DOTALL | re.IGNORECASE,
    )
    _GENERIC_BLOCK_PATTERN_GREEDY = re.compile(
        r"```\s*(.*)\s*```",
        re.DOTALL,
    )
    # Pattern for truncated JSON blocks (no closing ```)
    _TRUNCATED_JSON_BLOCK_PATTERN = re.compile(
        r"```json\s*(.*)",
        re.DOTALL | re.IGNORECASE,
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

    # Control characters to strip (BOM, zero-width spaces, bidi marks, line/paragraph separators)
    _CONTROL_CHARS = re.compile(
        r"[\x00-\x08\x0b\x0c\x0e-\x1f\ufeff\u200b\u200c\u200d\u200e\u200f\u2028\u2029\u2060]"
    )

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

        # Step 2.5: Try greedy code block extraction (handles nested ``` in JSON values)
        greedy_extracted, was_greedy = self._extract_greedy_code_block(content)
        if was_greedy and greedy_extracted != extracted:
            try:
                data = json.loads(greedy_extracted)
                fixes_applied.append("greedy_code_block_extraction")
                return ParseResult(
                    success=True,
                    data=data,
                    raw=content,
                    format_detected="json",
                    fixes_applied=fixes_applied,
                )
            except json.JSONDecodeError:
                # Try deterministic fixes on greedy result
                g_fixed, g_fix_names = self.apply_deterministic_fixes(greedy_extracted)
                if g_fixed is not None:
                    try:
                        data = json.loads(g_fixed)
                        fixes_applied.append("greedy_code_block_extraction")
                        fixes_applied.extend(g_fix_names)
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

    def _extract_greedy_code_block(self, content: str) -> tuple[str, bool]:
        """
        Extract content from code block using greedy matching.

        Greedy patterns match the OUTERMOST code block, handling cases where
        JSON values contain nested ``` markers (e.g., Markdown in final_content).

        Returns:
            tuple[str, bool]: (extracted content, whether extraction occurred)
        """
        match = self._JSON_BLOCK_PATTERN_GREEDY.search(content)
        if match:
            return match.group(1).strip(), True

        match = self._GENERIC_BLOCK_PATTERN_GREEDY.search(content)
        if match:
            return match.group(1).strip(), True

        return content.strip(), False

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

        # Try to extract raw JSON object/array from surrounding text
        raw_json = self._extract_raw_json(content)
        if raw_json:
            return raw_json, True

        # Return as-is
        return content.strip(), False

    def _extract_raw_json(self, content: str) -> str | None:
        """
        Extract a JSON object or array embedded in free text.

        Finds ``{`` or ``[`` and its matching closing bracket by tracking
        nesting depth while respecting string literals.  If the first
        candidate is not valid JSON, retries from the next ``{`` / ``[``.

        Returns:
            str or None: Extracted JSON string, or None if not found.
        """
        stripped = content.strip()

        # If content already looks like bare JSON, skip extraction
        if stripped.startswith(("{", "[")):
            return None

        search_from = 0
        while search_from < len(stripped):
            candidate = self._find_balanced_json(stripped, search_from)
            if candidate is None:
                return None

            text, end_pos = candidate
            # Validate: try as-is first, then with comment stripping
            try:
                json.loads(text)
                return text
            except json.JSONDecodeError:
                cleaned = self._strip_js_comments(text)
                try:
                    json.loads(cleaned)
                    return cleaned
                except json.JSONDecodeError:
                    # False positive — resume search after this opening bracket
                    search_from = end_pos + 1

        return None

    def _find_balanced_json(self, content: str, search_from: int) -> tuple[str, int] | None:
        """
        Find the next balanced ``{...}`` or ``[...]`` starting at *search_from*.

        Returns:
            tuple of (extracted_text, end_position) or None.
        """
        start = -1
        open_char = ""
        close_char = ""
        for i in range(search_from, len(content)):
            ch = content[i]
            if ch == "{":
                start = i
                open_char, close_char = "{", "}"
                break
            if ch == "[":
                start = i
                open_char, close_char = "[", "]"
                break

        if start == -1:
            return None

        # Walk forward tracking depth and string state
        depth = 0
        in_string = False
        escape_next = False

        for i in range(start, len(content)):
            ch = content[i]

            if escape_next:
                escape_next = False
                continue

            if ch == "\\":
                if in_string:
                    escape_next = True
                continue

            if ch == '"':
                in_string = not in_string
                continue

            if in_string:
                continue

            if ch == open_char:
                depth += 1
            elif ch == close_char:
                depth -= 1
                if depth == 0:
                    return content[start : i + 1], i

        return None

    @staticmethod
    def _strip_js_comments(content: str) -> str:
        """
        Remove JS-style comments while preserving string literals.

        Tracks whether the current position is inside a JSON string to avoid
        stripping ``//`` in URLs like ``"https://example.com"`` or ``//`` in
        string values like ``"a // b"``.

        Handles both ``// line`` and ``/* block */`` comments.
        """
        result: list[str] = []
        i = 0
        length = len(content)
        in_string = False
        escape_next = False

        while i < length:
            ch = content[i]

            # Handle escape sequences inside strings
            if escape_next:
                result.append(ch)
                escape_next = False
                i += 1
                continue

            if in_string:
                result.append(ch)
                if ch == "\\":
                    escape_next = True
                elif ch == '"':
                    in_string = False
                i += 1
                continue

            # Outside string: check for comments
            if ch == '"':
                in_string = True
                result.append(ch)
                i += 1
                continue

            if ch == "/" and i + 1 < length:
                next_ch = content[i + 1]
                if next_ch == "/":
                    # Line comment: skip until newline
                    i += 2
                    while i < length and content[i] != "\n":
                        i += 1
                    continue
                if next_ch == "*":
                    # Block comment: skip until */
                    i += 2
                    while i + 1 < length:
                        if content[i] == "*" and content[i + 1] == "/":
                            i += 2
                            break
                        i += 1
                    else:
                        i = length  # unterminated block comment
                    continue

            result.append(ch)
            i += 1

        return "".join(result)

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

        # Strip control characters (BOM, zero-width spaces)
        cleaned = self._CONTROL_CHARS.sub("", fixed)
        if cleaned != fixed:
            fixed = cleaned
            fixes_applied.append("control_chars_removed")

        # Remove JS-style comments (string-aware scanner)
        without_comments = self._strip_js_comments(fixed)
        if without_comments != fixed:
            fixed = without_comments
            fixes_applied.append("js_comments_removed")

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
