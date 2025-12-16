# Validation Module
# JSON/CSV validation with deterministic repair support

from .schemas import (
    ValidationSeverity,
    ValidationIssue,
    RepairAction,
    ValidationReport,
)
from .base import ValidatorInterface
from .json_validator import JsonValidator
from .csv_validator import CsvValidator
from .repairer import Repairer
from .exceptions import (
    ValidationError,
    RepairError,
    UnrepairableError,
    SchemaValidationError,
)

__all__ = [
    # Schemas
    "ValidationSeverity",
    "ValidationIssue",
    "RepairAction",
    "ValidationReport",
    # Validators
    "ValidatorInterface",
    "JsonValidator",
    "CsvValidator",
    # Repairer
    "Repairer",
    # Exceptions
    "ValidationError",
    "RepairError",
    "UnrepairableError",
    "SchemaValidationError",
]
