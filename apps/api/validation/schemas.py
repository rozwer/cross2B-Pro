"""Validation schemas for JSON/CSV validation."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ValidationSeverity(str, Enum):
    """Severity level of validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationIssue(BaseModel):
    """A single validation issue found during validation."""

    severity: ValidationSeverity
    code: str = Field(
        ...,
        description="Error code, e.g., 'JSON_TRAILING_COMMA', 'CSV_COLUMN_MISMATCH'",
    )
    message: str = Field(..., description="Human-readable error message")
    location: str | None = Field(
        default=None,
        description="Location of the issue, e.g., 'line 5, column 10'",
    )


class RepairAction(BaseModel):
    """A repair action that was applied to fix a validation issue."""

    code: str = Field(
        ...,
        description="Repair code, e.g., 'REMOVE_TRAILING_COMMA'",
    )
    description: str = Field(..., description="Human-readable description of the repair")
    applied_at: datetime = Field(..., description="When the repair was applied")
    before: str = Field(..., description="Content before repair (the affected part)")
    after: str = Field(..., description="Content after repair (the affected part)")


class ValidationReport(BaseModel):
    """Complete validation report for a piece of content."""

    valid: bool = Field(..., description="Whether the content is valid")
    format: str = Field(
        ...,
        description="Format type: 'json' or 'csv'",
    )
    issues: list[ValidationIssue] = Field(
        default_factory=list,
        description="List of validation issues found",
    )
    repairs: list[RepairAction] = Field(
        default_factory=list,
        description="List of repairs applied",
    )
    validated_at: datetime = Field(..., description="When validation was performed")
    original_hash: str = Field(
        ...,
        description="SHA256 hash of the original content",
    )
    repaired_hash: str | None = Field(
        default=None,
        description="SHA256 hash of repaired content (if repairs were applied)",
    )

    def has_errors(self) -> bool:
        """Check if there are any ERROR severity issues."""
        return any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)

    def has_warnings(self) -> bool:
        """Check if there are any WARNING severity issues."""
        return any(issue.severity == ValidationSeverity.WARNING for issue in self.issues)

    def error_count(self) -> int:
        """Count ERROR severity issues."""
        return sum(1 for issue in self.issues if issue.severity == ValidationSeverity.ERROR)

    def warning_count(self) -> int:
        """Count WARNING severity issues."""
        return sum(1 for issue in self.issues if issue.severity == ValidationSeverity.WARNING)
