"""Storage module for artifact management.

This module provides:
- ArtifactRef: Reference to stored artifacts (path + digest)
- ArtifactStore: MinIO-based artifact storage
"""

from .artifact_store import ArtifactStore
from .schemas import ArtifactRef

__all__ = [
    "ArtifactRef",
    "ArtifactStore",
]
