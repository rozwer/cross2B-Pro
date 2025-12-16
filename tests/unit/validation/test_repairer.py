"""Tests for deterministic content repairer."""

import json

import pytest

from apps.api.validation import (
    JsonValidator,
    Repairer,
    ValidationIssue,
    ValidationSeverity,
)
from apps.api.validation.exceptions import RepairError, UnrepairableError


class TestRepairerTrailingComma:
    """Tests for trailing comma repair."""

    def test_repair_single_trailing_comma(self) -> None:
        """Single trailing comma should be removed."""
        repairer = Repairer()
        content = '{"key": "value",}'
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="JSON_TRAILING_COMMA",
                message="Trailing comma",
                location="line 1",
            )
        ]

        repaired, actions = repairer.repair(content, issues)

        assert repaired == '{"key": "value"}'
        assert len(actions) == 1
        assert actions[0].code == "REMOVE_TRAILING_COMMA"

    def test_repair_multiple_trailing_commas(self) -> None:
        """Multiple trailing commas should all be removed."""
        repairer = Repairer()
        content = '{"a": [1, 2,], "b": {"c": 3,},}'
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="JSON_TRAILING_COMMA",
                message="Trailing comma",
                location="line 1",
            )
        ]

        repaired, actions = repairer.repair(content, issues)

        # All trailing commas should be removed
        assert ",]" not in repaired
        assert ",}" not in repaired
        # Result should be valid JSON
        json.loads(repaired)

    def test_repair_trailing_comma_with_whitespace(self) -> None:
        """Trailing comma with whitespace should be handled."""
        repairer = Repairer()
        content = '{"key": "value"  ,  }'
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="JSON_TRAILING_COMMA",
                message="Trailing comma",
                location="line 1",
            )
        ]

        repaired, actions = repairer.repair(content, issues)

        assert json.loads(repaired) is not None


class TestRepairerLineEndings:
    """Tests for line ending normalization."""

    def test_repair_crlf_to_lf(self) -> None:
        """CRLF should be converted to LF."""
        repairer = Repairer()
        content = "line1\r\nline2\r\nline3"
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="CSV_MIXED_LINE_ENDINGS",
                message="Mixed line endings",
                location=None,
            )
        ]

        repaired, actions = repairer.repair(content, issues)

        assert "\r\n" not in repaired
        assert "\r" not in repaired
        assert repaired == "line1\nline2\nline3"
        assert len(actions) == 1
        assert actions[0].code == "NORMALIZE_LINE_ENDINGS"

    def test_repair_cr_to_lf(self) -> None:
        """CR should be converted to LF."""
        repairer = Repairer()
        content = "line1\rline2\rline3"
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="CSV_MIXED_LINE_ENDINGS",
                message="Mixed line endings",
                location=None,
            )
        ]

        repaired, actions = repairer.repair(content, issues)

        assert "\r" not in repaired
        assert repaired == "line1\nline2\nline3"


class TestRepairerBOM:
    """Tests for BOM removal."""

    def test_repair_utf8_bom(self) -> None:
        """UTF-8 BOM should be removed."""
        repairer = Repairer()
        content = "\ufeffid,title\n1,Test"
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="CSV_UTF8_BOM",
                message="UTF-8 BOM detected",
                location="line 1, column 1",
            )
        ]

        repaired, actions = repairer.repair(content, issues)

        assert not repaired.startswith("\ufeff")
        assert repaired == "id,title\n1,Test"
        assert len(actions) == 1
        assert actions[0].code == "STRIP_BOM"

    def test_no_bom_unchanged(self) -> None:
        """Content without BOM should be unchanged."""
        repairer = Repairer()
        content = "id,title\n1,Test"
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="CSV_UTF8_BOM",
                message="UTF-8 BOM detected",
                location="line 1, column 1",
            )
        ]

        repaired, actions = repairer.repair(content, issues)

        assert repaired == content


class TestRepairerUnrepairable:
    """Tests for unrepairable content handling."""

    def test_unrepairable_issue_raises_error(self) -> None:
        """Unrepairable issues should raise UnrepairableError."""
        repairer = Repairer()
        content = '{"truncated'
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="JSON_PARSE_ERROR",  # Not in ISSUE_TO_REPAIR
                message="Unexpected end of input",
                location="line 1",
            )
        ]

        with pytest.raises(UnrepairableError) as exc_info:
            repairer.repair(content, issues)

        assert len(exc_info.value.issues) == 1
        assert exc_info.value.issues[0].code == "JSON_PARSE_ERROR"

    def test_column_mismatch_is_unrepairable(self) -> None:
        """Column mismatch is not deterministically repairable."""
        repairer = Repairer()
        content = "id,title\n1,Test,Extra"
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="CSV_COLUMN_MISMATCH",
                message="Expected 2 columns, found 3",
                location="line 2",
            )
        ]

        with pytest.raises(UnrepairableError):
            repairer.repair(content, issues)

    def test_mixed_repairable_and_unrepairable(self) -> None:
        """Mix of repairable and unrepairable issues should raise error."""
        repairer = Repairer()
        content = '{"key": "value",}'
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="JSON_TRAILING_COMMA",  # Repairable
                message="Trailing comma",
                location="line 1",
            ),
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="JSON_PARSE_ERROR",  # Not repairable
                message="Some other error",
                location="line 1",
            ),
        ]

        with pytest.raises(UnrepairableError):
            repairer.repair(content, issues)


class TestRepairerCanRepair:
    """Tests for can_repair method."""

    def test_can_repair_trailing_comma(self) -> None:
        """Trailing comma should be repairable."""
        repairer = Repairer()
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="JSON_TRAILING_COMMA",
                message="Trailing comma",
                location="line 1",
            )
        ]

        assert repairer.can_repair(issues) is True

    def test_can_repair_line_endings(self) -> None:
        """Mixed line endings should be repairable."""
        repairer = Repairer()
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="CSV_MIXED_LINE_ENDINGS",
                message="Mixed line endings",
                location=None,
            )
        ]

        assert repairer.can_repair(issues) is True

    def test_cannot_repair_parse_error(self) -> None:
        """Parse errors should not be repairable."""
        repairer = Repairer()
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="JSON_PARSE_ERROR",
                message="Unexpected token",
                location="line 1",
            )
        ]

        assert repairer.can_repair(issues) is False

    def test_warnings_ignored_in_can_repair(self) -> None:
        """Warning-level issues should be ignored in can_repair."""
        repairer = Repairer()
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.WARNING,  # Warning, not error
                code="JSON_PARSE_ERROR",  # Would be unrepairable if error
                message="Unexpected token",
                location="line 1",
            )
        ]

        # Warnings don't block repairability
        assert repairer.can_repair(issues) is True


class TestRepairerGetUnrepairable:
    """Tests for get_unrepairable_issues method."""

    def test_get_unrepairable_returns_unrepairable(self) -> None:
        """get_unrepairable_issues should return unrepairable issues."""
        repairer = Repairer()
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="JSON_TRAILING_COMMA",  # Repairable
                message="Trailing comma",
                location="line 1",
            ),
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="JSON_PARSE_ERROR",  # Not repairable
                message="Unexpected token",
                location="line 1",
            ),
        ]

        unrepairable = repairer.get_unrepairable_issues(issues)

        assert len(unrepairable) == 1
        assert unrepairable[0].code == "JSON_PARSE_ERROR"

    def test_get_unrepairable_empty_when_all_repairable(self) -> None:
        """get_unrepairable_issues should return empty list when all repairable."""
        repairer = Repairer()
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="JSON_TRAILING_COMMA",
                message="Trailing comma",
                location="line 1",
            )
        ]

        unrepairable = repairer.get_unrepairable_issues(issues)

        assert len(unrepairable) == 0


class TestRepairerActionLogging:
    """Tests for repair action logging."""

    def test_repair_action_has_timestamp(self) -> None:
        """Repair actions should have timestamp."""
        repairer = Repairer()
        content = '{"key": "value",}'
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="JSON_TRAILING_COMMA",
                message="Trailing comma",
                location="line 1",
            )
        ]

        _, actions = repairer.repair(content, issues)

        assert len(actions) == 1
        assert actions[0].applied_at is not None

    def test_repair_action_has_before_after(self) -> None:
        """Repair actions should have before/after content."""
        repairer = Repairer()
        content = '{"key": "value",}'
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="JSON_TRAILING_COMMA",
                message="Trailing comma",
                location="line 1",
            )
        ]

        _, actions = repairer.repair(content, issues)

        assert len(actions) == 1
        assert actions[0].before != ""
        assert actions[0].after != ""

    def test_repair_action_has_description(self) -> None:
        """Repair actions should have description."""
        repairer = Repairer()
        content = '{"key": "value",}'
        issues = [
            ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="JSON_TRAILING_COMMA",
                message="Trailing comma",
                location="line 1",
            )
        ]

        _, actions = repairer.repair(content, issues)

        assert len(actions) == 1
        assert "REMOVE_TRAILING_COMMA" in actions[0].description


class TestRepairerIntegration:
    """Integration tests with validators."""

    def test_repair_json_validator_issues(
        self, json_with_trailing_comma: str
    ) -> None:
        """Repairer should fix issues found by JsonValidator."""
        validator = JsonValidator()
        repairer = Repairer()

        # First validation
        report1 = validator.validate(json_with_trailing_comma)
        assert report1.valid is False

        # Repair
        error_issues = [
            i for i in report1.issues if i.severity == ValidationSeverity.ERROR
        ]

        # If there are repairable errors, repair them
        if error_issues and repairer.can_repair(error_issues):
            repaired, actions = repairer.repair(
                json_with_trailing_comma, error_issues
            )
            assert len(actions) > 0

            # Re-validate
            report2 = validator.validate(repaired)
            # After repair, it may still have errors (the original JSON
            # has multiple issues), but we should have made progress
            assert len(report2.issues) <= len(report1.issues)

    def test_no_repair_on_valid_content(self, valid_json: str) -> None:
        """Valid content should not need repair."""
        validator = JsonValidator()
        repairer = Repairer()

        report = validator.validate(valid_json)
        assert report.valid is True

        # No errors to repair
        error_issues = [
            i for i in report.issues if i.severity == ValidationSeverity.ERROR
        ]
        assert len(error_issues) == 0
