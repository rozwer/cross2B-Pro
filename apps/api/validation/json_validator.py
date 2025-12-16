"""JSON validation with syntax checking and schema validation."""

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any

import jsonschema
from jsonschema import Draft7Validator

from .base import ValidatorInterface
from .schemas import ValidationIssue, ValidationReport, ValidationSeverity


class JsonValidator(ValidatorInterface):
    """Validator for JSON content.

    Performs:
    - Syntax validation (trailing commas, unescaped characters, etc.)
    - Schema validation (JSON Schema Draft 7)
    - Location-aware error reporting
    """

    # Common JSON syntax issues that can be detected
    TRAILING_COMMA_PATTERN = re.compile(r",\s*([}\]])")
    SINGLE_QUOTE_PATTERN = re.compile(r"(?<!\\)'([^']*)'(?=\s*:)")

    def validate(self, content: str | bytes) -> ValidationReport:
        """Validate JSON syntax without schema constraints."""
        if isinstance(content, bytes):
            try:
                content = content.decode("utf-8")
            except UnicodeDecodeError as e:
                return self._create_report(
                    content=content if isinstance(content, str) else "",
                    valid=False,
                    issues=[
                        ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            code="JSON_INVALID_ENCODING",
                            message=f"Content is not valid UTF-8: {e}",
                            location=None,
                        )
                    ],
                )

        original_hash = self._compute_hash(content)
        issues: list[ValidationIssue] = []

        # Check for common syntax issues before parsing
        issues.extend(self._detect_syntax_issues(content))

        # Try to parse the JSON
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code=self._classify_json_error(e),
                    message=str(e),
                    location=f"line {e.lineno}, column {e.colno}",
                )
            )

        has_errors = any(i.severity == ValidationSeverity.ERROR for i in issues)

        return ValidationReport(
            valid=not has_errors,
            format="json",
            issues=issues,
            repairs=[],
            validated_at=datetime.now(UTC),
            original_hash=original_hash,
            repaired_hash=None,
        )

    def validate_with_schema(
        self,
        content: str | bytes,
        schema: dict[str, Any],
    ) -> ValidationReport:
        """Validate JSON content against a JSON Schema."""
        # First, do basic validation
        basic_report = self.validate(content)

        # If basic validation failed with parse errors, return early
        if not basic_report.valid:
            return basic_report

        if isinstance(content, bytes):
            content = content.decode("utf-8")

        original_hash = self._compute_hash(content)
        issues: list[ValidationIssue] = []

        try:
            data = json.loads(content)

            # Validate schema itself first
            Draft7Validator.check_schema(schema)

            # Validate data against schema
            validator = Draft7Validator(schema)
            for error in sorted(validator.iter_errors(data), key=lambda e: str(e.path)):
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="JSON_SCHEMA_VIOLATION",
                        message=error.message,
                        location=self._format_json_path(list(error.path)),
                    )
                )

        except json.JSONDecodeError as e:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code=self._classify_json_error(e),
                    message=str(e),
                    location=f"line {e.lineno}, column {e.colno}",
                )
            )
        except jsonschema.SchemaError as e:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="JSON_INVALID_SCHEMA",
                    message=f"Invalid schema: {e.message}",
                    location=self._format_json_path(list(e.path)),
                )
            )

        has_errors = any(i.severity == ValidationSeverity.ERROR for i in issues)

        return ValidationReport(
            valid=not has_errors,
            format="json",
            issues=issues,
            repairs=[],
            validated_at=datetime.now(UTC),
            original_hash=original_hash,
            repaired_hash=None,
        )

    def _detect_syntax_issues(self, content: str) -> list[ValidationIssue]:
        """Detect common JSON syntax issues before parsing."""
        issues: list[ValidationIssue] = []

        # Check for trailing commas
        for match in self.TRAILING_COMMA_PATTERN.finditer(content):
            line_num = content[: match.start()].count("\n") + 1
            col_num = match.start() - content.rfind("\n", 0, match.start())
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="JSON_TRAILING_COMMA",
                    message="Trailing comma before closing bracket",
                    location=f"line {line_num}, column {col_num}",
                )
            )

        # Check for single quotes used as string delimiters (keys)
        for match in self.SINGLE_QUOTE_PATTERN.finditer(content):
            line_num = content[: match.start()].count("\n") + 1
            col_num = match.start() - content.rfind("\n", 0, match.start())
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="JSON_SINGLE_QUOTES",
                    message="Single quotes used instead of double quotes for key",
                    location=f"line {line_num}, column {col_num}",
                )
            )

        return issues

    def _classify_json_error(self, error: json.JSONDecodeError) -> str:
        """Classify a JSON decode error into a specific error code."""
        msg = error.msg.lower()

        if "trailing" in msg:
            return "JSON_TRAILING_COMMA"
        elif "expecting" in msg and "delimiter" in msg:
            return "JSON_MISSING_DELIMITER"
        elif "expecting property name" in msg:
            return "JSON_INVALID_PROPERTY"
        elif "unterminated string" in msg:
            return "JSON_UNTERMINATED_STRING"
        elif "invalid escape" in msg:
            return "JSON_INVALID_ESCAPE"
        elif "invalid control character" in msg:
            return "JSON_INVALID_CONTROL_CHAR"
        elif "extra data" in msg:
            return "JSON_EXTRA_DATA"
        else:
            return "JSON_PARSE_ERROR"

    def _format_json_path(self, path: list[Any]) -> str:
        """Format a JSON path for error reporting."""
        if not path:
            return "root"

        parts = []
        for p in path:
            if isinstance(p, int):
                parts.append(f"[{p}]")
            else:
                if parts:
                    parts.append(f".{p}")
                else:
                    parts.append(str(p))

        return "".join(parts)

    def _create_report(
        self,
        content: str,
        valid: bool,
        issues: list[ValidationIssue],
    ) -> ValidationReport:
        """Create a validation report with the given parameters."""
        return ValidationReport(
            valid=valid,
            format="json",
            issues=issues,
            repairs=[],
            validated_at=datetime.now(UTC),
            original_hash=self._compute_hash(content) if content else "",
            repaired_hash=None,
        )

    def _compute_hash(self, content: str | bytes) -> str:
        """Compute SHA256 hash of content."""
        if isinstance(content, str):
            content = content.encode("utf-8")
        return hashlib.sha256(content).hexdigest()
