"""Database module for SEO article generation system.

This module provides:
- SQLAlchemy models for common DB and tenant DBs
- TenantDBManager for multi-tenant database connections
- Alembic migrations support
"""

from .audit import AuditLogger, AuditLogIntegrityError
from .models import (
    Artifact,
    AuditLog,
    Base,
    CommonBase,
    LLMModel,
    LLMProvider,
    Prompt,
    Run,
    Step,
    StepLLMDefault,
    Tenant,
)
from .tenant import TenantDBManager, TenantIdValidationError, validate_tenant_id

__all__ = [
    # Base classes
    "Base",
    "CommonBase",
    # Common DB models
    "Tenant",
    "LLMProvider",
    "LLMModel",
    "StepLLMDefault",
    # Tenant DB models
    "Run",
    "Step",
    "Artifact",
    "AuditLog",
    "Prompt",
    # Manager
    "TenantDBManager",
    # Audit (VULN-011)
    "AuditLogger",
    "AuditLogIntegrityError",
    # Validation (VULN-004)
    "validate_tenant_id",
    "TenantIdValidationError",
]
