"""Base interface for validators."""

from abc import ABC, abstractmethod
from typing import Any

from .schemas import ValidationReport


class ValidatorInterface(ABC):
    """Abstract base class for content validators.

    All validators must implement this interface to ensure consistent
    validation behavior across different formats.
    """

    @abstractmethod
    def validate(self, content: str | bytes) -> ValidationReport:
        """Validate content without schema constraints.

        Args:
            content: The content to validate (string or bytes).

        Returns:
            ValidationReport: A report containing validation results,
                including any issues found.
        """
        pass

    @abstractmethod
    def validate_with_schema(
        self,
        content: str | bytes,
        schema: dict[str, Any],
    ) -> ValidationReport:
        """Validate content against a schema.

        Args:
            content: The content to validate (string or bytes).
            schema: The schema to validate against (format-specific).

        Returns:
            ValidationReport: A report containing validation results,
                including any schema violations.
        """
        pass
