"""Checkpoint management for activity-level idempotency.

CheckpointManager enables saving/loading intermediate state within activities
for efficient re-execution and idempotency:
- Save checkpoints with input digest for verification
- Load checkpoints with digest matching
- Clear checkpoints for retry scenarios
"""

import hashlib
import json
from datetime import datetime
from typing import Any

from apps.api.storage.artifact_store import ArtifactStore


class CheckpointManager:
    """Activity-level checkpoint management."""

    def __init__(self, store: ArtifactStore):
        """
        Args:
            store: Storage instance
        """
        self.store = store

    async def save(
        self,
        tenant_id: str,
        run_id: str,
        step_id: str,
        phase: str,
        data: dict[str, Any],
        input_digest: str | None = None,
    ) -> str:
        """
        Save a checkpoint.

        Args:
            tenant_id: Tenant ID
            run_id: Run ID
            step_id: Step ID
            phase: Phase name (e.g., "queries_generated", "html_generated")
            data: Data to save
            input_digest: Input digest (for idempotency check)

        Returns:
            str: Storage path

        Storage format:
            {
                "_metadata": {
                    "phase": "...",
                    "created_at": "...",
                    "input_digest": "...",
                    "step_id": "..."
                },
                "data": { ... }
            }

        Storage path:
            storage/{tenant_id}/{run_id}/{step_id}/checkpoint_{phase}.json
        """
        # Build filename as checkpoint_{phase}.json to avoid slash in step parameter
        checkpoint_filename = f"checkpoint_{phase}.json"
        path = f"storage/{tenant_id}/{run_id}/{step_id}/{checkpoint_filename}"

        checkpoint = {
            "_metadata": {
                "phase": phase,
                "created_at": datetime.utcnow().isoformat(),
                "input_digest": input_digest,
                "step_id": step_id,
            },
            "data": data,
        }

        content = json.dumps(checkpoint, ensure_ascii=False, default=str)
        content_bytes = content.encode("utf-8")

        await self.store.put(
            content=content_bytes,
            path=path,
            content_type="application/json",
        )

        return path

    async def load(
        self,
        tenant_id: str,
        run_id: str,
        step_id: str,
        phase: str,
        input_digest: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Load a checkpoint.

        Args:
            tenant_id: Tenant ID
            run_id: Run ID
            step_id: Step ID
            phase: Phase name
            input_digest: Input digest (if specified, must match)

        Returns:
            dict | None: Saved data, or None if not found or digest mismatch

        Idempotency logic:
            1. Check if checkpoint exists
            2. If input_digest is specified and differs from saved, return None
            3. If match or not specified, return data

        Storage path:
            storage/{tenant_id}/{run_id}/{step_id}/checkpoint_{phase}.json
        """
        # Use checkpoint_{phase}.json filename to avoid slash in step parameter
        checkpoint_filename = f"checkpoint_{phase}.json"
        raw_content = await self.store.get_by_path(
            tenant_id, run_id, step_id, checkpoint_filename
        )

        if raw_content is None:
            return None

        try:
            checkpoint = json.loads(raw_content.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

        metadata = checkpoint.get("_metadata", {})

        # Verify input digest if specified
        if input_digest is not None:
            stored_digest = metadata.get("input_digest")
            if stored_digest is not None and stored_digest != input_digest:
                return None

        data = checkpoint.get("data")
        if data is None:
            return None
        return dict(data) if isinstance(data, dict) else None

    async def exists(
        self,
        tenant_id: str,
        run_id: str,
        step_id: str,
        phase: str,
    ) -> bool:
        """
        Check if checkpoint exists.

        Returns:
            bool: True if exists
        """
        # Use checkpoint_{phase}.json filename to avoid slash in step parameter
        checkpoint_filename = f"checkpoint_{phase}.json"
        raw_content = await self.store.get_by_path(
            tenant_id, run_id, step_id, checkpoint_filename
        )
        return raw_content is not None

    async def clear(
        self,
        tenant_id: str,
        run_id: str,
        step_id: str,
        phase: str | None = None,
    ) -> None:
        """
        Clear checkpoints.

        Args:
            phase: If specified, clear only that phase; otherwise clear all phases

        Storage path format:
            storage/{tenant_id}/{run_id}/{step_id}/checkpoint_{phase}.json
        """
        # List all checkpoint artifacts for this step
        paths = await self.store.list_run_artifacts(tenant_id, run_id)

        # Match checkpoint files: storage/{tenant}/{run}/{step}/checkpoint_{phase}.json
        checkpoint_prefix = f"storage/{tenant_id}/{run_id}/{step_id}/checkpoint_"

        for path in paths:
            if path.startswith(checkpoint_prefix):
                if phase is None or path.endswith(f"checkpoint_{phase}.json"):
                    from apps.api.storage.schemas import ArtifactRef

                    ref = ArtifactRef(
                        path=path,
                        digest="",  # Not needed for delete
                        content_type="application/json",
                        size_bytes=0,
                        created_at=datetime.utcnow(),
                    )
                    await self.store.delete(ref)

    def build_path(
        self,
        tenant_id: str,
        run_id: str,
        step_id: str,
        phase: str,
    ) -> str:
        """
        Build checkpoint path.

        Returns:
            str: "storage/{tenant_id}/{run_id}/{step_id}/checkpoint_{phase}.json"
        """
        return f"storage/{tenant_id}/{run_id}/{step_id}/checkpoint_{phase}.json"

    @staticmethod
    def compute_digest(data: Any) -> str:
        """
        Compute data digest.

        Args:
            data: JSON-serializable data

        Returns:
            str: SHA256 digest (hex)
        """
        content = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
