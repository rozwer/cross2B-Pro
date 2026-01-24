"""SQLAlchemy models for common and tenant databases.

Common DB: tenants, llm_providers, llm_models, step_llm_defaults
Tenant DB: runs, steps, artifacts, audit_logs, prompts
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
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
    provider_id: Mapped[str] = mapped_column(String(32), ForeignKey("llm_providers.id"), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_class: Mapped[str] = mapped_column(String(32), nullable=False)  # pro, standard
    cost_per_1k_input_tokens: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    cost_per_1k_output_tokens: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    provider: Mapped["LLMProvider"] = relationship(back_populates="models")


class StepLLMDefault(CommonBase):
    """Default LLM configuration per workflow step."""

    __tablename__ = "step_llm_defaults"

    step: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider_id: Mapped[str] = mapped_column(String(32), ForeignKey("llm_providers.id"), nullable=False)
    model_class: Mapped[str] = mapped_column(String(32), nullable=False)


class HelpContent(CommonBase):
    """Context-sensitive help content for UI components.

    Stores help text (Markdown supported) that can be displayed in modal dialogs
    when users click the "?" help button throughout the application.

    help_key format: "{category}.{subcategory}.{item}"
    Examples:
    - "wizard.step1.business" - ワークフロー作成の事業情報入力
    - "workflow.step0" - 工程0（キーワード選定）の説明
    - "github.pr" - PR管理の使い方
    """

    __tablename__ = "help_contents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    help_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # Markdown supported
    category: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


# =============================================================================
# Tenant DB Models
# =============================================================================


class Run(Base):
    """Workflow execution record."""

    __tablename__ = "runs"
    __table_args__ = (
        # Composite index for tenant-scoped queries filtered by status
        Index("ix_runs_tenant_id_status", "tenant_id", "status"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # マルチテナント分離必須
    # Status: pending, workflow_starting, running, paused, waiting_approval,
    # waiting_step1_approval, waiting_image_input, completed, failed, cancelled
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    current_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # 元入力データ保存
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Step11 画像生成の状態を保持するJSON。詳細構造は apps.api.routers.step11.Step11State を参照。
    # フィールド: phase, settings, positions, instructions, images, analysis_summary, sections, error
    step11_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    # GitHub integration (Phase 2)
    github_repo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    github_dir_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    # GitHub Fix Guidance: resume後に同一ステップで再度失敗した場合にIssue作成へ誘導
    last_resumed_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fix_issue_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    steps: Mapped[list["Step"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    artifacts: Mapped[list["Artifact"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    error_logs: Mapped[list["ErrorLog"]] = relationship(back_populates="run", cascade="all, delete-orphan")
    diagnostic_reports: Mapped[list["DiagnosticReport"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class Step(Base):
    """Step execution log within a run.

    NOTE: Matches init-db.sql schema:
    - id: UUID (not Integer)
    - step_name: VARCHAR(100) (not 'step')
    """

    __tablename__ = "steps"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default="uuid_generate_v4()")
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("runs.id"), nullable=False, index=True)
    step_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)  # ErrorCategory enum value
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

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default="uuid_generate_v4()")
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("steps.id", ondelete="SET NULL"), nullable=True, index=True)
    artifact_type: Mapped[str] = mapped_column(String(100), nullable=False)
    ref_path: Mapped[str] = mapped_column(Text, nullable=False)
    digest: Mapped[str] = mapped_column(String(64), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, index=True)
    # VULN-011: チェーンハッシュ
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 最初のエントリはNone
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA256 of entry content


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


# =============================================================================
# Error Logging and Diagnostics Models
# =============================================================================


class ErrorLog(Base):
    """Detailed error log for diagnostics.

    Collects all errors within a run/session for LLM-based failure analysis.
    Supports multiple sources: llm, tool, validation, storage, activity, api.
    """

    __tablename__ = "error_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default="uuid_generate_v4()")
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("runs.id"), nullable=False, index=True)
    step_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("steps.id", ondelete="SET NULL"), nullable=True, index=True
    )  # References steps.id (UUID)
    source: Mapped[str] = mapped_column(
        String(32), nullable=False, default="activity", index=True
    )  # llm, tool, validation, storage, activity, api
    error_category: Mapped[str] = mapped_column(String(32), nullable=False)  # retryable, non_retryable, validation_fail
    error_type: Mapped[str] = mapped_column(String(128), nullable=False)  # Exception class name
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    stack_trace: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # LLM model, tool name, input params, etc.
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, index=True)

    run: Mapped["Run"] = relationship(back_populates="error_logs")


class DiagnosticReport(Base):
    """LLM-generated failure diagnosis and recovery recommendation.

    Generated when a run fails to help understand root cause and next steps.
    """

    __tablename__ = "diagnostic_reports"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default="uuid_generate_v4()")
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("runs.id"), nullable=False, index=True)
    # LLM diagnostics results
    root_cause_analysis: Mapped[str] = mapped_column(Text, nullable=False)  # LLM's analysis of failure cause
    recommended_actions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)  # Ordered list of recommended steps
    resume_step: Mapped[str | None] = mapped_column(String(64), nullable=True)  # Suggested step to resume from
    confidence_score: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)  # LLM's confidence (0.0-1.0)
    # LLM metadata
    llm_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    llm_model: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)

    run: Mapped["Run"] = relationship(back_populates="diagnostic_reports")


# =============================================================================
# Hearing Template Model
# =============================================================================


class HearingTemplate(Base):
    """Hearing template for reusable workflow input configurations.

    Stores ArticleHearingInput data (without confirmed field) as a template
    that can be loaded and reused for new workflow runs.

    VULN-004: tenant_id必須でテナント分離を保証
    """

    __tablename__ = "hearing_templates"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default="uuid_generate_v4()")
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # マルチテナント分離必須
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)  # HearingTemplateData as JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_hearing_template_tenant_name"),)


# =============================================================================
# API Settings Model
# =============================================================================


class ApiSetting(Base):
    """API/LLM settings per tenant per service.

    Stores API keys (encrypted) and configuration for external services.
    Supports: gemini, openai, anthropic, serp, google_ads, github
    """

    __tablename__ = "api_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    service: Mapped[str] = mapped_column(String(32), nullable=False)  # gemini, openai, anthropic, serp, google_ads, github
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)  # AES-256-GCM encrypted
    default_model: Mapped[str | None] = mapped_column(String(128), nullable=True)  # For LLM providers
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # Service-specific config (grounding, etc.)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # Last successful connection test
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "service", name="uq_api_setting_tenant_service"),
        Index("ix_api_settings_tenant_id", "tenant_id"),
    )


# =============================================================================
# Review Request Model
# =============================================================================


class ReviewRequest(Base):
    """Review request and result storage.

    Stores Claude Code / Codex review requests and their results.
    Eliminates the need to fetch from GitHub API for review status.
    """

    __tablename__ = "review_requests"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default="uuid_generate_v4()")
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    step: Mapped[str] = mapped_column(String(20), nullable=False)

    # GitHub issue information
    issue_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    issue_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    issue_state: Mapped[str | None] = mapped_column(String(20), nullable=True)  # open, closed

    # Review status: pending, in_progress, completed, closed_without_result
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)

    # Review result
    review_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # all, fact, seo, quality
    review_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("run_id", "step", "review_type", name="uq_review_request_run_step_type"),
        Index("idx_review_requests_run_id", "run_id"),
        Index("idx_review_requests_status", "status"),
    )
