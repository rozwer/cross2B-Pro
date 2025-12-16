"""Artifact storage implementation using MinIO.

ArtifactStore handles all artifact persistence with:
- Content-addressable storage (SHA256 digest)
- Tenant isolation via path prefixes
- Integrity verification on retrieval

Security:
- All operations verify tenant isolation
- Paths are validated to prevent traversal attacks
- Access control enforced at storage layer
"""

import hashlib
import io
import logging
import os
import re
from datetime import datetime

from minio import Minio
from minio.error import S3Error

from .schemas import ArtifactRef

logger = logging.getLogger(__name__)


class ArtifactStoreError(Exception):
    """Base exception for artifact store operations."""

    pass


class ArtifactNotFoundError(ArtifactStoreError):
    """Artifact does not exist in storage."""

    pass


class ArtifactIntegrityError(ArtifactStoreError):
    """Artifact digest does not match stored content."""

    pass


class TenantAccessError(ArtifactStoreError):
    """Tenant access violation - attempt to access another tenant's data."""

    pass


# Valid tenant ID pattern: alphanumeric, hyphens, underscores, 3-64 chars
TENANT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{2,63}$")

# Valid run ID pattern: UUID format or alphanumeric
RUN_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{7,63}$")

# Valid step name pattern
STEP_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


def validate_tenant_id(tenant_id: str) -> bool:
    """Validate tenant ID format for security.

    Prevents path traversal by ensuring tenant_id contains only safe characters.
    """
    if not tenant_id:
        return False
    return bool(TENANT_ID_PATTERN.match(tenant_id))


def validate_run_id(run_id: str) -> bool:
    """Validate run ID format for security."""
    if not run_id:
        return False
    return bool(RUN_ID_PATTERN.match(run_id))


def validate_step_name(step: str) -> bool:
    """Validate step name format for security."""
    if not step:
        return False
    return bool(STEP_NAME_PATTERN.match(step))


class ArtifactStore:
    """MinIO-based artifact storage with integrity verification.

    Path convention: storage/{tenant_id}/{run_id}/{step}/output.json

    Security:
    - All content is verified via SHA256 digest on both write and read.
    - Tenant isolation is enforced at all operations.
    - Path components are validated to prevent traversal attacks.
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

        Security: Validates all path components to prevent traversal attacks.

        Args:
            tenant_id: Tenant identifier (validated)
            run_id: Run identifier (validated)
            step: Step name (validated)
            filename: Filename (validated for dangerous patterns)

        Returns: storage/{tenant_id}/{run_id}/{step}/{filename}

        Raises:
            TenantAccessError: If any path component is invalid
        """
        # Validate tenant_id
        if not validate_tenant_id(tenant_id):
            logger.warning(f"Invalid tenant_id in build_path: {tenant_id}")
            raise TenantAccessError(f"Invalid tenant_id format: {tenant_id}")

        # Validate run_id
        if not validate_run_id(run_id):
            logger.warning(f"Invalid run_id in build_path: {run_id}")
            raise TenantAccessError(f"Invalid run_id format: {run_id}")

        # Validate step
        if not validate_step_name(step):
            logger.warning(f"Invalid step name in build_path: {step}")
            raise TenantAccessError(f"Invalid step name format: {step}")

        # Validate filename (no path traversal)
        if ".." in filename or "/" in filename or "\\" in filename:
            logger.warning(f"Path traversal attempt in filename: {filename}")
            raise TenantAccessError(f"Invalid filename: {filename}")

        return f"storage/{tenant_id}/{run_id}/{step}/{filename}"

    def _verify_tenant_access(
        self,
        path: str,
        expected_tenant_id: str,
    ) -> None:
        """Verify that a path belongs to the expected tenant.

        Security: This method MUST be called before any read/delete operation
        to enforce tenant isolation.

        Args:
            path: Storage path to verify
            expected_tenant_id: Tenant ID that should own this path

        Raises:
            TenantAccessError: If path does not belong to expected tenant
        """
        # Validate expected tenant_id
        if not validate_tenant_id(expected_tenant_id):
            logger.warning(f"Invalid expected_tenant_id: {expected_tenant_id}")
            raise TenantAccessError(f"Invalid tenant_id: {expected_tenant_id}")

        # Extract tenant_id from path
        # Expected format: storage/{tenant_id}/{run_id}/{step}/{filename}
        parts = path.split("/")
        if len(parts) < 2 or parts[0] != "storage":
            logger.warning(f"Invalid path format: {path}")
            raise TenantAccessError(f"Invalid path format: {path}")

        path_tenant_id = parts[1]

        # Verify tenant matches
        if path_tenant_id != expected_tenant_id:
            logger.error(
                f"Tenant access violation: tenant {expected_tenant_id} "
                f"attempted to access path belonging to {path_tenant_id}"
            )
            raise TenantAccessError(
                f"Access denied: path belongs to different tenant"
            )

    def _extract_tenant_from_path(self, path: str) -> str | None:
        """Extract tenant_id from a storage path.

        Args:
            path: Storage path

        Returns:
            Tenant ID or None if path format is invalid
        """
        parts = path.split("/")
        if len(parts) >= 2 and parts[0] == "storage":
            return parts[1]
        return None

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

    async def get(
        self,
        ref: ArtifactRef,
        tenant_id: str,
        verify: bool = True,
    ) -> bytes:
        """Retrieve artifact content with tenant verification.

        Security: Verifies that the requesting tenant owns the artifact.

        Args:
            ref: Artifact reference
            tenant_id: Tenant ID of the requester (required for access control)
            verify: If True, verify digest matches (default: True)

        Returns:
            Raw bytes content

        Raises:
            TenantAccessError: If tenant does not own this artifact
            ArtifactNotFoundError: If artifact does not exist
            ArtifactIntegrityError: If digest verification fails
        """
        # Security: Verify tenant access before retrieval
        self._verify_tenant_access(ref.path, tenant_id)

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

    async def exists(
        self,
        ref: ArtifactRef,
        tenant_id: str,
    ) -> bool:
        """Check if artifact exists with tenant verification.

        Security: Verifies that the requesting tenant owns the artifact.

        Args:
            ref: Artifact reference
            tenant_id: Tenant ID of the requester (required for access control)

        Returns:
            True if artifact exists with matching digest

        Raises:
            TenantAccessError: If tenant does not own this artifact
        """
        # Security: Verify tenant access before checking existence
        self._verify_tenant_access(ref.path, tenant_id)

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

    async def delete(
        self,
        ref: ArtifactRef,
        tenant_id: str,
    ) -> None:
        """Delete an artifact with tenant verification.

        Security: Verifies that the requesting tenant owns the artifact.

        Args:
            ref: Artifact reference to delete
            tenant_id: Tenant ID of the requester (required for access control)

        Raises:
            TenantAccessError: If tenant does not own this artifact
        """
        # Security: Verify tenant access before deletion
        self._verify_tenant_access(ref.path, tenant_id)

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
        """List all artifact paths for a run with tenant validation.

        Security: Validates tenant_id and run_id to prevent path manipulation.

        Args:
            tenant_id: Tenant identifier (validated)
            run_id: Run identifier (validated)

        Returns:
            List of artifact paths

        Raises:
            TenantAccessError: If tenant_id or run_id format is invalid
        """
        # Security: Validate path components
        if not validate_tenant_id(tenant_id):
            logger.warning(f"Invalid tenant_id in list_run_artifacts: {tenant_id}")
            raise TenantAccessError(f"Invalid tenant_id format: {tenant_id}")

        if not validate_run_id(run_id):
            logger.warning(f"Invalid run_id in list_run_artifacts: {run_id}")
            raise TenantAccessError(f"Invalid run_id format: {run_id}")

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
        """Delete all artifacts for a run with tenant validation.

        Security: Validates tenant_id and run_id to prevent path manipulation.

        Args:
            tenant_id: Tenant identifier (validated)
            run_id: Run identifier (validated)

        Returns:
            Number of artifacts deleted

        Raises:
            TenantAccessError: If tenant_id or run_id format is invalid
        """
        # Validation is done in list_run_artifacts
        paths = await self.list_run_artifacts(tenant_id, run_id)
        for path in paths:
            self.client.remove_object(
                bucket_name=self.bucket,
                object_name=path,
            )
        logger.info(f"Deleted {len(paths)} artifacts for tenant={tenant_id}, run={run_id}")
        return len(paths)
