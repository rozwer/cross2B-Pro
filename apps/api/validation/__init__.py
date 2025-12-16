# Validation Module
# JSON/CSV validation with deterministic repair support

from .base import ValidatorInterface
from .csv_validator import CsvValidator
from .exceptions import (
    RepairError,
    SchemaValidationError,
    UnrepairableError,
    ValidationError,
)
from .json_validator import JsonValidator
from .repairer import Repairer
from .schemas import (
    RepairAction,
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
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
