"""Storage schemas for artifact references.

ArtifactRef is the contract for referencing stored content.
Only path/digest references are passed in workflow state - never raw content.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ArtifactRef(BaseModel):
    """Reference to an artifact stored in object storage.

    Path format: storage/{tenant_id}/{run_id}/{step}/output.json

    This is the only way to reference content in workflow state.
    Raw content must never be stored in Temporal history or LangGraph state.
    """

    path: str = Field(
        ...,
        description="Storage path: storage/{tenant_id}/{run_id}/{step}/output.json",
    )
    digest: str = Field(
        ...,
        description="SHA256 hash for integrity verification",
    )
    content_type: str = Field(
        default="application/json",
        description="MIME type of the content",
    )
    size_bytes: int = Field(
        ...,
        ge=0,
        description="Size of the content in bytes",
    )
    created_at: datetime = Field(
        ...,
        description="When the artifact was created",
    )

    def get_step(self) -> str:
        """Extract step name from path."""
        parts = self.path.split("/")
        if len(parts) >= 4:
            step = parts[3]
            if not step:
                raise ValueError(f"Empty step name in artifact path: {self.path}")
            return step
        raise ValueError(f"Invalid artifact path format: {self.path}")

    def get_run_id(self) -> str:
        """Extract run_id from path."""
        parts = self.path.split("/")
        if len(parts) >= 3:
            run_id = parts[2]
            if not run_id:
                raise ValueError(f"Empty run_id in artifact path: {self.path}")
            return run_id
        raise ValueError(f"Invalid artifact path format: {self.path}")

    def get_tenant_id(self) -> str:
        """Extract tenant_id from path."""
        parts = self.path.split("/")
        if len(parts) >= 2:
            tenant_id = parts[1]
            if not tenant_id:
                raise ValueError(f"Empty tenant_id in artifact path: {self.path}")
            return tenant_id
        raise ValueError(f"Invalid artifact path format: {self.path}")


class ArtifactMetrics(BaseModel):
    """Metrics associated with an artifact (for UI/logging)."""

    token_usage: dict[str, int] | None = Field(
        default=None,
        description="LLM token usage: {'input': N, 'output': M}",
    )
    char_count: int | None = Field(
        default=None,
        description="Character count of the content",
    )
    processing_time_ms: int | None = Field(
        default=None,
        description="Processing time in milliseconds",
    )
