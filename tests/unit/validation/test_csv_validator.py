"""Tests for CSV validator."""

import pytest

from apps.api.validation import CsvValidator, ValidationSeverity


class TestCsvValidatorBasicValidation:
    """Tests for basic CSV validation without schema."""

    def test_valid_csv_passes(self, valid_csv: str) -> None:
        """Valid CSV should pass validation."""
        validator = CsvValidator()
        report = validator.validate(valid_csv)

        assert report.valid is True
        assert report.format == "csv"
        assert report.error_count() == 0
        assert report.original_hash != ""
        assert report.repaired_hash is None

    def test_empty_csv_fails(self) -> None:
        """Empty CSV should fail validation."""
        validator = CsvValidator()
        report = validator.validate("")

        assert report.valid is False
        assert any(issue.code == "CSV_EMPTY" for issue in report.issues)

    def test_whitespace_only_csv_fails(self) -> None:
        """Whitespace-only CSV should fail validation."""
        validator = CsvValidator()
        report = validator.validate("   \n\n  \t  ")

        assert report.valid is False
        assert any(issue.code == "CSV_EMPTY" for issue in report.issues)

    def test_column_mismatch_detected(
        self, csv_with_column_mismatch: str
    ) -> None:
        """CSV with column count mismatch should be detected."""
        validator = CsvValidator()
        report = validator.validate(csv_with_column_mismatch)

        assert report.valid is False
        assert any(
            issue.code == "CSV_COLUMN_MISMATCH" for issue in report.issues
        )

    def test_unbalanced_quotes_detected(
        self, csv_with_unbalanced_quotes: str
    ) -> None:
        """CSV with unbalanced quotes should be detected."""
        validator = CsvValidator()
        report = validator.validate(csv_with_unbalanced_quotes)

        assert report.valid is False
        assert any(
            issue.code == "CSV_UNBALANCED_QUOTES" for issue in report.issues
        )

    def test_bytes_input_valid(self, valid_csv: str) -> None:
        """Validator should accept bytes input."""
        validator = CsvValidator()
        report = validator.validate(valid_csv.encode("utf-8"))

        assert report.valid is True

    def test_invalid_utf8_fails(self, csv_with_invalid_utf8: bytes) -> None:
        """Invalid UTF-8 bytes should fail validation."""
        validator = CsvValidator()
        report = validator.validate(csv_with_invalid_utf8)

        assert report.valid is False
        assert any(
            issue.code == "CSV_INVALID_ENCODING" for issue in report.issues
        )

    def test_utf8_bom_warning(self) -> None:
        """UTF-8 BOM should trigger a warning but not fail."""
        validator = CsvValidator()
        csv_with_bom = "\ufeffid,title\n1,Test"
        report = validator.validate(csv_with_bom)

        # BOM is a warning, not an error
        assert any(issue.code == "CSV_UTF8_BOM" for issue in report.issues)
        # But validation should still pass
        assert report.valid is True

    def test_hash_is_computed(self, valid_csv: str) -> None:
        """Original hash should be computed correctly."""
        validator = CsvValidator()
        report = validator.validate(valid_csv)

        assert report.original_hash != ""
        assert len(report.original_hash) == 64  # SHA256 hex

    def test_validated_at_is_set(self, valid_csv: str) -> None:
        """Validation timestamp should be set."""
        validator = CsvValidator()
        report = validator.validate(valid_csv)

        assert report.validated_at is not None


class TestCsvValidatorSchemaValidation:
    """Tests for CSV schema validation."""

    def test_valid_csv_passes_schema(
        self, valid_csv: str, csv_schema: dict
    ) -> None:
        """Valid CSV should pass schema validation."""
        validator = CsvValidator()
        report = validator.validate_with_schema(valid_csv, csv_schema)

        assert report.valid is True

    def test_missing_required_column_fails(self) -> None:
        """CSV missing required column should fail schema validation."""
        validator = CsvValidator()
        csv_without_id = "title,description\nTest,Description"
        schema = {
            "columns": ["id", "title", "description"],
            "required_columns": ["id"],
        }
        report = validator.validate_with_schema(csv_without_id, schema)

        assert report.valid is False
        assert any(
            issue.code == "CSV_MISSING_REQUIRED_COLUMN" for issue in report.issues
        )

    def test_missing_expected_column_warning(self) -> None:
        """CSV missing expected (but not required) column should warn."""
        validator = CsvValidator()
        csv_partial = "id,title\n1,Test"
        schema = {
            "columns": ["id", "title", "description"],
            "required_columns": ["id"],
        }
        report = validator.validate_with_schema(csv_partial, schema)

        # Should pass but have warning
        assert report.valid is True
        assert any(
            issue.code == "CSV_MISSING_COLUMN" for issue in report.issues
        )

    def test_strict_mode_fails_on_extra_column(
        self, strict_csv_schema: dict
    ) -> None:
        """Strict mode should fail on extra columns."""
        validator = CsvValidator()
        csv_extra = "id,title,description,extra\n1,Test,Desc,Extra"
        report = validator.validate_with_schema(csv_extra, strict_csv_schema)

        assert report.valid is False
        assert any(
            issue.code == "CSV_EXTRA_COLUMN" for issue in report.issues
        )

    def test_non_strict_mode_allows_extra_column(self) -> None:
        """Non-strict mode should allow extra columns."""
        validator = CsvValidator()
        csv_extra = "id,title,extra\n1,Test,Extra"
        schema = {
            "columns": ["id", "title"],
            "required_columns": ["id"],
            "strict": False,
        }
        report = validator.validate_with_schema(csv_extra, schema)

        assert report.valid is True

    def test_empty_csv_fails_schema_validation(self, csv_schema: dict) -> None:
        """Empty CSV should fail schema validation."""
        validator = CsvValidator()
        report = validator.validate_with_schema("", csv_schema)

        assert report.valid is False


class TestCsvValidatorLineEndings:
    """Tests for line ending handling."""

    def test_lf_endings_valid(self) -> None:
        """LF line endings should be valid."""
        validator = CsvValidator()
        csv_lf = "id,title\n1,Test\n2,Test2"
        report = validator.validate(csv_lf)

        assert report.valid is True
        assert not any(
            issue.code == "CSV_MIXED_LINE_ENDINGS" for issue in report.issues
        )

    def test_crlf_endings_valid(self) -> None:
        """CRLF line endings should be valid."""
        validator = CsvValidator()
        csv_crlf = "id,title\r\n1,Test\r\n2,Test2"
        report = validator.validate(csv_crlf)

        assert report.valid is True
        assert not any(
            issue.code == "CSV_MIXED_LINE_ENDINGS" for issue in report.issues
        )

    def test_mixed_endings_warning(self) -> None:
        """Mixed line endings should trigger a warning."""
        validator = CsvValidator()
        csv_mixed = "id,title\r\n1,Test\n2,Test2"
        report = validator.validate(csv_mixed)

        # Mixed endings is a warning, not an error
        assert any(
            issue.code == "CSV_MIXED_LINE_ENDINGS" for issue in report.issues
        )


class TestCsvValidatorQuoteHandling:
    """Tests for quote handling in CSV."""

    def test_properly_quoted_fields_valid(self) -> None:
        """Properly quoted fields should be valid."""
        validator = CsvValidator()
        csv_quoted = 'id,title,description\n1,"Quoted Title","Description with, comma"'
        report = validator.validate(csv_quoted)

        assert report.valid is True

    def test_escaped_quotes_valid(self) -> None:
        """Escaped quotes within fields should be valid."""
        validator = CsvValidator()
        csv_escaped = 'id,title\n1,"Title with ""quotes"" inside"'
        report = validator.validate(csv_escaped)

        assert report.valid is True

    def test_multiline_quoted_field_valid(self) -> None:
        """Multiline quoted fields should be valid."""
        validator = CsvValidator()
        csv_multiline = 'id,description\n1,"Line 1\nLine 2\nLine 3"'
        report = validator.validate(csv_multiline)

        assert report.valid is True


class TestCsvValidatorHelperMethods:
    """Tests for ValidationReport helper methods."""

    def test_has_errors(self, csv_with_column_mismatch: str) -> None:
        """has_errors should return True when there are errors."""
        validator = CsvValidator()
        report = validator.validate(csv_with_column_mismatch)

        assert report.has_errors() is True

    def test_has_warnings(self) -> None:
        """has_warnings should return True when there are warnings."""
        validator = CsvValidator()
        csv_with_bom = "\ufeffid,title\n1,Test"
        report = validator.validate(csv_with_bom)

        assert report.has_warnings() is True

    def test_error_count(self, csv_with_column_mismatch: str) -> None:
        """error_count should return correct count."""
        validator = CsvValidator()
        report = validator.validate(csv_with_column_mismatch)

        assert report.error_count() > 0

    def test_warning_count(self) -> None:
        """warning_count should return correct count."""
        validator = CsvValidator()
        csv_with_bom = "\ufeffid,title\n1,Test"
        report = validator.validate(csv_with_bom)

        assert report.warning_count() > 0
