"""SQLAlchemy models for common and tenant databases.

Common DB: tenants, llm_providers, llm_models, step_llm_defaults
Tenant DB: runs, steps, artifacts, audit_logs, prompts
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# =============================================================================
# Base Classes
# =============================================================================


class CommonBase(DeclarativeBase):
    """Base class for common management DB models."""

    pass


class Base(DeclarativeBase):
    """Base class for tenant DB models."""

    pass


# =============================================================================
# Common Management DB Models
# =============================================================================


class Tenant(CommonBase):
    """Tenant management - tracks all customer databases."""

    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    database_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class LLMProvider(CommonBase):
    """LLM provider configuration."""

    __tablename__ = "llm_providers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # claude, gemini, openai
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    api_base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    models: Mapped[list["LLMModel"]] = relationship(back_populates="provider")


class LLMModel(CommonBase):
    """LLM model configuration with cost tracking."""

    __tablename__ = "llm_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("llm_providers.id"), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_class: Mapped[str] = mapped_column(String(32), nullable=False)  # pro, standard
    cost_per_1k_input_tokens: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6), nullable=True
    )
    cost_per_1k_output_tokens: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    provider: Mapped["LLMProvider"] = relationship(back_populates="models")


class StepLLMDefault(CommonBase):
    """Default LLM configuration per workflow step."""

    __tablename__ = "step_llm_defaults"

    step: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("llm_providers.id"), nullable=False
    )
    model_class: Mapped[str] = mapped_column(String(32), nullable=False)


# =============================================================================
# Tenant DB Models
# =============================================================================


class Run(Base):
    """Workflow execution record."""

    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
    )
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # マルチテナント分離必須
    status: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # pending, running, waiting_approval, completed, failed, cancelled
    current_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )  # 元入力データ保存
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    steps: Mapped[list["Step"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    artifacts: Mapped[list["Artifact"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class Step(Base):
    """Step execution log within a run.

    NOTE: Matches init-db.sql schema:
    - id: UUID (not Integer)
    - step_name: VARCHAR(100) (not 'step')
    """

    __tablename__ = "steps"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default="uuid_generate_v4()"
    )
    run_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("runs.id"), nullable=False
    )
    step_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    run: Mapped["Run"] = relationship(back_populates="steps")


class Artifact(Base):
    """Generated file reference.

    NOTE: Matches init-db.sql schema:
    - id: UUID (not Integer)
    - step_id: UUID FK to steps (optional)
    - artifact_type: VARCHAR(100)
    - ref_path: TEXT
    - content_type: VARCHAR(100)
    """

    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default="uuid_generate_v4()"
    )
    run_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("runs.id"), nullable=False
    )
    step_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("steps.id", ondelete="SET NULL"), nullable=True
    )
    artifact_type: Mapped[str] = mapped_column(String(100), nullable=False)
    ref_path: Mapped[str] = mapped_column(Text, nullable=False)
    digest: Mapped[str] = mapped_column(String(64), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )

    run: Mapped["Run"] = relationship(back_populates="artifacts")


class AuditLog(Base):
    """Immutable audit log with chain hash (UPDATE/DELETE prohibited via trigger).

    VULN-011: 監査ログの完全性保証
    - prev_hash: 前のログエントリーのハッシュ（チェーンハッシュ）
    - entry_hash: このエントリーのハッシュ（改ざん検知用）
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    # VULN-011: チェーンハッシュ
    prev_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )  # 最初のエントリはNone
    entry_hash: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # SHA256 of entry content


class Prompt(Base):
    """Versioned prompts for workflow steps."""

    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    step: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("step", "version", name="uq_prompt_step_version"),)
