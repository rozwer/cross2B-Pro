"""Tests for shared Pydantic schemas."""

from datetime import datetime

import pytest

from apps.worker.helpers.schemas import (
    CheckpointMetadata,
    CompletenessResult,
    InputValidationResult,
    MarkdownMetrics,
    ParseResult,
    QualityResult,
    StepOutputBase,
    TextMetrics,
)


class TestQualityResult:
    """QualityResult tests."""

    def test_default_values(self) -> None:
        """Default values are set correctly."""
        result = QualityResult(is_acceptable=True)

        assert result.is_acceptable is True
        assert result.issues == []
        assert result.warnings == []
        assert result.scores == {}

    def test_with_issues(self) -> None:
        """Issues can be set."""
        result = QualityResult(
            is_acceptable=False,
            issues=["missing_keyword", "too_short"],
        )

        assert result.is_acceptable is False
        assert len(result.issues) == 2
        assert "missing_keyword" in result.issues
        assert "too_short" in result.issues

    def test_with_warnings_and_scores(self) -> None:
        """Warnings and scores can be set."""
        result = QualityResult(
            is_acceptable=True,
            warnings=["low_quality"],
            scores={"relevance": 0.8, "completeness": 0.9},
        )

        assert result.warnings == ["low_quality"]
        assert result.scores["relevance"] == 0.8
        assert result.scores["completeness"] == 0.9


class TestInputValidationResult:
    """InputValidationResult tests."""

    def test_valid_result(self) -> None:
        """Valid input result."""
        result = InputValidationResult(is_valid=True)

        assert result.is_valid is True
        assert result.missing_required == []
        assert result.missing_recommended == []
        assert result.quality_issues == []

    def test_invalid_result(self) -> None:
        """Invalid input result with missing fields."""
        result = InputValidationResult(
            is_valid=False,
            missing_required=["keyword", "url"],
            missing_recommended=["description"],
            quality_issues=["keyword_too_short"],
        )

        assert result.is_valid is False
        assert len(result.missing_required) == 2
        assert "keyword" in result.missing_required
        assert result.missing_recommended == ["description"]
        assert result.quality_issues == ["keyword_too_short"]


class TestCompletenessResult:
    """CompletenessResult tests."""

    def test_complete_result(self) -> None:
        """Complete result."""
        result = CompletenessResult(is_complete=True)

        assert result.is_complete is True
        assert result.is_truncated is False
        assert result.issues == []

    def test_truncated_result(self) -> None:
        """Truncated result."""
        result = CompletenessResult(
            is_complete=False,
            is_truncated=True,
            issues=["output_truncated_at_4000_chars"],
        )

        assert result.is_complete is False
        assert result.is_truncated is True
        assert len(result.issues) == 1


class TestParseResult:
    """ParseResult tests."""

    def test_successful_parse(self) -> None:
        """Successful parse result."""
        result = ParseResult(
            success=True,
            data={"key": "value"},
            format_detected="json",
        )

        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.format_detected == "json"
        assert result.raw == ""
        assert result.fixes_applied == []

    def test_failed_parse(self) -> None:
        """Failed parse result."""
        result = ParseResult(
            success=False,
            raw="invalid content",
            format_detected="unknown",
        )

        assert result.success is False
        assert result.data is None
        assert result.raw == "invalid content"
        assert result.format_detected == "unknown"

    def test_parse_with_fixes(self) -> None:
        """Parse result with fixes applied."""
        result = ParseResult(
            success=True,
            data={"key": "value"},
            format_detected="json",
            fixes_applied=["trailing_comma_removed", "code_block_removed"],
        )

        assert result.success is True
        assert len(result.fixes_applied) == 2
        assert "trailing_comma_removed" in result.fixes_applied


class TestTextMetrics:
    """TextMetrics tests."""

    def test_all_fields_required(self) -> None:
        """All fields are required."""
        metrics = TextMetrics(
            char_count=100,
            word_count=20,
            paragraph_count=3,
            sentence_count=5,
        )

        assert metrics.char_count == 100
        assert metrics.word_count == 20
        assert metrics.paragraph_count == 3
        assert metrics.sentence_count == 5

    def test_missing_field_raises(self) -> None:
        """Missing required field raises error."""
        with pytest.raises(Exception):  # pydantic.ValidationError
            TextMetrics(char_count=100, word_count=20)  # type: ignore[call-arg]


class TestMarkdownMetrics:
    """MarkdownMetrics tests."""

    def test_default_values(self) -> None:
        """All fields have default values of 0."""
        metrics = MarkdownMetrics()

        assert metrics.h1_count == 0
        assert metrics.h2_count == 0
        assert metrics.h3_count == 0
        assert metrics.h4_count == 0
        assert metrics.list_count == 0
        assert metrics.code_block_count == 0
        assert metrics.link_count == 0
        assert metrics.image_count == 0

    def test_with_values(self) -> None:
        """Custom values can be set."""
        metrics = MarkdownMetrics(
            h1_count=1,
            h2_count=5,
            h3_count=10,
            list_count=3,
            code_block_count=2,
            link_count=8,
        )

        assert metrics.h1_count == 1
        assert metrics.h2_count == 5
        assert metrics.h3_count == 10
        assert metrics.list_count == 3
        assert metrics.code_block_count == 2
        assert metrics.link_count == 8
        assert metrics.h4_count == 0  # default
        assert metrics.image_count == 0  # default


class TestCheckpointMetadata:
    """CheckpointMetadata tests."""

    def test_with_required_fields(self) -> None:
        """Create with required fields only."""
        now = datetime.utcnow()
        meta = CheckpointMetadata(
            phase="queries_generated",
            created_at=now,
        )

        assert meta.phase == "queries_generated"
        assert meta.created_at == now
        assert meta.input_digest is None
        assert meta.step_id == ""

    def test_with_optional_fields(self) -> None:
        """Create with optional fields."""
        now = datetime.utcnow()
        meta = CheckpointMetadata(
            phase="queries_generated",
            created_at=now,
            input_digest="abc123",
            step_id="step5",
        )

        assert meta.phase == "queries_generated"
        assert meta.input_digest == "abc123"
        assert meta.step_id == "step5"


class TestStepOutputBase:
    """StepOutputBase tests."""

    def test_with_required_fields(self) -> None:
        """Create with required fields only."""
        output = StepOutputBase(
            step="step3a",
            keyword="SEO keyword",
        )

        assert output.step == "step3a"
        assert output.keyword == "SEO keyword"
        assert output.execution_time_ms == 0
        assert output.token_usage == {}
        assert output.warnings == []

    def test_with_all_fields(self) -> None:
        """Create with all fields."""
        output = StepOutputBase(
            step="step3a",
            keyword="SEO keyword",
            execution_time_ms=1500,
            token_usage={"input": 100, "output": 500},
            warnings=["retried_once"],
        )

        assert output.step == "step3a"
        assert output.keyword == "SEO keyword"
        assert output.execution_time_ms == 1500
        assert output.token_usage["input"] == 100
        assert output.token_usage["output"] == 500
        assert output.warnings == ["retried_once"]
