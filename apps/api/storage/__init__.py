"""Storage module for artifact management.

This module provides:
- ArtifactRef: Reference to stored artifacts (path + digest)
- ArtifactStore: MinIO-based artifact storage with tenant isolation

VULN-012: Storageアクセス制御
- テナント分離（prefix強制）
- パストラバーサル防止
- 署名付きURL生成
"""

from .artifact_store import (
    ArtifactAccessDeniedError,
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    ArtifactStore,
    ArtifactStoreError,
)
from .schemas import ArtifactRef

__all__ = [
    "ArtifactRef",
    "ArtifactStore",
    # Exceptions
    "ArtifactStoreError",
    "ArtifactNotFoundError",
    "ArtifactIntegrityError",
    "ArtifactAccessDeniedError",
]
