"""CSV validation with column checking and encoding validation."""

import csv
import hashlib
import io
import re
from datetime import datetime, timezone
from typing import Any

from .base import ValidatorInterface
from .schemas import ValidationIssue, ValidationReport, ValidationSeverity


class CsvValidator(ValidatorInterface):
    """Validator for CSV content.

    Performs:
    - Encoding validation (UTF-8 required)
    - Column consistency checking
    - Quote balance checking
    - Schema validation (expected columns)
    """

    def validate(self, content: str | bytes) -> ValidationReport:
        """Validate CSV syntax without schema constraints."""
        issues: list[ValidationIssue] = []
        content_str: str

        # Check encoding
        if isinstance(content, bytes):
            encoding_issues, decoded_content = self._check_encoding(content)
            issues.extend(encoding_issues)
            if decoded_content is None:
                return self._create_report(
                    content="",
                    valid=False,
                    issues=issues,
                )
            content_str = decoded_content
        else:
            content_str = content
            # Check for BOM in string input too
            if content_str.startswith("\ufeff"):
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="CSV_UTF8_BOM",
                        message="Content has UTF-8 BOM (will be stripped)",
                        location="line 1, column 1",
                    )
                )
                content_str = content_str[1:]

        original_hash = self._compute_hash(content_str)

        # Check for empty content
        if not content_str.strip():
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="CSV_EMPTY",
                    message="CSV content is empty",
                    location=None,
                )
            )
            return ValidationReport(
                valid=False,
                format="csv",
                issues=issues,
                repairs=[],
                validated_at=datetime.now(timezone.utc),
                original_hash=original_hash,
                repaired_hash=None,
            )

        # Check for quote balance issues
        issues.extend(self._check_quote_balance(content_str))

        # Check for line ending consistency
        issues.extend(self._check_line_endings(content_str))

        # Parse and check column consistency
        try:
            column_issues = self._check_column_consistency(content_str)
            issues.extend(column_issues)
        except csv.Error as e:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="CSV_PARSE_ERROR",
                    message=str(e),
                    location=None,
                )
            )

        has_errors = any(i.severity == ValidationSeverity.ERROR for i in issues)

        return ValidationReport(
            valid=not has_errors,
            format="csv",
            issues=issues,
            repairs=[],
            validated_at=datetime.now(timezone.utc),
            original_hash=original_hash,
            repaired_hash=None,
        )

    def validate_with_schema(
        self,
        content: str | bytes,
        schema: dict[str, Any],
    ) -> ValidationReport:
        """Validate CSV content against a schema.

        Schema format:
        {
            "columns": ["col1", "col2", "col3"],  # Expected column names
            "required_columns": ["col1"],  # Columns that must be present
            "strict": True,  # If True, no extra columns allowed
        }
        """
        # First, do basic validation
        basic_report = self.validate(content)

        # If basic validation failed, return early
        if not basic_report.valid:
            return basic_report

        if isinstance(content, bytes):
            content = content.decode("utf-8")

        original_hash = self._compute_hash(content)
        issues: list[ValidationIssue] = []

        expected_columns = schema.get("columns", [])
        required_columns = schema.get("required_columns", [])
        strict = schema.get("strict", False)

        try:
            reader = csv.reader(io.StringIO(content))
            header_row = next(reader, None)

            if header_row is None:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="CSV_NO_HEADER",
                        message="CSV has no header row",
                        location="line 1",
                    )
                )
            else:
                actual_columns = [col.strip() for col in header_row]

                # Check for required columns
                for req_col in required_columns:
                    if req_col not in actual_columns:
                        issues.append(
                            ValidationIssue(
                                severity=ValidationSeverity.ERROR,
                                code="CSV_MISSING_REQUIRED_COLUMN",
                                message=f"Required column '{req_col}' is missing",
                                location="line 1",
                            )
                        )

                # Check for expected columns
                if expected_columns:
                    for exp_col in expected_columns:
                        if exp_col not in actual_columns:
                            issues.append(
                                ValidationIssue(
                                    severity=ValidationSeverity.WARNING,
                                    code="CSV_MISSING_COLUMN",
                                    message=f"Expected column '{exp_col}' is missing",
                                    location="line 1",
                                )
                            )

                    # Check for extra columns in strict mode
                    if strict:
                        for actual_col in actual_columns:
                            if actual_col not in expected_columns:
                                issues.append(
                                    ValidationIssue(
                                        severity=ValidationSeverity.ERROR,
                                        code="CSV_EXTRA_COLUMN",
                                        message=f"Unexpected column '{actual_col}' in strict mode",
                                        location="line 1",
                                    )
                                )

        except csv.Error as e:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="CSV_PARSE_ERROR",
                    message=str(e),
                    location=None,
                )
            )

        has_errors = any(i.severity == ValidationSeverity.ERROR for i in issues)

        return ValidationReport(
            valid=not has_errors,
            format="csv",
            issues=issues,
            repairs=[],
            validated_at=datetime.now(timezone.utc),
            original_hash=original_hash,
            repaired_hash=None,
        )

    def _check_encoding(
        self, content: bytes
    ) -> tuple[list[ValidationIssue], str | None]:
        """Check if content is valid UTF-8."""
        issues: list[ValidationIssue] = []

        # Try UTF-8 first (required encoding)
        try:
            decoded = content.decode("utf-8")

            # Check for BOM
            if decoded.startswith("\ufeff"):
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="CSV_UTF8_BOM",
                        message="Content has UTF-8 BOM (will be stripped)",
                        location="line 1, column 1",
                    )
                )
                decoded = decoded[1:]  # Strip BOM

            return issues, decoded

        except UnicodeDecodeError as e:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="CSV_INVALID_ENCODING",
                    message=f"Content is not valid UTF-8: {e}",
                    location=f"byte position {e.start}",
                )
            )
            return issues, None

    def _check_quote_balance(self, content: str) -> list[ValidationIssue]:
        """Check for unbalanced quotes in CSV content.

        This handles multi-line quoted fields correctly by tracking quote state
        across the entire content rather than line by line.
        """
        issues: list[ValidationIssue] = []

        # Track state across entire content
        in_quoted_field = False
        quote_start_line = 0
        line_num = 1
        i = 0

        while i < len(content):
            char = content[i]

            if char == "\n":
                line_num += 1
                i += 1
                continue

            if char == '"':
                if not in_quoted_field:
                    # Starting a quoted field
                    in_quoted_field = True
                    quote_start_line = line_num
                else:
                    # Check if it's an escaped quote ("") inside a quoted field
                    if i + 1 < len(content) and content[i + 1] == '"':
                        i += 2  # Skip escaped quote
                        continue
                    else:
                        # Ending a quoted field
                        in_quoted_field = False

            i += 1

        # If we end still inside a quoted field, it's unbalanced
        if in_quoted_field:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="CSV_UNBALANCED_QUOTES",
                    message=f"Unclosed quote starting on line {quote_start_line}",
                    location=f"line {quote_start_line}",
                )
            )

        return issues

    def _check_line_endings(self, content: str) -> list[ValidationIssue]:
        """Check for mixed line endings."""
        issues: list[ValidationIssue] = []

        has_crlf = "\r\n" in content
        has_cr = "\r" in content.replace("\r\n", "")
        has_lf = "\n" in content.replace("\r\n", "")

        endings_found = sum([has_crlf, has_cr, has_lf])

        if endings_found > 1:
            issues.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="CSV_MIXED_LINE_ENDINGS",
                    message="Mixed line endings detected (CRLF, CR, or LF)",
                    location=None,
                )
            )

        return issues

    def _check_column_consistency(self, content: str) -> list[ValidationIssue]:
        """Check that all rows have the same number of columns."""
        issues: list[ValidationIssue] = []

        reader = csv.reader(io.StringIO(content))
        header_row = next(reader, None)

        if header_row is None:
            return issues

        expected_columns = len(header_row)

        for line_num, row in enumerate(reader, start=2):
            actual_columns = len(row)
            if actual_columns != expected_columns:
                issues.append(
                    ValidationIssue(
                        severity=ValidationSeverity.ERROR,
                        code="CSV_COLUMN_MISMATCH",
                        message=f"Expected {expected_columns} columns, found {actual_columns}",
                        location=f"line {line_num}",
                    )
                )

        return issues

    def _create_report(
        self,
        content: str,
        valid: bool,
        issues: list[ValidationIssue],
    ) -> ValidationReport:
        """Create a validation report with the given parameters."""
        return ValidationReport(
            valid=valid,
            format="csv",
            issues=issues,
            repairs=[],
            validated_at=datetime.now(timezone.utc),
            original_hash=self._compute_hash(content) if content else "",
            repaired_hash=None,
        )

    def _compute_hash(self, content: str | bytes) -> str:
        """Compute SHA256 hash of content."""
        if isinstance(content, str):
            content = content.encode("utf-8")
        return hashlib.sha256(content).hexdigest()
