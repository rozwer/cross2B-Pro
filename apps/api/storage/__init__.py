"""Storage module for artifact management.

This module provides:
- ArtifactRef: Reference to stored artifacts (path + digest)
- ArtifactStore: MinIO-based artifact storage with tenant isolation

Security:
- All operations enforce tenant isolation
- Path validation prevents traversal attacks
- TenantAccessError raised on access violations
"""

from .artifact_store import (
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    ArtifactStore,
    ArtifactStoreError,
    TenantAccessError,
)
from .schemas import ArtifactRef

__all__ = [
    "ArtifactRef",
    "ArtifactStore",
    "ArtifactStoreError",
    "ArtifactNotFoundError",
    "ArtifactIntegrityError",
    "TenantAccessError",
]
