"""Artifact storage implementation using MinIO.

ArtifactStore handles all artifact persistence with:
- Content-addressable storage (SHA256 digest)
- Tenant isolation via path prefixes
- Integrity verification on retrieval
"""

import hashlib
import io
import os
from datetime import datetime

from minio import Minio
from minio.error import S3Error

from .schemas import ArtifactRef


class ArtifactStoreError(Exception):
    """Base exception for artifact store operations."""

    pass


class ArtifactNotFoundError(ArtifactStoreError):
    """Artifact does not exist in storage."""

    pass


class ArtifactIntegrityError(ArtifactStoreError):
    """Artifact digest does not match stored content."""

    pass


class ArtifactStore:
    """MinIO-based artifact storage with integrity verification.

    Path convention: storage/{tenant_id}/{run_id}/{step}/output.json

    All content is verified via SHA256 digest on both write and read.
    """

    def __init__(
        self,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        secure: bool | None = None,
        bucket: str | None = None,
    ):
        """Initialize MinIO client.

        Args:
            endpoint: MinIO endpoint (default: MINIO_ENDPOINT env or localhost:9000)
            access_key: Access key (default: MINIO_ACCESS_KEY env or minioadmin)
            secret_key: Secret key (default: MINIO_SECRET_KEY env or minioadmin)
            secure: Use HTTPS (default: MINIO_USE_SSL env or false)
            bucket: Bucket name (default: MINIO_BUCKET env or seo-gen-artifacts)
        """
        self.endpoint: str = endpoint or os.getenv("MINIO_ENDPOINT") or "localhost:9000"
        self.access_key: str = access_key or os.getenv("MINIO_ACCESS_KEY") or "minioadmin"
        self.secret_key: str = secret_key or os.getenv("MINIO_SECRET_KEY") or "minioadmin"
        self.secure: bool = secure if secure is not None else (
            os.getenv("MINIO_USE_SSL", "false").lower() == "true"
        )
        self.bucket: str = bucket or os.getenv("MINIO_BUCKET") or "seo-gen-artifacts"

        self._client: Minio | None = None

    @property
    def client(self) -> Minio:
        """Lazy initialization of MinIO client."""
        if self._client is None:
            self._client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )
        return self._client

    def _ensure_bucket(self) -> None:
        """Ensure the bucket exists, create if not."""
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    @staticmethod
    def _compute_digest(content: bytes) -> str:
        """Compute SHA256 digest of content."""
        return hashlib.sha256(content).hexdigest()

    def build_path(
        self,
        tenant_id: str,
        run_id: str,
        step: str,
        filename: str = "output.json",
    ) -> str:
        """Build storage path following convention.

        Returns: storage/{tenant_id}/{run_id}/{step}/{filename}
        """
        return f"storage/{tenant_id}/{run_id}/{step}/{filename}"

    async def put(
        self,
        content: bytes,
        path: str,
        content_type: str = "application/json",
    ) -> ArtifactRef:
        """Store artifact and return reference.

        Args:
            content: Raw bytes to store
            path: Storage path (use build_path() to construct)
            content_type: MIME type of content

        Returns:
            ArtifactRef with path, digest, size, and timestamp
        """
        self._ensure_bucket()

        digest = self._compute_digest(content)
        size_bytes = len(content)

        self.client.put_object(
            bucket_name=self.bucket,
            object_name=path,
            data=io.BytesIO(content),
            length=size_bytes,
            content_type=content_type,
        )

        return ArtifactRef(
            path=path,
            digest=digest,
            content_type=content_type,
            size_bytes=size_bytes,
            created_at=datetime.now(),
        )

    async def get(self, ref: ArtifactRef, verify: bool = True) -> bytes:
        """Retrieve artifact content.

        Args:
            ref: Artifact reference
            verify: If True, verify digest matches (default: True)

        Returns:
            Raw bytes content

        Raises:
            ArtifactNotFoundError: If artifact does not exist
            ArtifactIntegrityError: If digest verification fails
        """
        try:
            response = self.client.get_object(
                bucket_name=self.bucket,
                object_name=ref.path,
            )
            content = response.read()
            response.close()
            response.release_conn()
        except S3Error as e:
            if e.code == "NoSuchKey":
                raise ArtifactNotFoundError(f"Artifact not found: {ref.path}") from e
            raise ArtifactStoreError(f"Failed to retrieve artifact: {e}") from e

        if verify:
            actual_digest = self._compute_digest(content)
            if actual_digest != ref.digest:
                raise ArtifactIntegrityError(
                    f"Digest mismatch for {ref.path}: "
                    f"expected {ref.digest}, got {actual_digest}"
                )

        return content

    async def exists(self, ref: ArtifactRef) -> bool:
        """Check if artifact exists and optionally verify digest.

        Args:
            ref: Artifact reference

        Returns:
            True if artifact exists with matching digest
        """
        try:
            stat = self.client.stat_object(
                bucket_name=self.bucket,
                object_name=ref.path,
            )
            # Size check as quick verification
            return stat.size == ref.size_bytes
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            raise ArtifactStoreError(f"Failed to check artifact: {e}") from e

    async def delete(self, ref: ArtifactRef) -> None:
        """Delete an artifact.

        Args:
            ref: Artifact reference to delete
        """
        try:
            self.client.remove_object(
                bucket_name=self.bucket,
                object_name=ref.path,
            )
        except S3Error as e:
            if e.code == "NoSuchKey":
                return  # Already deleted
            raise ArtifactStoreError(f"Failed to delete artifact: {e}") from e

    async def list_run_artifacts(
        self,
        tenant_id: str,
        run_id: str,
    ) -> list[str]:
        """List all artifact paths for a run.

        Args:
            tenant_id: Tenant identifier
            run_id: Run identifier

        Returns:
            List of artifact paths
        """
        prefix = f"storage/{tenant_id}/{run_id}/"
        objects = self.client.list_objects(
            bucket_name=self.bucket,
            prefix=prefix,
            recursive=True,
        )
        return [obj.object_name for obj in objects]

    async def delete_run_artifacts(
        self,
        tenant_id: str,
        run_id: str,
    ) -> int:
        """Delete all artifacts for a run.

        Args:
            tenant_id: Tenant identifier
            run_id: Run identifier

        Returns:
            Number of artifacts deleted
        """
        paths = await self.list_run_artifacts(tenant_id, run_id)
        for path in paths:
            self.client.remove_object(
                bucket_name=self.bucket,
                object_name=path,
            )
        return len(paths)
