"""Tests for JSON validator."""

import json

import pytest

from apps.api.validation import JsonValidator, ValidationSeverity


class TestJsonValidatorBasicValidation:
    """Tests for basic JSON validation without schema."""

    def test_valid_json_passes(self, valid_json: str) -> None:
        """Valid JSON should pass validation."""
        validator = JsonValidator()
        report = validator.validate(valid_json)

        assert report.valid is True
        assert report.format == "json"
        assert report.error_count() == 0
        assert report.original_hash != ""
        assert report.repaired_hash is None

    def test_empty_object_is_valid(self) -> None:
        """Empty JSON object should be valid."""
        validator = JsonValidator()
        report = validator.validate("{}")

        assert report.valid is True
        assert report.error_count() == 0

    def test_empty_array_is_valid(self) -> None:
        """Empty JSON array should be valid."""
        validator = JsonValidator()
        report = validator.validate("[]")

        assert report.valid is True
        assert report.error_count() == 0

    def test_trailing_comma_detected(self, json_with_trailing_comma: str) -> None:
        """JSON with trailing comma should be detected."""
        validator = JsonValidator()
        report = validator.validate(json_with_trailing_comma)

        assert report.valid is False
        # Should have warning about trailing comma AND error from parse failure
        assert any(
            issue.code == "JSON_TRAILING_COMMA" for issue in report.issues
        )

    def test_truncated_json_fails(self, truncated_json: str) -> None:
        """Truncated JSON should fail validation."""
        validator = JsonValidator()
        report = validator.validate(truncated_json)

        assert report.valid is False
        assert report.error_count() > 0

    def test_bytes_input_valid(self, valid_json: str) -> None:
        """Validator should accept bytes input."""
        validator = JsonValidator()
        report = validator.validate(valid_json.encode("utf-8"))

        assert report.valid is True

    def test_invalid_utf8_fails(self) -> None:
        """Invalid UTF-8 bytes should fail validation."""
        validator = JsonValidator()
        invalid_bytes = b'{"key": "value \xff invalid"}'
        report = validator.validate(invalid_bytes)

        assert report.valid is False
        assert any(
            issue.code == "JSON_INVALID_ENCODING" for issue in report.issues
        )

    def test_hash_is_computed(self, valid_json: str) -> None:
        """Original hash should be computed correctly."""
        validator = JsonValidator()
        report = validator.validate(valid_json)

        assert report.original_hash != ""
        assert len(report.original_hash) == 64  # SHA256 hex

    def test_validated_at_is_set(self, valid_json: str) -> None:
        """Validation timestamp should be set."""
        validator = JsonValidator()
        report = validator.validate(valid_json)

        assert report.validated_at is not None


class TestJsonValidatorSchemaValidation:
    """Tests for JSON schema validation."""

    def test_valid_json_passes_schema(
        self, valid_json: str, simple_json_schema: dict
    ) -> None:
        """Valid JSON should pass schema validation."""
        validator = JsonValidator()
        report = validator.validate_with_schema(valid_json, simple_json_schema)

        assert report.valid is True

    def test_missing_required_field_fails(self, simple_json_schema: dict) -> None:
        """JSON missing required field should fail schema validation."""
        validator = JsonValidator()
        json_without_title = '{"keywords": ["test"]}'
        report = validator.validate_with_schema(json_without_title, simple_json_schema)

        assert report.valid is False
        assert any(
            issue.code == "JSON_SCHEMA_VIOLATION" for issue in report.issues
        )

    def test_wrong_type_fails(self, simple_json_schema: dict) -> None:
        """JSON with wrong type should fail schema validation."""
        validator = JsonValidator()
        json_wrong_type = '{"title": 123}'  # title should be string
        report = validator.validate_with_schema(json_wrong_type, simple_json_schema)

        assert report.valid is False
        assert any(
            issue.code == "JSON_SCHEMA_VIOLATION" for issue in report.issues
        )

    def test_invalid_schema_fails(self, valid_json: str) -> None:
        """Invalid schema should fail validation."""
        validator = JsonValidator()
        invalid_schema = {"type": "invalid_type"}
        report = validator.validate_with_schema(valid_json, invalid_schema)

        assert report.valid is False
        assert any(
            issue.code == "JSON_INVALID_SCHEMA" for issue in report.issues
        )

    def test_location_includes_path(self) -> None:
        """Schema violations should include JSON path in location."""
        validator = JsonValidator()
        schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                }
            },
        }
        json_content = '{"items": ["valid", 123, "also_valid"]}'
        report = validator.validate_with_schema(json_content, schema)

        assert report.valid is False
        # Should have location like "items[1]"
        assert any(
            issue.location and "items" in issue.location for issue in report.issues
        )


class TestJsonValidatorErrorClassification:
    """Tests for JSON error classification."""

    def test_classify_missing_comma(self) -> None:
        """Missing comma should be classified correctly."""
        validator = JsonValidator()
        json_missing_comma = '{"a": 1 "b": 2}'
        report = validator.validate(json_missing_comma)

        assert report.valid is False
        # Should have parse error
        assert any(
            issue.severity == ValidationSeverity.ERROR for issue in report.issues
        )

    def test_classify_unterminated_string(self) -> None:
        """Unterminated string should be classified correctly."""
        validator = JsonValidator()
        json_unterminated = '{"key": "value'
        report = validator.validate(json_unterminated)

        assert report.valid is False

    def test_classify_extra_data(self) -> None:
        """Extra data after JSON should be classified correctly."""
        validator = JsonValidator()
        json_extra = '{"key": "value"} extra'
        report = validator.validate(json_extra)

        assert report.valid is False


class TestJsonValidatorHelperMethods:
    """Tests for ValidationReport helper methods."""

    def test_has_errors(self, truncated_json: str) -> None:
        """has_errors should return True when there are errors."""
        validator = JsonValidator()
        report = validator.validate(truncated_json)

        assert report.has_errors() is True

    def test_has_warnings(self, json_with_trailing_comma: str) -> None:
        """has_warnings should return True when there are warnings."""
        validator = JsonValidator()
        report = validator.validate(json_with_trailing_comma)

        # Trailing comma detection adds a warning
        assert report.has_warnings() is True

    def test_error_count(self, truncated_json: str) -> None:
        """error_count should return correct count."""
        validator = JsonValidator()
        report = validator.validate(truncated_json)

        assert report.error_count() > 0

    def test_warning_count(self, json_with_trailing_comma: str) -> None:
        """warning_count should return correct count."""
        validator = JsonValidator()
        report = validator.validate(json_with_trailing_comma)

        assert report.warning_count() > 0
