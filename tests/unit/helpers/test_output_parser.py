"""Tests for OutputParser."""

import pytest

from apps.worker.helpers import OutputParser, ParseResult


class TestParseJson:
    """parse_json tests."""

    def test_parse_plain_json(self) -> None:
        """Parse plain JSON."""
        parser = OutputParser()
        result = parser.parse_json('{"key": "value"}')

        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.format_detected == "json"
        assert result.fixes_applied == []

    def test_parse_json_with_code_block(self) -> None:
        """Parse ```json code block."""
        parser = OutputParser()
        content = '```json\n{"key": "value"}\n```'
        result = parser.parse_json(content)

        assert result.success is True
        assert result.data == {"key": "value"}
        assert "code_block_removed" in result.fixes_applied

    def test_parse_json_with_generic_code_block(self) -> None:
        """Parse ``` code block (no language specifier)."""
        parser = OutputParser()
        content = '```\n{"key": "value"}\n```'
        result = parser.parse_json(content)

        assert result.success is True
        assert result.data == {"key": "value"}

    def test_fix_trailing_comma_in_object(self) -> None:
        """Fix trailing comma in object."""
        parser = OutputParser()
        content = '{"key": "value",}'
        result = parser.parse_json(content)

        assert result.success is True
        assert result.data == {"key": "value"}
        assert "trailing_comma_removed" in result.fixes_applied

    def test_fix_trailing_comma_in_array(self) -> None:
        """Fix trailing comma in array."""
        parser = OutputParser()
        content = '["a", "b",]'
        result = parser.parse_json(content)

        assert result.success is True
        assert result.data == ["a", "b"]
        assert "trailing_comma_removed" in result.fixes_applied

    def test_parse_failure_returns_raw(self) -> None:
        """Parse failure returns raw string."""
        parser = OutputParser()
        content = "This is not JSON"
        result = parser.parse_json(content)

        assert result.success is False
        assert result.data is None
        assert result.raw == content
        assert result.format_detected == "unknown"

    def test_nested_json(self) -> None:
        """Parse nested JSON."""
        parser = OutputParser()
        content = '{"outer": {"inner": [1, 2, 3]}}'
        result = parser.parse_json(content)

        assert result.success is True
        assert result.data["outer"]["inner"] == [1, 2, 3]

    def test_json_with_surrounding_text(self) -> None:
        """Parse JSON code block with surrounding text."""
        parser = OutputParser()
        content = 'Here is the result:\n```json\n{"key": "value"}\n```\nDone.'
        result = parser.parse_json(content)

        assert result.success is True
        assert result.data == {"key": "value"}

    def test_json_array_root(self) -> None:
        """Parse JSON array as root."""
        parser = OutputParser()
        content = '[{"id": 1}, {"id": 2}]'
        result = parser.parse_json(content)

        assert result.success is True
        assert result.data == [{"id": 1}, {"id": 2}]

    def test_empty_json_object(self) -> None:
        """Parse empty JSON object."""
        parser = OutputParser()
        content = "{}"
        result = parser.parse_json(content)

        assert result.success is True
        assert result.data == {}

    def test_empty_json_array(self) -> None:
        """Parse empty JSON array."""
        parser = OutputParser()
        content = "[]"
        result = parser.parse_json(content)

        assert result.success is True
        assert result.data == []

    def test_fix_nested_trailing_commas(self) -> None:
        """Fix trailing commas in nested structure."""
        parser = OutputParser()
        content = '{"outer": {"inner": [1, 2,],},}'
        result = parser.parse_json(content)

        assert result.success is True
        assert result.data["outer"]["inner"] == [1, 2]
        assert "trailing_comma_removed" in result.fixes_applied

    def test_markdown_detected_on_failure(self) -> None:
        """Markdown format detected when JSON parse fails."""
        parser = OutputParser()
        content = "# Title\n\nSome content"
        result = parser.parse_json(content)

        assert result.success is False
        assert result.format_detected == "markdown"

    def test_json_with_whitespace(self) -> None:
        """Parse JSON with extra whitespace."""
        parser = OutputParser()
        content = '  \n  {"key": "value"}  \n  '
        result = parser.parse_json(content)

        assert result.success is True
        assert result.data == {"key": "value"}


class TestExtractJsonBlock:
    """extract_json_block tests."""

    def test_extract_from_json_block(self) -> None:
        """Extract from ```json block."""
        parser = OutputParser()
        content = '```json\n{"key": "value"}\n```'
        extracted = parser.extract_json_block(content)

        assert extracted == '{"key": "value"}'

    def test_extract_from_generic_block(self) -> None:
        """Extract from ``` block."""
        parser = OutputParser()
        content = '```\n{"key": "value"}\n```'
        extracted = parser.extract_json_block(content)

        assert extracted == '{"key": "value"}'

    def test_no_code_block(self) -> None:
        """Return stripped content when no code block."""
        parser = OutputParser()
        content = '  {"key": "value"}  '
        extracted = parser.extract_json_block(content)

        assert extracted == '{"key": "value"}'


class TestApplyDeterministicFixes:
    """apply_deterministic_fixes tests."""

    def test_fix_trailing_comma_object(self) -> None:
        """Fix trailing comma in object."""
        parser = OutputParser()
        content = '{"key": "value",}'
        fixed, fixes = parser.apply_deterministic_fixes(content)

        assert fixed == '{"key": "value"}'
        assert "trailing_comma_removed" in fixes

    def test_fix_trailing_comma_array(self) -> None:
        """Fix trailing comma in array."""
        parser = OutputParser()
        content = '["a", "b",]'
        fixed, fixes = parser.apply_deterministic_fixes(content)

        assert fixed == '["a", "b"]'
        assert "trailing_comma_removed" in fixes

    def test_no_fix_needed(self) -> None:
        """No fix needed returns None."""
        parser = OutputParser()
        content = '{"key": "value"}'
        fixed, fixes = parser.apply_deterministic_fixes(content)

        assert fixed is None
        assert fixes == []

    def test_multiple_trailing_commas(self) -> None:
        """Fix multiple trailing commas."""
        parser = OutputParser()
        content = '{"a": [1,], "b": 2,}'
        fixed, fixes = parser.apply_deterministic_fixes(content)

        assert fixed == '{"a": [1], "b": 2}'
        assert "trailing_comma_removed" in fixes
        # Should only have one trailing_comma_removed entry
        assert fixes.count("trailing_comma_removed") == 1


class TestLooksLikeMarkdown:
    """looks_like_markdown tests."""

    @pytest.mark.parametrize(
        "content",
        [
            "# Title",
            "## Section",
            "### Subsection",
            "* list item",
            "- list item",
            "1. numbered item",
        ],
    )
    def test_detects_markdown(self, content: str) -> None:
        """Detect Markdown format."""
        parser = OutputParser()
        assert parser.looks_like_markdown(content) is True

    def test_plain_text_not_markdown(self) -> None:
        """Plain text is not Markdown."""
        parser = OutputParser()
        assert parser.looks_like_markdown("Just plain text") is False

    def test_json_not_markdown(self) -> None:
        """JSON is not Markdown."""
        parser = OutputParser()
        assert parser.looks_like_markdown('{"key": "value"}') is False

    def test_inline_hash_not_markdown(self) -> None:
        """Inline hash is not header."""
        parser = OutputParser()
        # Hash not at line start
        assert parser.looks_like_markdown("This is #not a header") is False

    def test_multiline_with_markdown(self) -> None:
        """Multiline content with Markdown."""
        parser = OutputParser()
        content = "Some text\n## Header\nMore text"
        assert parser.looks_like_markdown(content) is True


class TestLooksLikeJson:
    """looks_like_json tests."""

    def test_detects_json_object(self) -> None:
        """Detect JSON object."""
        parser = OutputParser()
        assert parser.looks_like_json('{"key": "value"}') is True

    def test_detects_json_array(self) -> None:
        """Detect JSON array."""
        parser = OutputParser()
        assert parser.looks_like_json("[1, 2, 3]") is True

    def test_not_json(self) -> None:
        """Non-JSON content."""
        parser = OutputParser()
        assert parser.looks_like_json("plain text") is False
        assert parser.looks_like_json("# Markdown") is False

    def test_json_with_whitespace(self) -> None:
        """JSON with surrounding whitespace."""
        parser = OutputParser()
        assert parser.looks_like_json("  {}\n  ") is True
        assert parser.looks_like_json("\n[]\n") is True

    def test_partial_json_not_detected(self) -> None:
        """Partial JSON not detected."""
        parser = OutputParser()
        assert parser.looks_like_json("{incomplete") is False
        assert parser.looks_like_json("[incomplete") is False
