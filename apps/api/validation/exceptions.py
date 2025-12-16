"""Validation-related exceptions."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .schemas import ValidationIssue


class ValidationError(Exception):
    """Base exception for validation errors.

    Raised when content fails validation and cannot be automatically repaired.
    """

    def __init__(
        self,
        message: str,
        issues: list["ValidationIssue"] | None = None,
    ) -> None:
        super().__init__(message)
        self.issues = issues or []


class RepairError(Exception):
    """Exception raised when a repair operation fails.

    This indicates that an attempted repair could not be applied,
    not that the content is unrepairable.
    """

    def __init__(
        self,
        message: str,
        repair_code: str,
        original_content: str | None = None,
    ) -> None:
        super().__init__(message)
        self.repair_code = repair_code
        self.original_content = original_content


class UnrepairableError(Exception):
    """Exception raised when content cannot be repaired.

    This is raised when validation issues are found that cannot be
    fixed by any deterministic repair operation.

    Note: Per project rules, fallback to LLM regeneration is NOT
    automatic. This exception signals that manual intervention or
    explicit LLM regeneration is required.
    """

    def __init__(
        self,
        message: str,
        issues: list["ValidationIssue"] | None = None,
    ) -> None:
        super().__init__(message)
        self.issues = issues or []


class SchemaValidationError(ValidationError):
    """Exception raised when content violates a schema.

    This is a specialized ValidationError for schema-specific violations.
    """

    def __init__(
        self,
        message: str,
        schema_path: str | None = None,
        issues: list["ValidationIssue"] | None = None,
    ) -> None:
        super().__init__(message, issues)
        self.schema_path = schema_path
