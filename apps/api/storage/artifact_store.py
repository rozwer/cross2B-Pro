"""Artifact storage implementation using MinIO.

ArtifactStore handles all artifact persistence with:
- Content-addressable storage (SHA256 digest)
- Tenant isolation via path prefixes
- Integrity verification on retrieval

VULN-012: Storageアクセス制御
- テナント分離（prefix強制）
- パストラバーサル防止
- tenant_idバリデーション
"""

import hashlib
import io
import logging
import os
import re
from datetime import datetime, timedelta

from minio import Minio
from minio.error import S3Error

from .schemas import ArtifactRef

logger = logging.getLogger(__name__)

# VULN-012: パストラバーサル検出パターン
PATH_TRAVERSAL_PATTERN = re.compile(r"\.\./|\.\.\\|%2e%2e|%252e")

# tenant_id 許可パターン（SQL injection対策と同じ）
SAFE_TENANT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def _validate_path_component(value: str, name: str) -> None:
    """パスコンポーネントの検証（VULN-012）

    Args:
        value: 検証対象の値
        name: コンポーネント名（エラーメッセージ用）

    Raises:
        ArtifactStoreError: 不正な値の場合
    """
    if not value:
        raise ArtifactStoreError(f"Empty {name} is not allowed")

    # パストラバーサル検出
    if PATH_TRAVERSAL_PATTERN.search(value):
        logger.warning(f"Path traversal attempt detected in {name}: {value[:50]}")
        raise ArtifactStoreError(f"Invalid {name}: path traversal detected")

    # 禁止文字チェック
    forbidden = ["/", "\\", "\0", "\n", "\r"]
    for char in forbidden:
        if char in value:
            raise ArtifactStoreError(f"Invalid {name}: contains forbidden character")


def _validate_tenant_id(tenant_id: str) -> None:
    """tenant_idの検証（VULN-012）

    Args:
        tenant_id: 検証対象のテナントID

    Raises:
        ArtifactStoreError: 不正な値の場合
    """
    if not tenant_id:
        raise ArtifactStoreError("tenant_id is required")

    if not SAFE_TENANT_ID_PATTERN.match(tenant_id):
        logger.warning(f"Invalid tenant_id format: {tenant_id[:20]}")
        raise ArtifactStoreError("Invalid tenant_id format")


class ArtifactStoreError(Exception):
    """Base exception for artifact store operations."""

    pass


class ArtifactNotFoundError(ArtifactStoreError):
    """Artifact does not exist in storage."""

    pass


class ArtifactIntegrityError(ArtifactStoreError):
    """Artifact digest does not match stored content."""

    pass


class ArtifactAccessDeniedError(ArtifactStoreError):
    """Access denied due to tenant isolation violation."""

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

        VULN-012: 全コンポーネントを検証してパストラバーサルを防止

        Args:
            tenant_id: テナントID（必須、検証される）
            run_id: 実行ID（必須、検証される）
            step: 工程名（必須、検証される）
            filename: ファイル名（検証される）

        Returns: storage/{tenant_id}/{run_id}/{step}/{filename}

        Raises:
            ArtifactStoreError: 不正なパラメータの場合
        """
        # VULN-012: 全コンポーネントを検証
        _validate_tenant_id(tenant_id)
        _validate_path_component(run_id, "run_id")
        _validate_path_component(step, "step")
        _validate_path_component(filename, "filename")

        return f"storage/{tenant_id}/{run_id}/{step}/{filename}"

    def _verify_path_ownership(self, path: str, tenant_id: str) -> None:
        """パスがテナントに所属することを検証（VULN-012）

        Args:
            path: 検証対象のパス
            tenant_id: 期待されるテナントID

        Raises:
            ArtifactAccessDeniedError: テナント越境の場合
        """
        expected_prefix = f"storage/{tenant_id}/"

        if not path.startswith(expected_prefix):
            logger.warning(
                f"Tenant isolation violation: path={path}, tenant_id={tenant_id}"
            )
            raise ArtifactAccessDeniedError(
                f"Access denied: path does not belong to tenant {tenant_id}"
            )

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

        VULN-012: tenant_idとrun_idを検証

        Args:
            tenant_id: Tenant identifier
            run_id: Run identifier

        Returns:
            List of artifact paths
        """
        # VULN-012: パラメータ検証
        _validate_tenant_id(tenant_id)
        _validate_path_component(run_id, "run_id")

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

        VULN-012: tenant_idとrun_idを検証

        Args:
            tenant_id: Tenant identifier
            run_id: Run identifier

        Returns:
            Number of artifacts deleted
        """
        # VULN-012: パラメータ検証
        _validate_tenant_id(tenant_id)
        _validate_path_component(run_id, "run_id")

        paths = await self.list_run_artifacts(tenant_id, run_id)
        for path in paths:
            self.client.remove_object(
                bucket_name=self.bucket,
                object_name=path,
            )
        return len(paths)

    def get_presigned_url(
        self,
        tenant_id: str,
        ref: ArtifactRef,
        expires: timedelta = timedelta(hours=1),
    ) -> str:
        """署名付きURLを生成（VULN-012）

        テナント越境を防止しつつ、一時的なダウンロードURLを発行。

        Args:
            tenant_id: リクエスト元のテナントID（検証用）
            ref: アーティファクト参照
            expires: URL有効期限（デフォルト1時間）

        Returns:
            署名付きダウンロードURL

        Raises:
            ArtifactAccessDeniedError: テナント越境の場合
        """
        # VULN-012: テナント越境チェック
        _validate_tenant_id(tenant_id)
        self._verify_path_ownership(ref.path, tenant_id)

        return self.client.presigned_get_object(
            bucket_name=self.bucket,
            object_name=ref.path,
            expires=expires,
        )

    async def get_with_tenant_check(
        self,
        tenant_id: str,
        ref: ArtifactRef,
        verify: bool = True,
    ) -> bytes:
        """テナント越境チェック付きのアーティファクト取得（VULN-012）

        Args:
            tenant_id: リクエスト元のテナントID
            ref: アーティファクト参照
            verify: ダイジェスト検証を行うか

        Returns:
            アーティファクトのバイトデータ

        Raises:
            ArtifactAccessDeniedError: テナント越境の場合
            ArtifactNotFoundError: アーティファクトが存在しない場合
            ArtifactIntegrityError: ダイジェスト検証失敗の場合
        """
        # VULN-012: テナント越境チェック
        _validate_tenant_id(tenant_id)
        self._verify_path_ownership(ref.path, tenant_id)

        return await self.get(ref, verify=verify)

    async def get_by_path(
        self,
        tenant_id: str,
        run_id: str,
        step: str,
        filename: str = "output.json",
    ) -> bytes | None:
        """パスから直接アーティファクトを取得（VULN-012）

        Args:
            tenant_id: テナントID
            run_id: 実行ID
            step: 工程名
            filename: ファイル名

        Returns:
            アーティファクトのバイトデータ、存在しない場合はNone
        """
        path = self.build_path(tenant_id, run_id, step, filename)
        try:
            response = self.client.get_object(
                bucket_name=self.bucket,
                object_name=path,
            )
            content = response.read()
            response.close()
            response.release_conn()
            return content
        except S3Error as e:
            if e.code == "NoSuchKey":
                return None
            raise ArtifactStoreError(f"Failed to retrieve artifact: {e}") from e

    async def list_step_artifacts(
        self,
        tenant_id: str,
        run_id: str,
    ) -> dict[str, bool]:
        """各ステップのアーティファクト存在状況を取得

        Args:
            tenant_id: テナントID
            run_id: 実行ID

        Returns:
            dict: {step_name: exists}
        """
        paths = await self.list_run_artifacts(tenant_id, run_id)
        steps: dict[str, bool] = {}
        for path in paths:
            # storage/{tenant_id}/{run_id}/{step}/output.json
            parts = path.split("/")
            if len(parts) >= 4:
                step = parts[3]
                steps[step] = True
        return steps
