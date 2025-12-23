"""FastAPI application entry point.

SEO Article Generator API server with endpoints for:
- Run management (create, list, get, approve, reject, retry, cancel)
- Artifact retrieval
- WebSocket progress streaming
"""

import json
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from typing import Any, Literal

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

# Temporal client for workflow management
from temporalio.client import Client as TemporalClient

from apps.api.auth import get_current_user
from apps.api.auth.middleware import (
    AuthError,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from apps.api.auth.schemas import (
    AuthUser,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
)
from apps.api.db import (
    Artifact as ArtifactModel,
)
from apps.api.db import (
    AuditLogger,
    Run,
    Step,
    TenantDBManager,
    TenantIdValidationError,
)
from apps.api.prompts.loader import PromptPackLoader, PromptPackNotFoundError
from apps.api.routers import diagnostics, hearing, keywords, step11, step12
from apps.api.schemas.article_hearing import (
    ArticleHearingInput,
)
from apps.api.storage import (
    ArtifactNotFoundError,
    ArtifactStore,
    ArtifactStoreError,
)
from apps.api.storage import (
    ArtifactRef as StorageArtifactRef,
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class RunStatus(str, Enum):
    """Run status values matching UI expectations."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    WAITING_IMAGE_INPUT = "waiting_image_input"  # Step11画像生成のユーザー入力待ち
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Step status values matching UI expectations."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ErrorType(str, Enum):
    """Error type classification."""

    RETRYABLE = "RETRYABLE"
    NON_RETRYABLE = "NON_RETRYABLE"
    VALIDATION_FAIL = "VALIDATION_FAIL"


# =============================================================================
# Pydantic Models - Request/Response matching UI types.ts
# =============================================================================


class ModelConfigOptions(BaseModel):
    """Model configuration options."""

    grounding: bool | None = None
    temperature: float | None = None
    max_tokens: int | None = None


class ModelConfig(BaseModel):
    """LLM model configuration."""

    platform: str  # gemini, openai, anthropic
    model: str
    options: ModelConfigOptions = Field(default_factory=ModelConfigOptions)


class ToolConfig(BaseModel):
    """Tool configuration."""

    serp_fetch: bool = True
    page_fetch: bool = True
    url_verify: bool = True
    pdf_extract: bool = False


class LegacyRunInput(BaseModel):
    """Legacy run input data (backward compatibility)."""

    keyword: str
    target_audience: str | None = None
    competitor_urls: list[str] | None = None
    additional_requirements: str | None = None


# Type alias for backward compatibility
RunInput = LegacyRunInput


class RunOptions(BaseModel):
    """Run execution options."""

    retry_limit: int = 3
    repair_enabled: bool = True


class StepModelConfig(BaseModel):
    """Per-step model configuration - matches UI StepModelConfig."""

    step_id: str
    platform: str  # gemini, openai, anthropic
    model: str
    temperature: float = 0.7
    grounding: bool = False
    retry_limit: int = 3
    repair_enabled: bool = True


class CreateRunInput(BaseModel):
    """Request to create a new run - supports both legacy and new input formats.

    For legacy format:
        input: { keyword: "...", target_audience: "...", ... }

    For new format (ArticleHearingInput):
        input: { business: {...}, keyword: {...}, strategy: {...}, ... }
    """

    # Accept either LegacyRunInput or ArticleHearingInput
    input: LegacyRunInput | ArticleHearingInput
    model_config_data: ModelConfig = Field(alias="model_config")
    step_configs: list[StepModelConfig] | None = None
    tool_config: ToolConfig | None = None
    options: RunOptions | None = None

    class Config:
        populate_by_name = True

    def get_normalized_input(self) -> dict[str, Any]:
        """Normalize input to a consistent format for storage and workflow."""
        if isinstance(self.input, ArticleHearingInput):
            # New format: store full structure and also extract legacy fields
            return {
                "format": "article_hearing_v1",
                "data": self.input.model_dump(),
                # Legacy fields for backward compatibility
                "keyword": self.input.get_effective_keyword(),
                "target_audience": self.input.business.target_audience,
                "competitor_urls": None,
                "additional_requirements": self.input._build_additional_requirements(),
            }
        else:
            # Legacy format
            return {
                "format": "legacy",
                "keyword": self.input.keyword,
                "target_audience": self.input.target_audience,
                "competitor_urls": self.input.competitor_urls,
                "additional_requirements": self.input.additional_requirements,
            }

    def get_effective_keyword(self) -> str:
        """Get the effective keyword from either input format."""
        if isinstance(self.input, ArticleHearingInput):
            return self.input.get_effective_keyword()
        return self.input.keyword


class RejectRunInput(BaseModel):
    """Request body for rejecting a run."""

    reason: str = ""


class StepError(BaseModel):
    """Step error information."""

    type: ErrorType
    code: str
    message: str
    details: dict[str, Any] | None = None


class RepairLog(BaseModel):
    """Repair action log."""

    repair_type: str
    applied_at: str
    description: str


class StepAttemptStatus(str, Enum):
    """Step attempt status values."""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class StepAttempt(BaseModel):
    """Step attempt record."""

    id: str
    step_id: str
    attempt_num: int
    status: StepAttemptStatus
    started_at: str
    completed_at: str | None = None
    error: StepError | None = None
    repairs: list[RepairLog] | None = None


class ValidationError(BaseModel):
    """Validation error."""

    code: str
    message: str
    path: str | None = None
    line: int | None = None


class ValidationWarning(BaseModel):
    """Validation warning."""

    code: str
    message: str
    path: str | None = None
    suggestion: str | None = None


class ValidationReport(BaseModel):
    """Validation report matching UI expectations."""

    format: str  # json, csv, html, markdown
    valid: bool
    errors: list[ValidationError] = Field(default_factory=list)
    warnings: list[ValidationWarning] = Field(default_factory=list)
    checked_at: str


class ArtifactRef(BaseModel):
    """Artifact reference matching UI ArtifactRef."""

    id: str
    step_id: str
    step_name: str = ""  # Human-readable step name for display
    ref_path: str
    digest: str
    content_type: str
    size_bytes: int
    created_at: str


class ArtifactContent(BaseModel):
    """Artifact content matching UI ArtifactContent."""

    ref: ArtifactRef
    content: str
    encoding: str = "utf-8"  # utf-8 or base64


class StepResponse(BaseModel):
    """Step response matching UI Step type."""

    id: str
    run_id: str
    step_name: str
    status: StepStatus
    attempts: list[StepAttempt] = Field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None
    artifacts: list[ArtifactRef] | None = None
    validation_report: ValidationReport | None = None


class StepUpdateRequest(BaseModel):
    """Request to update step status (internal API)."""

    run_id: str
    step_name: str
    status: Literal["running", "completed", "failed"]
    error_message: str | None = None
    retry_count: int = 0


class RunError(BaseModel):
    """Run error information."""

    code: str
    message: str
    step: str | None = None
    details: dict[str, Any] | None = None


class RunSummary(BaseModel):
    """Run summary for list view."""

    id: str
    status: RunStatus
    current_step: str | None
    keyword: str
    model_config_data: ModelConfig = Field(alias="model_config")
    created_at: str
    updated_at: str

    class Config:
        populate_by_name = True


class RunResponse(BaseModel):
    """Full run response matching UI Run type."""

    id: str
    tenant_id: str
    status: RunStatus
    current_step: str | None
    input: RunInput
    model_config_data: ModelConfig = Field(alias="model_config")
    step_configs: list[StepModelConfig] | None = None
    tool_config: ToolConfig | None = None
    options: RunOptions | None = None
    steps: list[StepResponse] = Field(default_factory=list)
    created_at: str
    updated_at: str
    started_at: str | None = None
    completed_at: str | None = None
    error: RunError | None = None

    class Config:
        populate_by_name = True


class EventResponse(BaseModel):
    """Event response for audit log."""

    id: str
    event_type: str
    payload: dict[str, Any]
    created_at: str


# =============================================================================
# Prompt Pydantic Models
# =============================================================================


class PromptVariableInfo(BaseModel):
    """Prompt variable information."""

    required: bool = True
    type: str = "string"
    description: str = ""
    default: str | None = None


class PromptResponse(BaseModel):
    """Prompt response model."""

    id: int
    step: str
    version: int
    content: str
    variables: dict[str, PromptVariableInfo] | None = None
    is_active: bool
    created_at: str | None = None


class PromptListResponse(BaseModel):
    """Prompt list response model."""

    prompts: list[PromptResponse]
    total: int


class CreatePromptInput(BaseModel):
    """Request to create a new prompt."""

    step: str = Field(..., description="Step identifier (e.g., step0, step1, step3a)")
    content: str = Field(..., description="Prompt content text")
    variables: dict[str, PromptVariableInfo] | None = Field(None, description="Variable definitions for template rendering")


class UpdatePromptInput(BaseModel):
    """Request to update an existing prompt."""

    content: str | None = Field(None, description="Updated prompt content")
    variables: dict[str, PromptVariableInfo] | None = Field(None, description="Updated variable definitions")
    is_active: bool | None = Field(None, description="Active status")


# =============================================================================
# Environment Validation
# =============================================================================


def validate_environment() -> list[str]:
    """Validate required environment variables.

    Returns:
        List of warning messages for missing optional variables
    """
    warnings = []

    # Check LLM API keys (at least one should be set for production)
    llm_keys = ["GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
    has_llm_key = any(os.getenv(key) for key in llm_keys)

    if not has_llm_key and os.getenv("USE_MOCK_LLM", "false").lower() != "true":
        warnings.append(f"No LLM API key set. Set at least one of: {', '.join(llm_keys)} or set USE_MOCK_LLM=true")

    return warnings


# =============================================================================
# Application Lifecycle
# =============================================================================

# Global infrastructure instances
tenant_db_manager: TenantDBManager | None = None
artifact_store: ArtifactStore | None = None
temporal_client: TemporalClient | None = None

# Temporal configuration
TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost")
TEMPORAL_PORT = os.getenv("TEMPORAL_PORT", "7233")
TEMPORAL_NAMESPACE = os.getenv("TEMPORAL_NAMESPACE", "default")
TEMPORAL_TASK_QUEUE = os.getenv("TEMPORAL_TASK_QUEUE", "seo-article-generation")


def get_tenant_db_manager() -> TenantDBManager:
    """Get the global TenantDBManager instance."""
    if tenant_db_manager is None:
        raise RuntimeError("TenantDBManager not initialized")
    return tenant_db_manager


def get_artifact_store() -> ArtifactStore:
    """Get the global ArtifactStore instance."""
    if artifact_store is None:
        raise RuntimeError("ArtifactStore not initialized")
    return artifact_store


def get_temporal_client() -> TemporalClient:
    """Get the global Temporal client instance."""
    if temporal_client is None:
        raise RuntimeError("Temporal client not initialized")
    return temporal_client


async def get_step11_workflow_handle(run_id: str) -> Any:
    """Get the workflow handle for Step11 operations.

    For completed runs that have ImageAdditionWorkflow running,
    returns the handle for image-addition-{run_id}.
    Otherwise returns the handle for the original ArticleWorkflow (run_id).
    """
    client = get_temporal_client()

    # First try the ImageAdditionWorkflow (for completed runs)
    image_addition_workflow_id = f"image-addition-{run_id}"
    try:
        handle = client.get_workflow_handle(image_addition_workflow_id)
        # Check if this workflow is running by trying to describe it
        description = await handle.describe()
        if description.status is not None and description.status.name == "RUNNING":
            logger.debug(f"Using ImageAdditionWorkflow for run {run_id}")
            return handle
    except Exception:
        # ImageAdditionWorkflow doesn't exist or isn't running
        pass

    # Fall back to ArticleWorkflow
    logger.debug(f"Using ArticleWorkflow for run {run_id}")
    return client.get_workflow_handle(run_id)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    global tenant_db_manager, artifact_store, temporal_client

    logger.info("=" * 60)
    logger.info("SEO Article Generator - API Server Starting")
    logger.info("=" * 60)

    # Validate environment
    warnings = validate_environment()
    for warning in warnings:
        logger.warning(warning)

    # Log configuration
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"Log Level: {os.getenv('LOG_LEVEL', 'INFO')}")
    logger.info(f"CORS Origins: {os.getenv('CORS_ORIGINS', '*')}")

    # Initialize infrastructure components
    tenant_db_manager = TenantDBManager()
    artifact_store = ArtifactStore()
    logger.info("Infrastructure components initialized (TenantDBManager, ArtifactStore)")

    # Initialize Temporal client (lazy reconnect on health check)
    try:
        temporal_address = f"{TEMPORAL_HOST}:{TEMPORAL_PORT}"
        temporal_client = await TemporalClient.connect(
            temporal_address,
            namespace=TEMPORAL_NAMESPACE,
        )
        logger.info(f"Connected to Temporal at {temporal_address} (namespace: {TEMPORAL_NAMESPACE})")
    except Exception as e:
        logger.warning(f"Failed to connect to Temporal: {e}. Workflow features will be disabled.")
        temporal_client = None

    yield

    # Cleanup
    if tenant_db_manager:
        await tenant_db_manager.close()
        logger.info("TenantDBManager connections closed")

    logger.info("API Server shutting down...")


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="SEO Article Generator API",
    description="API for managing SEO article generation workflows",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware (VULN-008: 許可オリジンを明示的に指定)
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
# 空文字列を除去
cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]
if not cors_origins:
    cors_origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

# Include routers
app.include_router(diagnostics.router)
app.include_router(hearing.router)
app.include_router(keywords.router)
app.include_router(step11.router)
app.include_router(step12.router)


# =============================================================================
# Health Check
# =============================================================================


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    environment: str


class DetailedHealthResponse(BaseModel):
    """Detailed health check response."""

    status: str
    version: str
    environment: str
    services: dict[str, str]


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        environment=os.getenv("ENVIRONMENT", "development"),
    )


@app.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check() -> DetailedHealthResponse:
    """Detailed health check with service status.

    Checks connectivity to:
    - PostgreSQL (via TenantDBManager)
    - MinIO/Storage (via ArtifactStore)
    - Temporal (via Temporal client)
    """
    services: dict[str, str] = {}
    overall_healthy = True

    # Check PostgreSQL
    try:
        if tenant_db_manager:
            # Try a simple operation on dev tenant
            async with tenant_db_manager.get_session("dev-tenant") as session:
                from sqlalchemy import text

                await session.execute(text("SELECT 1"))
            services["postgres"] = "healthy"
        else:
            services["postgres"] = "not_initialized"
            overall_healthy = False
    except Exception as e:
        services["postgres"] = f"unhealthy: {str(e)[:50]}"
        overall_healthy = False

    # Check MinIO/Storage
    try:
        if artifact_store:
            # ArtifactStore uses MinIO client
            services["minio"] = "healthy"
        else:
            services["minio"] = "not_initialized"
            overall_healthy = False
    except Exception as e:
        services["minio"] = f"unhealthy: {str(e)[:50]}"
        overall_healthy = False

    # Check Temporal (attempt reconnect if not connected)
    global temporal_client
    try:
        if temporal_client is None:
            # Attempt to reconnect
            try:
                temporal_address = f"{TEMPORAL_HOST}:{TEMPORAL_PORT}"
                temporal_client = await TemporalClient.connect(
                    temporal_address,
                    namespace=TEMPORAL_NAMESPACE,
                )
                logger.info(f"Reconnected to Temporal at {temporal_address}")
                services["temporal"] = "healthy"
            except Exception as reconnect_error:
                services["temporal"] = f"not_connected: {str(reconnect_error)[:30]}"
                if os.getenv("ENVIRONMENT") != "development":
                    overall_healthy = False
        else:
            services["temporal"] = "healthy"
    except Exception as e:
        services["temporal"] = f"unhealthy: {str(e)[:50]}"
        overall_healthy = False

    return DetailedHealthResponse(
        status="healthy" if overall_healthy else "degraded",
        version="0.1.0",
        environment=os.getenv("ENVIRONMENT", "development"),
        services=services,
    )


# =============================================================================
# Authentication Endpoints (VULN-005)
# =============================================================================


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest) -> LoginResponse:
    """ログイン処理

    TODO: 実際のユーザー認証ロジックを実装
    現在はスタブ実装
    """
    if os.getenv("ENVIRONMENT") == "development":
        user = AuthUser(
            user_id="dev-user",
            tenant_id="dev-tenant",
            email=request.email,
            roles=["user"],
        )
        access_token = create_access_token(user.user_id, user.tenant_id, user.roles)
        refresh_token = create_refresh_token(user.user_id, user.tenant_id)

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=15 * 60,
            user=user,
        )

    raise HTTPException(status_code=501, detail="Not implemented")


@app.post("/api/auth/refresh", response_model=RefreshResponse)
async def refresh_token_endpoint(request: RefreshRequest) -> RefreshResponse:
    """トークンリフレッシュ"""
    try:
        token_data = verify_token(request.refresh_token, expected_type="refresh")

        new_access_token = create_access_token(
            token_data.sub,
            token_data.tenant_id,
            token_data.roles,
        )

        new_refresh_token = create_refresh_token(
            token_data.sub,
            token_data.tenant_id,
        )

        return RefreshResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=15 * 60,
        )

    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
        ) from e


@app.post("/api/auth/logout")
async def logout(user: AuthUser = Depends(get_current_user)) -> dict[str, bool]:
    """ログアウト処理

    TODO: トークンの無効化リストへの追加（Redis等）
    """
    logger.info(f"User logged out: {user.user_id}")
    return {"success": True}


# =============================================================================
# Helper Functions
# =============================================================================


def _run_orm_to_response(run: Run, steps: list[Step] | None = None) -> RunResponse:
    """Convert Run ORM model to RunResponse Pydantic model."""
    # Parse stored JSON configs
    input_data = run.input_data or {}
    config = run.config or {}

    run_input = RunInput(
        keyword=input_data.get("keyword", ""),
        target_audience=input_data.get("target_audience"),
        competitor_urls=input_data.get("competitor_urls"),
        additional_requirements=input_data.get("additional_requirements"),
    )

    model_config_data = config.get("model_config", {})
    model_config = ModelConfig(
        platform=model_config_data.get("platform", "gemini"),
        model=model_config_data.get("model", "gemini-1.5-pro"),
        options=ModelConfigOptions(**model_config_data.get("options", {})),
    )

    tool_config_data = config.get("tool_config")
    tool_config = ToolConfig(**tool_config_data) if tool_config_data else None

    options_data = config.get("options")
    options = RunOptions(**options_data) if options_data else None

    # Parse step_configs
    step_configs_data = config.get("step_configs")
    step_configs: list[StepModelConfig] | None = None
    if step_configs_data:
        step_configs = [StepModelConfig(**sc) for sc in step_configs_data]

    # Convert steps if provided
    step_responses: list[StepResponse] = []
    if steps:
        for step_orm in steps:
            step_responses.append(
                StepResponse(
                    id=str(step_orm.id),
                    run_id=str(step_orm.run_id),
                    step_name=step_orm.step_name,  # DB column is step_name
                    status=StepStatus(step_orm.status),
                    attempts=[],
                    started_at=step_orm.started_at.isoformat() if step_orm.started_at else None,
                    completed_at=step_orm.completed_at.isoformat() if step_orm.completed_at else None,
                )
            )

    # Build error if present
    error = None
    if run.error_message:
        error = RunError(
            code=run.error_code or "UNKNOWN",
            message=run.error_message,
            step=run.current_step,
        )

    return RunResponse(
        id=str(run.id),
        tenant_id=run.tenant_id,
        status=RunStatus(run.status),
        current_step=run.current_step,
        input=run_input,
        model_config=model_config,
        step_configs=step_configs,
        tool_config=tool_config,
        options=options,
        steps=step_responses,
        created_at=run.created_at.isoformat(),
        updated_at=run.updated_at.isoformat(),
        started_at=run.started_at.isoformat() if run.started_at else None,
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        error=error,
    )


async def _get_steps_from_storage(
    tenant_id: str, run_id: str, current_step: str | None, run_status: str | None = None
) -> list[StepResponse]:
    """Build step responses from storage artifacts.

    When DB doesn't have step records, we infer step status from storage.
    If a step has output.json in storage, it's considered completed.
    Also builds artifact refs for each step.

    Args:
        tenant_id: Tenant ID
        run_id: Run ID
        current_step: Current step name from Temporal
        run_status: Overall run status (e.g., "failed", "running", "completed")
    """
    store = get_artifact_store()
    if store is None:
        return []

    try:
        artifact_paths = await store.list_run_artifacts(tenant_id, run_id)
    except Exception as e:
        logger.warning(f"Failed to list artifacts for steps: {e}")
        return []

    # Extract step names and artifacts from paths like: storage/tenant/run/step0/output.json
    completed_steps: set[str] = set()
    step_artifacts: dict[str, list[str]] = {}  # step_name -> list of artifact paths

    for path in artifact_paths:
        parts = path.split("/")
        if len(parts) >= 4:
            step_name = parts[-2]
            # Track artifacts per step
            if step_name not in step_artifacts:
                step_artifacts[step_name] = []
            step_artifacts[step_name].append(path)
            # Mark step as completed if it has output.json
            if parts[-1] == "output.json":
                completed_steps.add(step_name)

    # Define all workflow steps in order
    # Note: step6_5 in storage corresponds to step6.5 in UI
    # step-1 is the input step (always completed when workflow starts)
    # step3 is a parent step whose status is derived from step3a/b/c
    all_steps = [
        "step-1",
        "step0",
        "step1",
        "step2",
        "step3",
        "step3a",
        "step3b",
        "step3c",
        "step4",
        "step5",
        "step6",
        "step6_5",
        "step7a",
        "step7b",
        "step8",
        "step9",
        "step10",
    ]

    # Steps that are always completed once workflow starts (no artifact needed)
    always_completed_steps = {"step-1", "step0"}

    # Define parent steps with their children (parent status derived from children)
    parent_child_groups = {
        "step3": ["step3a", "step3b", "step3c"],
    }

    # Define parallel step groups (these steps run in parallel, not sequentially)
    parallel_groups = {
        "step3a": {"step3a", "step3b", "step3c"},
        "step3b": {"step3a", "step3b", "step3c"},
        "step3c": {"step3a", "step3b", "step3c"},
        "step7a": {"step7a", "step7b"},
        "step7b": {"step7a", "step7b"},
    }

    # Define steps after each parallel group (used for inference)
    steps_after_parallel = {
        "step3a": "step4",
        "step3b": "step4",
        "step3c": "step4",
        "step7a": "step8",
        "step7b": "step8",
    }

    step_responses: list[StepResponse] = []
    for i, step_name in enumerate(all_steps):
        # Normalize step name (step6_5 -> step6.5 for display consistency)
        display_name = step_name.replace("_", ".")

        # Determine status
        if step_name in completed_steps:
            status = StepStatus.COMPLETED
        elif current_step and current_step == step_name:
            # If run is failed, the current step is the failed step
            if run_status == RunStatus.FAILED.value:
                status = StepStatus.FAILED
            else:
                status = StepStatus.RUNNING
        elif current_step and current_step == display_name:
            # If run is failed, the current step is the failed step
            if run_status == RunStatus.FAILED.value:
                status = StepStatus.FAILED
            else:
                status = StepStatus.RUNNING
        # Special handling for input steps: always completed once workflow starts
        elif step_name in always_completed_steps:
            status = StepStatus.COMPLETED
        # Special handling for parent steps (step3): derive from children
        elif step_name in parent_child_groups:
            children = parent_child_groups[step_name]
            # Parent is completed when ALL children are completed
            all_children_completed = all(child in completed_steps for child in children)
            if all_children_completed:
                status = StepStatus.COMPLETED
            # Parent is running/failed if any child is current step
            elif current_step in children:
                if run_status == RunStatus.FAILED.value:
                    status = StepStatus.FAILED
                else:
                    status = StepStatus.RUNNING
            else:
                status = StepStatus.PENDING
        else:
            # Special handling for parallel steps (step3a/b/c, step7a/b)
            if step_name in parallel_groups:
                # If the step after this parallel group is completed or running,
                # this parallel step must be completed
                next_step = steps_after_parallel[step_name]
                next_step_idx = all_steps.index(next_step) if next_step in all_steps else -1
                if next_step_idx >= 0:
                    # Check if next step or any step after is completed/running
                    later_completed = any(s in completed_steps for s in all_steps[next_step_idx:])
                    later_running = current_step in all_steps[next_step_idx:] if current_step else False
                    if later_completed or later_running:
                        status = StepStatus.COMPLETED
                    else:
                        status = StepStatus.PENDING
                else:
                    status = StepStatus.PENDING
            else:
                # Check if any later step is completed (means this one was skipped or completed)
                later_completed = any(s in completed_steps for s in all_steps[i + 1 :])
                if later_completed:
                    status = StepStatus.COMPLETED
                else:
                    status = StepStatus.PENDING

        # Build artifact refs for this step
        artifacts: list[ArtifactRef] = []
        paths = step_artifacts.get(step_name, [])
        for idx, artifact_path in enumerate(paths):
            # Extract filename for content type inference
            filename = artifact_path.split("/")[-1] if "/" in artifact_path else artifact_path
            content_type = (
                "application/json"
                if filename.endswith(".json")
                else "text/html"
                if filename.endswith(".html")
                else "text/markdown"
                if filename.endswith(".md")
                else "application/octet-stream"
            )

            artifacts.append(
                ArtifactRef(
                    id=f"{run_id}-{step_name}-{idx}",
                    step_id=f"{run_id}-{step_name}",
                    ref_path=artifact_path,
                    digest="",  # Unknown from path only
                    content_type=content_type,
                    size_bytes=0,  # Unknown from path only
                    created_at=datetime.now().isoformat(),
                )
            )

        step_responses.append(
            StepResponse(
                id=f"{run_id}-{step_name}",
                run_id=run_id,
                step_name=display_name,
                status=status,
                attempts=[],
                started_at=None,
                completed_at=None,
                artifacts=artifacts if artifacts else None,
            )
        )

    return step_responses


# =============================================================================
# Run Management Endpoints
# =============================================================================


@app.post("/api/runs", response_model=RunResponse)
async def create_run(
    data: CreateRunInput,
    start_workflow: bool = Query(default=True, description="Whether to start the Temporal workflow immediately"),
    user: AuthUser = Depends(get_current_user),
) -> RunResponse:
    """Create a new workflow run and optionally start Temporal workflow.

    Args:
        data: Run configuration
        start_workflow: If True, starts Temporal workflow immediately (default: True)
        user: Authenticated user
    """
    import uuid

    tenant_id = user.tenant_id
    run_id = str(uuid.uuid4())
    now = datetime.now()

    # Prepare JSON data for storage using normalized input
    input_data = data.get_normalized_input()
    effective_keyword = data.get_effective_keyword()

    # Extract legacy-compatible fields for workflow
    target_audience = input_data.get("target_audience")
    competitor_urls = input_data.get("competitor_urls")
    additional_requirements = input_data.get("additional_requirements")

    # Build workflow config
    # Note: keyword/target_audience are duplicated at top level for step0 activity compatibility
    workflow_config = {
        "model_config": data.model_config_data.model_dump(),
        "step_configs": [sc.model_dump() for sc in data.step_configs] if data.step_configs else None,
        "tool_config": data.tool_config.model_dump() if data.tool_config else None,
        "options": data.options.model_dump() if data.options else None,
        "pack_id": "default",  # Required by ArticleWorkflow
        "input": input_data,
        # Step activities expect these at top level
        "keyword": effective_keyword,
        "target_audience": target_audience,
        "competitor_urls": competitor_urls,
        "additional_requirements": additional_requirements,
    }

    db_manager = get_tenant_db_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # Create Run ORM instance
            run_orm = Run(
                id=run_id,
                tenant_id=tenant_id,
                status=RunStatus.PENDING.value,
                current_step=None,
                input_data=input_data,
                config=workflow_config,
                created_at=now,
                updated_at=now,
            )
            session.add(run_orm)

            # Log audit entry
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="create",
                resource_type="run",
                resource_id=run_id,
                details={"keyword": effective_keyword, "start_workflow": start_workflow},
            )

            await session.flush()

            logger.info("Run created", extra={"run_id": run_id, "tenant_id": tenant_id})

            # ===== DEBUG_LOG_START =====
            logger.debug(f"[CREATE_RUN] start_workflow={start_workflow}, temporal_client={temporal_client is not None}")
            # ===== DEBUG_LOG_END =====

            # Start Temporal workflow if requested and client is available
            if start_workflow and temporal_client is not None:
                # ===== DEBUG_LOG_START =====
                logger.debug(f"[CREATE_RUN] Attempting to start Temporal workflow for run_id={run_id}")
                # ===== DEBUG_LOG_END =====
                try:
                    # Start ArticleWorkflow
                    await temporal_client.start_workflow(
                        "ArticleWorkflow",  # Workflow type name
                        args=[tenant_id, run_id, workflow_config, None],  # resume_from=None
                        id=run_id,  # Use run_id as workflow_id for correlation
                        task_queue=TEMPORAL_TASK_QUEUE,
                    )

                    # Update run status to running
                    run_orm.status = RunStatus.RUNNING.value
                    run_orm.started_at = now
                    run_orm.updated_at = now

                    logger.info(
                        "Temporal workflow started",
                        extra={"run_id": run_id, "tenant_id": tenant_id, "task_queue": TEMPORAL_TASK_QUEUE},
                    )

                    # Broadcast run started event via WebSocket
                    await ws_manager.broadcast_run_update(
                        run_id=run_id,
                        event_type="run.started",
                        status=RunStatus.RUNNING.value,
                    )

                except Exception as wf_error:
                    logger.error(f"Failed to start Temporal workflow: {wf_error}", exc_info=True)
                    # Run is created but workflow failed to start
                    # Mark as failed and record error
                    run_orm.status = RunStatus.FAILED.value
                    run_orm.error_code = "WORKFLOW_START_FAILED"
                    run_orm.error_message = str(wf_error)
                    run_orm.updated_at = now

            elif start_workflow and temporal_client is None:
                # ===== DEBUG_LOG_START =====
                logger.debug("[CREATE_RUN] temporal_client is None, skipping workflow start")
                # ===== DEBUG_LOG_END =====
                logger.warning(
                    "Temporal client not available, workflow not started",
                    extra={"run_id": run_id, "tenant_id": tenant_id},
                )
                # Keep status as pending since workflow was requested but couldn't start

            return _run_orm_to_response(run_orm)

    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to create run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create run") from e


@app.get("/api/runs")
async def list_runs(
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List runs with optional filtering."""
    from sqlalchemy import func, select

    tenant_id = user.tenant_id
    offset = (page - 1) * limit

    db_manager = get_tenant_db_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # Build query with tenant isolation
            query = select(Run).where(Run.tenant_id == tenant_id)

            # Status filter
            if status:
                query = query.where(Run.status == status)

            # Count total
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await session.execute(count_query)
            total = total_result.scalar() or 0

            # Apply pagination and ordering
            query = query.order_by(Run.created_at.desc()).offset(offset).limit(limit)
            result = await session.execute(query)
            runs = result.scalars().all()

            # Convert to RunSummary format
            runs_summary = []
            for r in runs:
                input_data = r.input_data or {}
                config = r.config or {}
                model_config_data = config.get("model_config", {})

                runs_summary.append(
                    {
                        "id": str(r.id),
                        "status": r.status,
                        "current_step": r.current_step,
                        "keyword": input_data.get("keyword", ""),
                        "model_config": model_config_data,
                        "created_at": r.created_at.isoformat(),
                        "updated_at": r.updated_at.isoformat(),
                    }
                )

            return {"runs": runs_summary, "total": total, "limit": limit, "offset": offset}

    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to list runs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list runs") from e


@app.get("/api/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, user: AuthUser = Depends(get_current_user)) -> RunResponse:
    """Get run details with Temporal state synchronization."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    tenant_id = user.tenant_id

    db_manager = get_tenant_db_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # Query run with steps eager loading
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id).options(selectinload(Run.steps))
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # Sync with Temporal state if workflow is active
            db_updated = False
            if run.status in (RunStatus.RUNNING.value, RunStatus.WAITING_APPROVAL.value, RunStatus.PENDING.value):
                db_updated = await _sync_run_with_temporal(run, session)

            if db_updated:
                await session.flush()
                await session.refresh(run)

            # If no steps in DB, try to infer from storage
            db_steps = list(run.steps)
            if not db_steps:
                storage_steps = await _get_steps_from_storage(tenant_id, run_id, run.current_step, run.status)
                # Build response with storage-based steps
                response = _run_orm_to_response(run, steps=[])
                response.steps = storage_steps
                return response

            return _run_orm_to_response(run, steps=db_steps)

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to get run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get run") from e


async def _sync_run_with_temporal(run: Run, session: Any) -> bool:
    """Sync Run DB record with Temporal workflow state.

    Queries Temporal for current workflow status and updates DB if needed.
    Returns True if DB was updated.
    """
    if temporal_client is None:
        return False

    try:
        workflow_handle = temporal_client.get_workflow_handle(str(run.id))

        # Query workflow status
        workflow_status = await workflow_handle.query("get_status")
        current_step = workflow_status.get("current_step", "")
        rejected = workflow_status.get("rejected", False)
        rejection_reason = workflow_status.get("rejection_reason")

        # Check workflow execution status
        workflow_desc = await workflow_handle.describe()
        workflow_execution_status = workflow_desc.status

        # Import enum for comparison
        from temporalio.client import WorkflowExecutionStatus

        db_updated = False
        now = datetime.now()

        # Update current_step if changed
        if current_step and run.current_step != current_step:
            run.current_step = current_step
            run.updated_at = now
            db_updated = True
            logger.debug(f"Synced current_step: {current_step} for run {run.id}")

        # Update status based on Temporal state
        if workflow_execution_status == WorkflowExecutionStatus.COMPLETED:
            if run.status != RunStatus.COMPLETED.value:
                run.status = RunStatus.COMPLETED.value
                run.completed_at = now
                run.updated_at = now
                db_updated = True
                logger.info(f"Run {run.id} marked as completed from Temporal sync")

        elif workflow_execution_status == WorkflowExecutionStatus.FAILED:
            if run.status != RunStatus.FAILED.value:
                run.status = RunStatus.FAILED.value
                run.updated_at = now
                db_updated = True
                logger.info(f"Run {run.id} marked as failed from Temporal sync")

        elif workflow_execution_status == WorkflowExecutionStatus.CANCELED:
            if run.status != RunStatus.CANCELLED.value:
                run.status = RunStatus.CANCELLED.value
                run.updated_at = now
                db_updated = True
                logger.info(f"Run {run.id} marked as cancelled from Temporal sync")

        elif workflow_execution_status == WorkflowExecutionStatus.RUNNING:
            # Step11 waiting states
            step11_waiting_states = (
                "waiting_image_generation",
                "step11_position_review",
                "step11_image_instructions",
                "step11_image_review",
                "step11_preview",
            )
            # Check if waiting for approval (Step3)
            if current_step == "waiting_approval":
                if run.status != RunStatus.WAITING_APPROVAL.value:
                    run.status = RunStatus.WAITING_APPROVAL.value
                    run.updated_at = now
                    db_updated = True
                    logger.info(f"Run {run.id} marked as waiting_approval from Temporal sync")
            # Check if waiting for image input (Step11)
            elif current_step in step11_waiting_states:
                if run.status != RunStatus.WAITING_IMAGE_INPUT.value:
                    run.status = RunStatus.WAITING_IMAGE_INPUT.value
                    run.updated_at = now
                    db_updated = True
                    logger.info(f"Run {run.id} marked as waiting_image_input from Temporal sync")
            elif rejected:
                if run.status != RunStatus.FAILED.value:
                    run.status = RunStatus.FAILED.value
                    run.error_message = rejection_reason or "Rejected by user"
                    run.updated_at = now
                    db_updated = True
            elif run.status not in (RunStatus.RUNNING.value, RunStatus.WAITING_APPROVAL.value, RunStatus.WAITING_IMAGE_INPUT.value):
                run.status = RunStatus.RUNNING.value
                run.updated_at = now
                db_updated = True

        return db_updated

    except Exception as e:
        # Temporal query failed - workflow may not exist or be terminated
        logger.debug(f"Failed to sync with Temporal for run {run.id}: {e}")
        return False


@app.post("/api/runs/{run_id}/approve")
async def approve_run(
    run_id: str,
    comment: str | None = None,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, bool]:
    """Approve a run waiting for approval.

    Sends approval signal to Temporal workflow.
    """
    from sqlalchemy import select

    tenant_id = user.tenant_id
    logger.info(
        "Approving run",
        extra={"run_id": run_id, "tenant_id": tenant_id, "comment": comment, "user_id": user.user_id},
    )

    db_manager = get_tenant_db_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # 1. Verify run exists and belongs to tenant
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # 2. Verify run is in waiting_approval status
            if run.status != RunStatus.WAITING_APPROVAL.value:
                raise HTTPException(status_code=400, detail=f"Run is not waiting for approval (current status: {run.status})")

            # 3. Record in audit_logs (MUST be done before Temporal signal)
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="approve",
                resource_type="run",
                resource_id=run_id,
                details={"comment": comment, "previous_status": run.status},
            )

            # 4. Send signal to Temporal workflow (MUST succeed before DB update)
            if temporal_client is not None:
                try:
                    workflow_handle = temporal_client.get_workflow_handle(run_id)
                    await workflow_handle.signal("approve")
                    logger.info("Temporal approval signal sent", extra={"run_id": run_id})
                except Exception as sig_error:
                    logger.error(f"Failed to send approval signal: {sig_error}", exc_info=True)
                    # Signal failed - do NOT update DB to maintain consistency
                    raise HTTPException(status_code=503, detail=f"Failed to send approval signal to workflow: {sig_error}")
            else:
                logger.warning(
                    "Temporal client not available, signal not sent",
                    extra={"run_id": run_id},
                )
                raise HTTPException(status_code=503, detail="Temporal service unavailable")

            # 5. Update run status (only after signal success)
            run.status = RunStatus.RUNNING.value
            run.updated_at = datetime.now()

            await session.flush()
            logger.info("Run approved", extra={"run_id": run_id, "tenant_id": tenant_id})

            # Broadcast approval event via WebSocket
            await ws_manager.broadcast_run_update(
                run_id=run_id,
                event_type="run.approved",
                status=RunStatus.RUNNING.value,
            )

            return {"success": True}

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to approve run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to approve run") from e


@app.post("/api/runs/{run_id}/reject")
async def reject_run(
    run_id: str,
    data: RejectRunInput,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, bool]:
    """Reject a run waiting for approval.

    Sends rejection signal to Temporal workflow.
    """
    from sqlalchemy import select

    reason = data.reason
    tenant_id = user.tenant_id
    logger.info(
        "Rejecting run",
        extra={"run_id": run_id, "tenant_id": tenant_id, "reason": reason, "user_id": user.user_id},
    )

    db_manager = get_tenant_db_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # 1. Verify run exists and belongs to tenant
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # 2. Verify run is in waiting_approval status
            if run.status != RunStatus.WAITING_APPROVAL.value:
                raise HTTPException(status_code=400, detail=f"Run is not waiting for approval (current status: {run.status})")

            # 3. Record in audit_logs
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="reject",
                resource_type="run",
                resource_id=run_id,
                details={"reason": reason, "previous_status": run.status},
            )

            # 4. Send rejection signal to Temporal workflow (MUST succeed before DB update)
            if temporal_client is not None:
                try:
                    workflow_handle = temporal_client.get_workflow_handle(run_id)
                    await workflow_handle.signal("reject", reason or "Rejected by reviewer")
                    logger.info("Temporal rejection signal sent", extra={"run_id": run_id})
                except Exception as sig_error:
                    logger.error(f"Failed to send rejection signal: {sig_error}", exc_info=True)
                    # Signal failed - do NOT update DB to maintain consistency
                    raise HTTPException(status_code=503, detail=f"Failed to send rejection signal to workflow: {sig_error}")
            else:
                logger.warning(
                    "Temporal client not available, signal not sent",
                    extra={"run_id": run_id},
                )
                raise HTTPException(status_code=503, detail="Temporal service unavailable")

            # 5. Update run status (only after signal success)
            run.status = RunStatus.FAILED.value
            run.error_code = "REJECTED"
            run.error_message = reason or "Rejected by reviewer"
            run.updated_at = datetime.now()
            run.completed_at = datetime.now()

            await session.flush()
            logger.info("Run rejected", extra={"run_id": run_id, "tenant_id": tenant_id})

            # Broadcast rejection event via WebSocket
            await ws_manager.broadcast_run_update(
                run_id=run_id,
                event_type="run.rejected",
                status=RunStatus.FAILED.value,
                error={"code": "REJECTED", "message": reason or "Rejected by reviewer"},
            )

            return {"success": True}

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to reject run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to reject run") from e


# =============================================================================
# Step 11: Image Generation API
# =============================================================================


class Step11StartInput(BaseModel):
    """Request body for starting image generation."""

    enabled: bool = True
    image_count: int = Field(default=3, ge=1, le=5)
    position_request: str | None = None


@app.post("/api/runs/{run_id}/step11/start")
async def start_image_generation(
    run_id: str,
    data: Step11StartInput,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, bool | str]:
    """Start image generation for a run waiting at step11.

    Sends start_image_generation signal to Temporal workflow.
    """
    from sqlalchemy import select

    tenant_id = user.tenant_id
    logger.info(
        "Starting image generation",
        extra={
            "run_id": run_id,
            "tenant_id": tenant_id,
            "enabled": data.enabled,
            "image_count": data.image_count,
            "user_id": user.user_id,
        },
    )

    db_manager = get_tenant_db_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # 1. Verify run exists and belongs to tenant
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # 2. Verify run is in waiting for image generation decision
            allowed_statuses = [RunStatus.WAITING_APPROVAL.value, RunStatus.WAITING_IMAGE_INPUT.value]
            if run.status not in allowed_statuses:
                raise HTTPException(
                    status_code=400, detail=f"Run is not waiting for image generation decision (current status: {run.status})"
                )

            # 3. Record in audit_logs
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="start_image_generation",
                resource_type="run",
                resource_id=run_id,
                details={
                    "enabled": data.enabled,
                    "image_count": data.image_count,
                    "position_request": data.position_request,
                },
            )

            # 4. Send signal to Temporal workflow
            if temporal_client is not None:
                try:
                    workflow_handle = temporal_client.get_workflow_handle(run_id)
                    # Send config to workflow
                    config = {
                        "enabled": data.enabled,
                        "step11_image_count": data.image_count,
                        "step11_position_request": data.position_request or "",
                    }
                    await workflow_handle.signal("start_image_generation", config)
                    logger.info("Temporal start_image_generation signal sent", extra={"run_id": run_id})
                except Exception as sig_error:
                    logger.error(f"Failed to send start_image_generation signal: {sig_error}", exc_info=True)
                    raise HTTPException(status_code=503, detail=f"Failed to send signal to workflow: {sig_error}")
            else:
                logger.warning(
                    "Temporal client not available, signal not sent",
                    extra={"run_id": run_id},
                )
                raise HTTPException(status_code=503, detail="Temporal service unavailable")

            # 5. Update run status (only after signal success)
            run.status = RunStatus.RUNNING.value
            run.updated_at = datetime.now()

            await session.flush()
            logger.info("Image generation started", extra={"run_id": run_id, "tenant_id": tenant_id})

            # Broadcast event via WebSocket
            await ws_manager.broadcast_run_update(
                run_id=run_id,
                event_type="run.image_generation_started",
                status=RunStatus.RUNNING.value,
            )

            return {"success": True, "message": "Image generation started"}

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to start image generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to start image generation") from e


@app.post("/api/runs/{run_id}/step11/skip")
async def skip_image_generation(
    run_id: str,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, bool]:
    """Skip image generation for a run waiting at step11.

    Sends skip_image_generation signal to Temporal workflow.
    """
    from sqlalchemy import select

    tenant_id = user.tenant_id
    logger.info(
        "Skipping image generation",
        extra={"run_id": run_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    db_manager = get_tenant_db_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # 1. Verify run exists and belongs to tenant
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # 2. Verify run is in waiting for image generation decision
            allowed_statuses = [RunStatus.WAITING_APPROVAL.value, RunStatus.WAITING_IMAGE_INPUT.value]
            if run.status not in allowed_statuses:
                raise HTTPException(
                    status_code=400, detail=f"Run is not waiting for image generation decision (current status: {run.status})"
                )

            # 3. Record in audit_logs
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="skip_image_generation",
                resource_type="run",
                resource_id=run_id,
                details={},
            )

            # 4. Send signal to Temporal workflow
            if temporal_client is not None:
                try:
                    workflow_handle = temporal_client.get_workflow_handle(run_id)
                    await workflow_handle.signal("skip_image_generation")
                    logger.info("Temporal skip_image_generation signal sent", extra={"run_id": run_id})
                except Exception as sig_error:
                    logger.error(f"Failed to send skip_image_generation signal: {sig_error}", exc_info=True)
                    raise HTTPException(status_code=503, detail=f"Failed to send signal to workflow: {sig_error}")
            else:
                logger.warning(
                    "Temporal client not available, signal not sent",
                    extra={"run_id": run_id},
                )
                raise HTTPException(status_code=503, detail="Temporal service unavailable")

            # 5. Update run status (only after signal success)
            run.status = RunStatus.RUNNING.value
            run.updated_at = datetime.now()

            await session.flush()
            logger.info("Image generation skipped", extra={"run_id": run_id, "tenant_id": tenant_id})

            # Broadcast event via WebSocket
            await ws_manager.broadcast_run_update(
                run_id=run_id,
                event_type="run.image_generation_skipped",
                status=RunStatus.RUNNING.value,
            )

            return {"success": True}

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to skip image generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to skip image generation") from e


@app.post("/api/runs/{run_id}/step11/complete")
async def complete_step11(
    run_id: str,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, bool]:
    """Mark step11 as completed (skipped) for already completed runs.

    This is used when a run was completed before step11 was implemented,
    or when the user wants to skip image generation on an already completed run.
    """
    from sqlalchemy import select

    tenant_id = user.tenant_id
    logger.info(
        "Marking step11 as completed",
        extra={"run_id": run_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    db_manager = get_tenant_db_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # 1. Verify run exists and belongs to tenant
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # 2. Check existing steps for this run
            all_steps_query = select(Step).where(Step.run_id == run_id)
            all_steps_result = await session.execute(all_steps_query)
            existing_steps = {s.step_name: s for s in all_steps_result.scalars().all()}

            # 3. If run is completed but steps are missing, backfill them
            # This handles legacy runs that completed before step tracking was added
            if run.status == "completed" and len(existing_steps) == 0:
                # All steps except step11 should be marked as completed
                all_step_names = [
                    "step-1",
                    "step0",
                    "step1",
                    "step2",
                    "step3",
                    "step3a",
                    "step3b",
                    "step3c",
                    "step4",
                    "step5",
                    "step6",
                    "step6.5",
                    "step7a",
                    "step7b",
                    "step8",
                    "step9",
                    "step10",
                ]
                now = datetime.now()
                for step_name in all_step_names:
                    step = Step(
                        run_id=run_id,
                        step_name=step_name,
                        status="completed",
                        started_at=now,
                        completed_at=now,
                        retry_count=0,
                    )
                    session.add(step)
                    existing_steps[step_name] = step
                logger.info("Backfilled missing steps for legacy run", extra={"run_id": run_id, "step_count": len(all_step_names)})

            # 4. Check if step11 already exists
            step11 = existing_steps.get("step11")

            if step11:
                # Update existing step11 to completed
                step11.status = "completed"
                step11.completed_at = datetime.now()
            else:
                # Create new step11 record as completed
                step11 = Step(
                    run_id=run_id,
                    step_name="step11",
                    status="completed",
                    started_at=datetime.now(),
                    completed_at=datetime.now(),
                    retry_count=0,
                )
                session.add(step11)

            # 3. Record in audit_logs
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="complete_step11",
                resource_type="run",
                resource_id=run_id,
                details={"skipped": True},
            )

            await session.flush()
            logger.info("Step11 marked as completed", extra={"run_id": run_id, "tenant_id": tenant_id})

            # Broadcast event via WebSocket
            await ws_manager.broadcast_run_update(
                run_id=run_id,
                event_type="step_completed",
                status=run.status,
                current_step="step11",
            )

            return {"success": True}

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to complete step11: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to complete step11") from e


# ========== Step11 Multi-phase Endpoints ==========


class Step11SettingsInput(BaseModel):
    """Input for Step11 settings (Phase 11A)."""

    image_count: int = Field(default=3, ge=1, le=10)
    position_request: str = Field(default="")


class ImagePositionInput(BaseModel):
    """Image insertion position."""

    section_title: str
    section_index: int
    position: str = Field(pattern="^(before|after)$")
    source_text: str = ""
    description: str = ""


class PositionReviewInput(BaseModel):
    """Input for position review (Phase 11B)."""

    approved: bool
    modified_positions: list[ImagePositionInput] | None = None
    reanalyze: bool = False
    reanalyze_request: str = ""


class ImageInstructionInput(BaseModel):
    """Image instruction for a single position."""

    index: int
    instruction: str


class InstructionsInput(BaseModel):
    """Input for image instructions (Phase 11C)."""

    instructions: list[ImageInstructionInput]


class ImageReviewItem(BaseModel):
    """Review for a single image."""

    index: int
    accepted: bool
    retry: bool = False
    retry_instruction: str = ""


class ImageReviewInput(BaseModel):
    """Input for image review (Phase 11D)."""

    reviews: list[ImageReviewItem]


class FinalizeInput(BaseModel):
    """Input for finalization (Phase 11E)."""

    confirmed: bool
    restart_from: str | None = None


@app.post("/api/runs/{run_id}/step11/settings")
async def submit_step11_settings(
    run_id: str,
    data: Step11SettingsInput,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, bool | str]:
    """Submit initial settings for Step11 (Phase 11A).

    Sends step11_start_settings signal to Temporal workflow.
    """
    from sqlalchemy import select

    tenant_id = user.tenant_id
    logger.info(
        "Submitting step11 settings",
        extra={
            "run_id": run_id,
            "tenant_id": tenant_id,
            "image_count": data.image_count,
            "user_id": user.user_id,
        },
    )

    db_manager = get_tenant_db_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # Verify run exists and is waiting
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # Step11は waiting_image_input、Step3承認後の画像追加は waiting_approval
            allowed_statuses = [RunStatus.WAITING_APPROVAL.value, RunStatus.WAITING_IMAGE_INPUT.value]
            if run.status not in allowed_statuses:
                raise HTTPException(status_code=400, detail=f"Run is not waiting for settings (current status: {run.status})")

            # Audit log
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="step11_submit_settings",
                resource_type="run",
                resource_id=run_id,
                details={
                    "image_count": data.image_count,
                    "position_request": data.position_request,
                },
            )

            # Send signal or start new workflow
            if temporal_client is not None:
                config = {
                    "image_count": data.image_count,
                    "position_request": data.position_request,
                }

                try:
                    # まずは既存のWorkflowにsignalを送る
                    workflow_handle = temporal_client.get_workflow_handle(run_id)
                    await workflow_handle.signal("step11_start_settings", config)
                    logger.info("step11_start_settings signal sent", extra={"run_id": run_id})
                except Exception as sig_error:
                    # Workflowが存在しない場合は ImageAdditionWorkflow を起動
                    if "workflow not found" in str(sig_error).lower():
                        logger.info("Workflow not found, starting ImageAdditionWorkflow", extra={"run_id": run_id})

                        # Get step10 output (article markdown) for the workflow
                        store = get_artifact_store()
                        try:
                            step10_data = await store.get_by_path(tenant_id, run_id, "step10")
                            if step10_data:
                                step10_output = json.loads(step10_data.decode("utf-8"))
                                article_markdown = step10_output.get("markdown", "")
                            else:
                                article_markdown = ""
                        except Exception as e:
                            logger.warning(f"Failed to read step10 output: {e}")
                            article_markdown = ""

                        workflow_config = {
                            "image_count": data.image_count,
                            "position_request": data.position_request,
                            "article_markdown": article_markdown,
                        }

                        await temporal_client.start_workflow(
                            "ImageAdditionWorkflow",
                            args=[tenant_id, run_id, workflow_config],
                            id=f"image-addition-{run_id}",
                            task_queue=TEMPORAL_TASK_QUEUE,
                        )
                        logger.info("Started ImageAdditionWorkflow", extra={"run_id": run_id})
                    else:
                        logger.error(f"Failed to send signal: {sig_error}", exc_info=True)
                        raise HTTPException(status_code=503, detail=f"Failed to send signal to workflow: {sig_error}")
            else:
                raise HTTPException(status_code=503, detail="Temporal service unavailable")

            # Update status
            run.status = RunStatus.RUNNING.value
            run.updated_at = datetime.now()
            await session.flush()

            # WebSocket broadcast
            await ws_manager.broadcast_run_update(
                run_id=run_id,
                event_type="run.step11_settings_submitted",
                status=RunStatus.RUNNING.value,
            )

            return {"success": True, "message": "Settings submitted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit step11 settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to submit settings") from e


@app.post("/api/runs/{run_id}/step11/add-images")
async def add_images_to_completed_run(
    run_id: str,
    data: Step11SettingsInput,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, bool | str]:
    """Add images to an already completed run.

    This endpoint allows adding images to a run that has already completed
    without going through Step11. It will:
    1. Change the run status to waiting_approval
    2. Set current_step to waiting_image_generation
    3. Start a new workflow execution for image generation only

    This is different from the normal flow where Step11 is part of the main workflow.
    """
    from sqlalchemy import select

    tenant_id = user.tenant_id
    logger.info(
        "Adding images to completed run",
        extra={
            "run_id": run_id,
            "tenant_id": tenant_id,
            "image_count": data.image_count,
            "user_id": user.user_id,
        },
    )

    db_manager = get_tenant_db_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # Verify run exists and is completed
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            if run.status != RunStatus.COMPLETED.value:
                raise HTTPException(status_code=400, detail=f"Run must be completed to add images (current status: {run.status})")

            # Check if step11 already has generated images
            step11_query = select(Step).where(Step.run_id == run_id, Step.step_name == "step11")
            step11_result = await session.execute(step11_query)
            step11 = step11_result.scalar_one_or_none()

            if step11 and step11.status == "completed":
                # Check if images were actually generated (not just skipped)
                artifact_query = select(ArtifactModel).where(ArtifactModel.run_id == run_id, ArtifactModel.step_id == step11.id)
                artifact_result = await session.execute(artifact_query)
                artifacts = artifact_result.scalars().all()

                if artifacts and len(artifacts) > 0:
                    # Images already exist, warn user
                    logger.warning(
                        "Attempting to add images to run that already has step11 artifacts",
                        extra={"run_id": run_id, "artifact_count": len(artifacts)},
                    )
                    # Allow re-adding for now, but could be changed to error

            # Update run status to trigger image generation flow
            run.status = RunStatus.WAITING_APPROVAL.value
            run.current_step = "waiting_image_generation"
            run.updated_at = datetime.now()

            # Reset step11 if it exists
            if step11:
                step11.status = "pending"
                step11.started_at = None
                step11.completed_at = None
            else:
                # Create step11 record
                step11 = Step(
                    run_id=run_id,
                    step_name="step11",
                    status="pending",
                    retry_count=0,
                )
                session.add(step11)

            # Audit log
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="step11_add_images_initiated",
                resource_type="run",
                resource_id=run_id,
                details={
                    "image_count": data.image_count,
                    "position_request": data.position_request,
                    "previous_status": "completed",
                },
            )

            await session.flush()

            # Store settings in MinIO for later retrieval
            store = get_artifact_store()
            settings_path = f"tenants/{tenant_id}/runs/{run_id}/step11/settings.json"
            settings_data = {
                "image_count": data.image_count,
                "position_request": data.position_request,
                "initiated_at": datetime.now().isoformat(),
                "initiated_by": user.user_id,
            }
            await store.put(json.dumps(settings_data).encode("utf-8"), settings_path, "application/json")

            # Get step10 output (article markdown) for the workflow
            try:
                step10_data = await store.get_by_path(tenant_id, run_id, "step10")
                if step10_data:
                    step10_output = json.loads(step10_data.decode("utf-8"))
                    article_markdown = step10_output.get("markdown", "")
                else:
                    article_markdown = ""
            except Exception as e:
                logger.warning(f"Failed to read step10 output: {e}")
                article_markdown = ""

            # Start ImageAdditionWorkflow
            temporal_client = get_temporal_client()
            workflow_config = {
                "image_count": data.image_count,
                "position_request": data.position_request,
                "article_markdown": article_markdown,
            }

            await temporal_client.start_workflow(
                "ImageAdditionWorkflow",
                args=[tenant_id, run_id, workflow_config],
                id=f"image-addition-{run_id}",
                task_queue=TEMPORAL_TASK_QUEUE,
            )

            logger.info(
                "Started ImageAdditionWorkflow",
                extra={
                    "run_id": run_id,
                    "workflow_id": f"image-addition-{run_id}",
                },
            )

            # WebSocket broadcast
            await ws_manager.broadcast_run_update(
                run_id=run_id,
                event_type="run.add_images_initiated",
                status=RunStatus.RUNNING.value,
                current_step="step11_analyzing",
            )

            return {
                "success": True,
                "message": "Image generation workflow started.",
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add images to completed run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to initiate image generation") from e


@app.get("/api/runs/{run_id}/step11/positions")
async def get_step11_positions(
    run_id: str,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get proposed image positions for Step11 (Phase 11B).

    Returns positions analyzed by the workflow.
    """
    from sqlalchemy import select

    tenant_id = user.tenant_id

    db_manager = get_tenant_db_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # Verify run exists
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # Load positions from storage
            from apps.api.storage.artifact_store import ArtifactStore

            store = ArtifactStore()

            positions_bytes = await store.get_by_path(
                tenant_id=tenant_id,
                run_id=run_id,
                step="step11",
                filename="positions.json",
            )

            if not positions_bytes:
                return {"positions": [], "sections": [], "analysis_summary": ""}

            positions_data = json.loads(positions_bytes.decode("utf-8"))

            return {
                "positions": positions_data.get("position_analysis", {}).get("positions", []),
                "sections": positions_data.get("position_analysis", {}).get("sections", []),
                "analysis_summary": positions_data.get("position_analysis", {}).get("analysis_summary", ""),
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get step11 positions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get positions") from e


@app.post("/api/runs/{run_id}/step11/positions")
async def submit_position_review(
    run_id: str,
    data: PositionReviewInput,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, bool]:
    """Submit position review for Step11 (Phase 11B).

    Sends step11_confirm_positions signal to Temporal workflow.
    """
    from sqlalchemy import select

    tenant_id = user.tenant_id
    logger.info(
        "Submitting position review",
        extra={
            "run_id": run_id,
            "tenant_id": tenant_id,
            "approved": data.approved,
            "reanalyze": data.reanalyze,
            "user_id": user.user_id,
        },
    )

    db_manager = get_tenant_db_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # Audit log
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="step11_position_review",
                resource_type="run",
                resource_id=run_id,
                details={
                    "approved": data.approved,
                    "reanalyze": data.reanalyze,
                    "modified_count": len(data.modified_positions or []),
                },
            )

            # Send signal to the appropriate workflow (ArticleWorkflow or ImageAdditionWorkflow)
            if temporal_client is not None:
                try:
                    workflow_handle = await get_step11_workflow_handle(run_id)
                    payload = {
                        "approved": data.approved,
                        "modified_positions": ([p.model_dump() for p in data.modified_positions] if data.modified_positions else None),
                        "reanalyze": data.reanalyze,
                        "reanalyze_request": data.reanalyze_request,
                    }
                    await workflow_handle.signal("step11_confirm_positions", payload)
                    logger.info("step11_confirm_positions signal sent", extra={"run_id": run_id})
                except Exception as sig_error:
                    logger.error(f"Failed to send signal: {sig_error}", exc_info=True)
                    raise HTTPException(status_code=503, detail=f"Failed to send signal to workflow: {sig_error}")
            else:
                raise HTTPException(status_code=503, detail="Temporal service unavailable")

            await session.flush()

            # WebSocket broadcast
            await ws_manager.broadcast_run_update(
                run_id=run_id,
                event_type="run.step11_positions_reviewed",
                status=run.status,
            )

            return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit position review: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to submit position review") from e


@app.post("/api/runs/{run_id}/step11/instructions")
async def submit_image_instructions(
    run_id: str,
    data: InstructionsInput,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, bool]:
    """Submit image instructions for Step11 (Phase 11C).

    Sends step11_submit_instructions signal to Temporal workflow.
    """
    from sqlalchemy import select

    tenant_id = user.tenant_id
    logger.info(
        "Submitting image instructions",
        extra={
            "run_id": run_id,
            "tenant_id": tenant_id,
            "instruction_count": len(data.instructions),
            "user_id": user.user_id,
        },
    )

    db_manager = get_tenant_db_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # Audit log
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="step11_submit_instructions",
                resource_type="run",
                resource_id=run_id,
                details={"instruction_count": len(data.instructions)},
            )

            # Send signal to the appropriate workflow (ArticleWorkflow or ImageAdditionWorkflow)
            if temporal_client is not None:
                try:
                    workflow_handle = await get_step11_workflow_handle(run_id)
                    payload = {
                        "instructions": [i.model_dump() for i in data.instructions],
                    }
                    await workflow_handle.signal("step11_submit_instructions", payload)
                    logger.info("step11_submit_instructions signal sent", extra={"run_id": run_id})
                except Exception as sig_error:
                    logger.error(f"Failed to send signal: {sig_error}", exc_info=True)
                    raise HTTPException(status_code=503, detail=f"Failed to send signal to workflow: {sig_error}")
            else:
                raise HTTPException(status_code=503, detail="Temporal service unavailable")

            await session.flush()

            # WebSocket broadcast
            await ws_manager.broadcast_run_update(
                run_id=run_id,
                event_type="run.step11_instructions_submitted",
                status=run.status,
            )

            return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit instructions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to submit instructions") from e


@app.get("/api/runs/{run_id}/step11/images")
async def get_step11_images(
    run_id: str,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get generated images for Step11 (Phase 11D).

    Returns generated images from storage.
    """
    from sqlalchemy import select

    tenant_id = user.tenant_id

    db_manager = get_tenant_db_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # Load images from storage
            from apps.api.storage.artifact_store import ArtifactStore

            store = ArtifactStore()

            images_bytes = await store.get_by_path(
                tenant_id=tenant_id,
                run_id=run_id,
                step="step11",
                filename="images.json",
            )

            if not images_bytes:
                return {"images": [], "warnings": []}

            images_data = json.loads(images_bytes.decode("utf-8"))

            return {
                "images": images_data.get("generated_images", []),
                "warnings": images_data.get("warnings", []),
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get step11 images: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get images") from e


@app.post("/api/runs/{run_id}/step11/images/review")
async def submit_image_review(
    run_id: str,
    data: ImageReviewInput,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, bool]:
    """Submit image review for Step11 (Phase 11D).

    Sends step11_review_images signal to Temporal workflow.
    """
    from sqlalchemy import select

    tenant_id = user.tenant_id
    logger.info(
        "Submitting image review",
        extra={
            "run_id": run_id,
            "tenant_id": tenant_id,
            "review_count": len(data.reviews),
            "user_id": user.user_id,
        },
    )

    db_manager = get_tenant_db_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # Count retries
            retry_count = sum(1 for r in data.reviews if r.retry)

            # Audit log
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="step11_image_review",
                resource_type="run",
                resource_id=run_id,
                details={
                    "review_count": len(data.reviews),
                    "retry_count": retry_count,
                },
            )

            # Send signal to the appropriate workflow (ArticleWorkflow or ImageAdditionWorkflow)
            if temporal_client is not None:
                try:
                    workflow_handle = await get_step11_workflow_handle(run_id)
                    payload = {
                        "reviews": [r.model_dump() for r in data.reviews],
                    }
                    await workflow_handle.signal("step11_review_images", payload)
                    logger.info("step11_review_images signal sent", extra={"run_id": run_id})
                except Exception as sig_error:
                    logger.error(f"Failed to send signal: {sig_error}", exc_info=True)
                    raise HTTPException(status_code=503, detail=f"Failed to send signal to workflow: {sig_error}")
            else:
                raise HTTPException(status_code=503, detail="Temporal service unavailable")

            await session.flush()

            # WebSocket broadcast
            await ws_manager.broadcast_run_update(
                run_id=run_id,
                event_type="run.step11_images_reviewed",
                status=run.status,
            )

            return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit image review: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to submit image review") from e


@app.get("/api/runs/{run_id}/step11/preview")
async def get_step11_preview(
    run_id: str,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get preview HTML for Step11 (Phase 11E).

    Returns preview HTML with images inserted.
    """
    from sqlalchemy import select

    tenant_id = user.tenant_id

    db_manager = get_tenant_db_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # Load preview from storage
            from apps.api.storage.artifact_store import ArtifactStore

            store = ArtifactStore()

            preview_bytes = await store.get_by_path(
                tenant_id=tenant_id,
                run_id=run_id,
                step="step11",
                filename="preview.html",
            )

            if not preview_bytes:
                return {"preview_html": "", "preview_available": False}

            return {
                "preview_html": preview_bytes.decode("utf-8"),
                "preview_available": True,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get step11 preview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get preview") from e


@app.post("/api/runs/{run_id}/step11/finalize")
async def finalize_step11(
    run_id: str,
    data: FinalizeInput,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, bool]:
    """Finalize Step11 (Phase 11E).

    Sends step11_finalize signal to Temporal workflow.
    """
    from sqlalchemy import select

    tenant_id = user.tenant_id
    logger.info(
        "Finalizing step11",
        extra={
            "run_id": run_id,
            "tenant_id": tenant_id,
            "confirmed": data.confirmed,
            "restart_from": data.restart_from,
            "user_id": user.user_id,
        },
    )

    db_manager = get_tenant_db_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # Audit log
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="step11_finalize",
                resource_type="run",
                resource_id=run_id,
                details={
                    "confirmed": data.confirmed,
                    "restart_from": data.restart_from,
                },
            )

            # Send signal to the appropriate workflow (ArticleWorkflow or ImageAdditionWorkflow)
            if temporal_client is not None:
                try:
                    workflow_handle = await get_step11_workflow_handle(run_id)
                    payload = {
                        "confirmed": data.confirmed,
                        "restart_from": data.restart_from,
                    }
                    await workflow_handle.signal("step11_finalize", payload)
                    logger.info("step11_finalize signal sent", extra={"run_id": run_id})
                except Exception as sig_error:
                    logger.error(f"Failed to send signal: {sig_error}", exc_info=True)
                    raise HTTPException(status_code=503, detail=f"Failed to send signal to workflow: {sig_error}")
            else:
                raise HTTPException(status_code=503, detail="Temporal service unavailable")

            await session.flush()

            # WebSocket broadcast
            event_type = "run.step11_finalized" if data.confirmed else "run.step11_restarting"
            await ws_manager.broadcast_run_update(
                run_id=run_id,
                event_type=event_type,
                status=run.status,
            )

            return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to finalize step11: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to finalize step11") from e


@app.post("/api/runs/{run_id}/retry/{step}")
async def retry_step(
    run_id: str,
    step: str,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Retry a failed step.

    Same conditions only - no fallback to different model/tool.
    Sends retry signal to Temporal workflow.
    """
    import uuid

    from sqlalchemy import select

    tenant_id = user.tenant_id
    logger.info(
        "Retrying step",
        extra={"run_id": run_id, "step": step, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    # Valid step names
    valid_steps = [
        "step0",
        "step1",
        "step2",
        "step3a",
        "step3b",
        "step3c",
        "step4",
        "step5",
        "step6",
        "step6_5",
        "step7a",
        "step7b",
        "step8",
        "step9",
        "step10",
    ]

    # Normalize step name (step6.5 -> step6_5)
    normalized_step = step.replace(".", "_")
    if normalized_step not in valid_steps:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid step: {step}. Valid steps: {', '.join(valid_steps)}",
        )

    db_manager = get_tenant_db_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # 1. Verify run exists and belongs to tenant
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # 2. Verify run is in a retryable status (failed)
            if run.status != RunStatus.FAILED.value:
                raise HTTPException(status_code=400, detail=f"Run must be in failed status to retry (current status: {run.status})")

            # 3. Get step record (if exists) for retry count tracking
            step_query = select(Step).where(
                Step.run_id == run_id,
                Step.step_name == normalized_step.replace("_", "."),
            )
            step_result = await session.execute(step_query)
            step_record = step_result.scalar_one_or_none()

            # Note: We allow retrying from any step when run is failed
            # This enables "retry from this step" and "retry from previous step" functionality

            # 4. Record in audit_logs
            new_attempt_id = str(uuid.uuid4())
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="retry",
                resource_type="step",
                resource_id=f"{run_id}/{step}",
                details={
                    "new_attempt_id": new_attempt_id,
                    "previous_status": run.status,
                },
            )

            # 5. Start new Temporal workflow with resume_from
            # Note: Failed workflows cannot receive signals, so we start a new workflow
            if temporal_client is None:
                raise HTTPException(status_code=503, detail="Temporal client not available")

            try:
                # Load original config
                loaded_config = dict(run.config) if run.config else {}

                # Generate new workflow ID (Temporal requires unique workflow IDs)
                new_workflow_id = f"{run_id}-retry-{new_attempt_id[:8]}"

                await temporal_client.start_workflow(
                    "ArticleWorkflow",
                    args=[tenant_id, run_id, loaded_config, normalized_step],  # resume_from=normalized_step
                    id=new_workflow_id,
                    task_queue=TEMPORAL_TASK_QUEUE,
                )
                logger.info(
                    "Temporal retry workflow started",
                    extra={"run_id": run_id, "step": step, "new_workflow_id": new_workflow_id},
                )
            except Exception as wf_error:
                logger.error(f"Failed to start retry workflow: {wf_error}", exc_info=True)
                raise HTTPException(status_code=503, detail=f"Failed to start retry workflow: {wf_error}")

            # 6. Update run status
            run.status = RunStatus.RUNNING.value
            run.updated_at = datetime.now()

            # Update step status if record exists
            if step_record:
                step_record.status = StepStatus.RUNNING.value
                step_record.retry_count = (step_record.retry_count or 0) + 1

            await session.flush()
            logger.info("Step retry initiated", extra={"run_id": run_id, "step": step})

            # Broadcast retry event via WebSocket
            await ws_manager.broadcast_step_event(
                run_id=run_id,
                step=step,
                event_type="step_retrying",
                status=StepStatus.RUNNING.value,
                message=f"Retrying step {step}",
                attempt=step_record.retry_count if step_record else 1,
            )

            return {"success": True, "new_attempt_id": new_attempt_id}

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to retry step: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retry step") from e


@app.post("/api/runs/{run_id}/resume/{step}")
async def resume_from_step(
    run_id: str,
    step: str,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Resume/restart workflow from a specific step.

    Loads artifacts from completed steps and starts a new workflow from the specified step.
    Uses the same run_id (overwrites failed workflow) rather than creating a new one.

    Args:
        run_id: Original run ID to resume
        step: Step to resume from (e.g., "step9")

    Returns:
        { success: bool, run_id: str, resume_from: str }
    """
    import uuid

    from sqlalchemy import select

    tenant_id = user.tenant_id
    logger.info(
        "Resuming run",
        extra={"run_id": run_id, "step": step, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    # Step order for validation and loading
    step_order = [
        "step0",
        "step1",
        "step2",
        "step3a",
        "step3b",
        "step3c",
        "step4",
        "step5",
        "step6",
        "step6_5",
        "step7a",
        "step7b",
        "step8",
        "step9",
        "step10",
    ]

    # Validate step name
    if step not in step_order:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid step: {step}. Valid steps: {', '.join(step_order)}",
        )

    db_manager = get_tenant_db_manager()
    artifact_store = ArtifactStore()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # 1. Verify original run exists and belongs to tenant
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            original_run = result.scalar_one_or_none()

            if not original_run:
                raise HTTPException(status_code=404, detail="Run not found")

            # 2. Load artifacts from completed steps (before resume_from)
            step_index = step_order.index(step)
            steps_to_load = step_order[:step_index]

            # Build config with loaded step data
            # config is already a dict (JSON column), no json.loads needed
            loaded_config = dict(original_run.config) if original_run.config else {}

            for prev_step in steps_to_load:
                artifact_data = await artifact_store.get_by_path(
                    tenant_id=tenant_id,
                    run_id=run_id,
                    step=prev_step,
                )
                if artifact_data:
                    step_data = json.loads(artifact_data.decode("utf-8"))
                    loaded_config[f"{prev_step}_data"] = step_data
                    logger.debug(f"Loaded artifact for {prev_step}")

            # 3. Delete artifacts for steps after resume point
            steps_to_delete = step_order[step_index:]  # Include current step and all subsequent
            # Also include step11 which is not in step_order but may exist
            steps_to_delete_with_step11 = steps_to_delete + ["step11"]

            deleted_artifacts_count = 0
            for step_to_delete in steps_to_delete_with_step11:
                count = await artifact_store.delete_step_artifacts(
                    tenant_id=tenant_id,
                    run_id=run_id,
                    step=step_to_delete,
                )
                deleted_artifacts_count += count

            if deleted_artifacts_count > 0:
                logger.info(
                    f"Deleted {deleted_artifacts_count} artifacts for resume",
                    extra={
                        "run_id": run_id,
                        "resume_from": step,
                        "deleted_steps": steps_to_delete_with_step11,
                    },
                )

            # 4. Update step statuses in DB
            # - Steps before resume point: mark as completed
            # - Steps at and after resume point: delete records (will be recreated by workflow)
            from sqlalchemy import delete as sql_delete

            from apps.api.db.models import Step

            # Delete step records for steps at and after resume point
            await session.execute(
                sql_delete(Step).where(
                    Step.run_id == run_id,
                    Step.step_name.in_(steps_to_delete_with_step11),
                )
            )

            # Mark all prior steps as completed
            for prev_step in steps_to_load:
                step_query = select(Step).where(
                    Step.run_id == run_id,
                    Step.step_name == prev_step,
                )
                step_result = await session.execute(step_query)
                step_record = step_result.scalar_one_or_none()

                if step_record:
                    step_record.status = StepStatus.COMPLETED.value
                    if not step_record.completed_at:
                        step_record.completed_at = datetime.now()
                else:
                    # Create completed step record if it doesn't exist
                    new_step = Step(
                        run_id=run_id,
                        step_name=prev_step,
                        status=StepStatus.COMPLETED.value,
                        started_at=datetime.now(),
                        completed_at=datetime.now(),
                        retry_count=0,
                    )
                    session.add(new_step)

            logger.info(
                "Updated step statuses for resume",
                extra={
                    "run_id": run_id,
                    "completed_steps": steps_to_load,
                    "deleted_step_records": steps_to_delete_with_step11,
                },
            )

            # 5. Start new Temporal workflow with resume_from
            if temporal_client is None:
                raise HTTPException(
                    status_code=503,
                    detail="Temporal client not available",
                )

            # Generate new workflow run ID (Temporal requires unique workflow IDs)
            new_workflow_id = f"{run_id}-resume-{uuid.uuid4().hex[:8]}"

            await temporal_client.start_workflow(
                "ArticleWorkflow",
                args=[tenant_id, run_id, loaded_config, step],  # resume_from=step
                id=new_workflow_id,
                task_queue=TEMPORAL_TASK_QUEUE,
            )

            # Update run status and current step, clear error state
            now = datetime.now()
            original_run.status = RunStatus.RUNNING.value
            original_run.current_step = step
            original_run.error_message = None
            original_run.error_code = None
            original_run.completed_at = None
            original_run.updated_at = now

            # Log audit entry
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="resume",
                resource_type="run",
                resource_id=run_id,
                details={
                    "resume_from": step,
                    "workflow_id": new_workflow_id,
                    "deleted_artifacts_count": deleted_artifacts_count,
                    "deleted_steps": steps_to_delete_with_step11,
                },
            )

            await session.commit()

            logger.info(
                "Run resumed",
                extra={
                    "run_id": run_id,
                    "resume_from": step,
                    "workflow_id": new_workflow_id,
                    "loaded_steps": steps_to_load,
                },
            )

            return {
                "success": True,
                "new_run_id": run_id,  # Frontend expects new_run_id
                "resume_from": step,
                "workflow_id": new_workflow_id,
                "loaded_steps": steps_to_load,
                "deleted_artifacts_count": deleted_artifacts_count,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to resume run: {e}") from e


class CloneRunInput(BaseModel):
    """Request body for cloning a run with optional overrides."""

    keyword: str | None = None
    target_audience: str | None = None
    competitor_urls: list[str] | None = None
    additional_requirements: str | None = None
    model_config_override: ModelConfig | None = Field(None, alias="model_config")
    start_workflow: bool = True

    class Config:
        populate_by_name = True


@app.post("/api/runs/{run_id}/clone", response_model=RunResponse)
async def clone_run(
    run_id: str,
    data: CloneRunInput | None = None,
    user: AuthUser = Depends(get_current_user),
) -> RunResponse:
    """Clone an existing run with optional config overrides.

    Creates a new run based on an existing run's configuration.
    Optionally overrides specific input fields.
    """
    import uuid

    from sqlalchemy import select

    tenant_id = user.tenant_id
    logger.info(
        "Cloning run",
        extra={"run_id": run_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    db_manager = get_tenant_db_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # 1. Verify original run exists and belongs to tenant
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            original_run = result.scalar_one_or_none()

            if not original_run:
                raise HTTPException(status_code=404, detail="Run not found")

            # 2. Copy run config from original
            original_input = original_run.input_data or {}
            original_config = original_run.config or {}

            # Build new input with optional overrides
            new_input = {
                "keyword": (data.keyword if data and data.keyword else original_input.get("keyword", "")),
                "target_audience": (data.target_audience if data and data.target_audience else original_input.get("target_audience")),
                "competitor_urls": (data.competitor_urls if data and data.competitor_urls else original_input.get("competitor_urls")),
                "additional_requirements": (
                    data.additional_requirements if data and data.additional_requirements else original_input.get("additional_requirements")
                ),
            }

            # Copy model config with optional override
            if data and data.model_config_override:
                new_model_config = data.model_config_override.model_dump()
            else:
                new_model_config = original_config.get(
                    "model_config",
                    {
                        "platform": "gemini",
                        "model": "gemini-1.5-pro",
                        "options": {},
                    },
                )

            # Build new workflow config
            new_workflow_config = {
                "model_config": new_model_config,
                "step_configs": original_config.get("step_configs"),
                "tool_config": original_config.get("tool_config"),
                "options": original_config.get("options"),
                "pack_id": original_config.get("pack_id", "default"),
                "input": new_input,
                # Step activities expect these at top level
                "keyword": new_input["keyword"],
                "target_audience": new_input.get("target_audience"),
                "competitor_urls": new_input.get("competitor_urls"),
                "additional_requirements": new_input.get("additional_requirements"),
            }

            # 3. Create new run
            new_run_id = str(uuid.uuid4())
            now = datetime.now()

            new_run = Run(
                id=new_run_id,
                tenant_id=tenant_id,
                status=RunStatus.PENDING.value,
                current_step=None,
                input_data=new_input,
                config=new_workflow_config,
                created_at=now,
                updated_at=now,
            )
            session.add(new_run)

            # 4. Log audit entry
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="clone",
                resource_type="run",
                resource_id=new_run_id,
                details={
                    "source_run_id": run_id,
                    "keyword": new_input["keyword"],
                    "start_workflow": data.start_workflow if data else True,
                },
            )

            await session.flush()
            logger.info(
                "Run cloned",
                extra={"new_run_id": new_run_id, "source_run_id": run_id, "tenant_id": tenant_id},
            )

            # 5. Optionally start Temporal workflow
            start_workflow = data.start_workflow if data else True
            if start_workflow and temporal_client is not None:
                try:
                    await temporal_client.start_workflow(
                        "ArticleWorkflow",
                        args=[tenant_id, new_run_id, new_workflow_config, None],
                        id=new_run_id,
                        task_queue=TEMPORAL_TASK_QUEUE,
                    )

                    new_run.status = RunStatus.RUNNING.value
                    new_run.started_at = now
                    new_run.updated_at = now

                    logger.info(
                        "Cloned workflow started",
                        extra={"run_id": new_run_id, "task_queue": TEMPORAL_TASK_QUEUE},
                    )

                    await ws_manager.broadcast_run_update(
                        run_id=new_run_id,
                        event_type="run.started",
                        status=RunStatus.RUNNING.value,
                    )

                except Exception as wf_error:
                    logger.error(f"Failed to start cloned workflow: {wf_error}", exc_info=True)
                    new_run.status = RunStatus.FAILED.value
                    new_run.error_code = "WORKFLOW_START_FAILED"
                    new_run.error_message = str(wf_error)
                    new_run.updated_at = now

            return _run_orm_to_response(new_run)

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to clone run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to clone run") from e


@app.delete("/api/runs/{run_id}")
async def cancel_run(run_id: str, user: AuthUser = Depends(get_current_user)) -> dict[str, bool]:
    """Cancel a running workflow."""
    from sqlalchemy import select

    tenant_id = user.tenant_id
    logger.info(
        "Cancelling run",
        extra={"run_id": run_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    db_manager = get_tenant_db_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # 1. Verify run exists and belongs to tenant
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # 2. Verify run is in a cancellable status
            cancellable_statuses = [
                RunStatus.PENDING.value,
                RunStatus.RUNNING.value,
                RunStatus.WAITING_APPROVAL.value,
            ]
            if run.status not in cancellable_statuses:
                raise HTTPException(status_code=400, detail=f"Run cannot be cancelled (current status: {run.status})")

            # 3. Record in audit_logs
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="cancel",
                resource_type="run",
                resource_id=run_id,
                details={"previous_status": run.status},
            )

            # 4. Cancel Temporal workflow if running
            if temporal_client is not None:
                try:
                    workflow_handle = temporal_client.get_workflow_handle(run_id)
                    await workflow_handle.cancel()
                    logger.info("Temporal workflow cancelled", extra={"run_id": run_id})
                except Exception as cancel_error:
                    logger.warning(f"Failed to cancel Temporal workflow: {cancel_error}")
                    # Continue anyway - DB state is updated
            else:
                logger.warning(
                    "Temporal client not available, workflow not cancelled",
                    extra={"run_id": run_id},
                )

            # 5. Update run status
            run.status = RunStatus.CANCELLED.value
            run.updated_at = datetime.now()
            run.completed_at = datetime.now()

            await session.flush()
            logger.info("Run cancelled", extra={"run_id": run_id, "tenant_id": tenant_id})

            # Broadcast cancellation event via WebSocket
            await ws_manager.broadcast_run_update(
                run_id=run_id,
                event_type="run.cancelled",
                status=RunStatus.CANCELLED.value,
            )

            return {"success": True}

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to cancel run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to cancel run") from e


@app.delete("/api/runs/{run_id}/delete")
async def delete_run(run_id: str, user: AuthUser = Depends(get_current_user)) -> dict[str, bool]:
    """Delete a completed, failed, or cancelled run."""
    from sqlalchemy import delete as sql_delete
    from sqlalchemy import select

    tenant_id = user.tenant_id
    logger.info(
        "Deleting run",
        extra={"run_id": run_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    db_manager = get_tenant_db_manager()
    store = get_artifact_store()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # 1. Verify run exists and belongs to tenant
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # 2. Verify run is in a deletable status (not running)
            deletable_statuses = [
                RunStatus.COMPLETED.value,
                RunStatus.FAILED.value,
                RunStatus.CANCELLED.value,
                RunStatus.WAITING_IMAGE_INPUT.value,
                RunStatus.WAITING_APPROVAL.value,
            ]
            if run.status not in deletable_statuses:
                raise HTTPException(
                    status_code=400, detail=f"Run cannot be deleted while in progress (current status: {run.status}). Cancel it first."
                )

            # 3. Record in audit_logs before deletion
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="delete",
                resource_type="run",
                resource_id=run_id,
                details={"status": run.status, "keyword": run.input_data.get("keyword") if run.input_data else None},
            )

            # 4. Delete artifacts from storage
            try:
                deleted_count = await store.delete_run_artifacts(tenant_id, run_id)
                logger.info(f"Deleted {deleted_count} artifacts from storage", extra={"run_id": run_id})
            except Exception as storage_error:
                logger.warning(f"Failed to delete some artifacts from storage: {storage_error}")
                # Continue with DB deletion anyway

            # 5. Delete related records from DB
            # Delete artifacts
            await session.execute(sql_delete(ArtifactModel).where(ArtifactModel.run_id == run_id))

            # Delete steps
            await session.execute(sql_delete(Step).where(Step.run_id == run_id))

            # Delete the run itself
            await session.delete(run)

            await session.flush()
            logger.info("Run deleted", extra={"run_id": run_id, "tenant_id": tenant_id})

            return {"success": True}

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to delete run: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete run") from e


class BulkDeleteRequest(BaseModel):
    """Request body for bulk delete."""

    run_ids: list[str]


class BulkDeleteResponse(BaseModel):
    """Response for bulk delete."""

    deleted: list[str]
    failed: list[dict[str, str]]  # [{"id": "...", "error": "..."}]


@app.post("/api/runs/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_runs(
    request: BulkDeleteRequest,
    user: AuthUser = Depends(get_current_user),
) -> BulkDeleteResponse:
    """Delete multiple runs. Running/pending/waiting runs are cancelled first."""
    from sqlalchemy import delete as sql_delete
    from sqlalchemy import select

    tenant_id = user.tenant_id
    logger.info(
        "Bulk deleting runs",
        extra={"run_ids": request.run_ids, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    db_manager = get_tenant_db_manager()
    store = get_artifact_store()

    deleted: list[str] = []
    failed: list[dict[str, str]] = []

    # Statuses that need to be cancelled before deletion
    cancellable_statuses = [
        RunStatus.PENDING.value,
        RunStatus.RUNNING.value,
        RunStatus.WAITING_APPROVAL.value,
    ]

    try:
        async with db_manager.get_session(tenant_id) as session:
            for run_id in request.run_ids:
                try:
                    # 1. Verify run exists and belongs to tenant
                    query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
                    result = await session.execute(query)
                    run = result.scalar_one_or_none()

                    if not run:
                        failed.append({"id": run_id, "error": "Run not found"})
                        continue

                    # 2. If running/pending/waiting, cancel first
                    if run.status in cancellable_statuses:
                        # Cancel Temporal workflow if running
                        if temporal_client is not None:
                            try:
                                workflow_handle = temporal_client.get_workflow_handle(run_id)
                                await workflow_handle.cancel()
                                logger.info("Temporal workflow cancelled for bulk delete", extra={"run_id": run_id})
                            except Exception as cancel_error:
                                logger.warning(f"Failed to cancel Temporal workflow {run_id}: {cancel_error}")

                        # Update status to cancelled
                        run.status = RunStatus.CANCELLED.value
                        run.updated_at = datetime.utcnow()
                        await session.flush()

                        # Log cancellation
                        audit = AuditLogger(session)
                        await audit.log(
                            user_id=user.user_id,
                            action="cancel",
                            resource_type="run",
                            resource_id=run_id,
                            details={"previous_status": run.status, "bulk": True, "reason": "bulk_delete"},
                        )

                    # 3. Record deletion in audit_logs
                    audit = AuditLogger(session)
                    await audit.log(
                        user_id=user.user_id,
                        action="delete",
                        resource_type="run",
                        resource_id=run_id,
                        details={"status": run.status, "bulk": True},
                    )

                    # 4. Delete artifacts from storage
                    try:
                        await store.delete_run_artifacts(tenant_id, run_id)
                    except Exception as storage_error:
                        logger.warning(f"Failed to delete artifacts for {run_id}: {storage_error}")

                    # 5. Delete related records from DB
                    await session.execute(sql_delete(ArtifactModel).where(ArtifactModel.run_id == run_id))
                    await session.execute(sql_delete(Step).where(Step.run_id == run_id))
                    await session.delete(run)

                    deleted.append(run_id)

                except Exception as e:
                    logger.error(f"Failed to delete run {run_id}: {e}")
                    failed.append({"id": run_id, "error": str(e)})

            # Commit all changes at once
            await session.flush()

        logger.info(f"Bulk delete completed: {len(deleted)} deleted, {len(failed)} failed")
        return BulkDeleteResponse(deleted=deleted, failed=failed)

    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to bulk delete runs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to bulk delete runs") from e


# =============================================================================
# Internal API Endpoints (for Worker communication)
# =============================================================================


@app.post("/api/internal/steps/update")
async def update_step_status(request: StepUpdateRequest) -> dict[str, bool]:
    """Update step status in DB (internal API for Worker).

    This endpoint is called by Temporal Worker to record step progress.
    No authentication required - assumes Docker network isolation.
    """
    from sqlalchemy import text

    logger.info(
        "Updating step status",
        extra={
            "run_id": request.run_id,
            "step_name": request.step_name,
            "status": request.status,
        },
    )

    db_manager = get_tenant_db_manager()

    try:
        # Get tenant_id from run
        # Note: We use dev-tenant-001 for now since internal API doesn't have auth context
        # TODO: Pass tenant_id from Worker or look up from run
        tenant_id = "dev-tenant-001"

        async with db_manager.get_session(tenant_id) as session:
            # UPSERT step record
            # Note: Cast :status to VARCHAR to avoid asyncpg type inference issues
            # (inconsistent types: text vs character varying)
            await session.execute(
                text("""
                    INSERT INTO steps (id, run_id, step_name, status, started_at, retry_count)
                    VALUES (
                        gen_random_uuid(),
                        CAST(:run_id AS UUID),
                        CAST(:step_name AS VARCHAR),
                        CAST(:status AS VARCHAR),
                        CASE WHEN CAST(:status AS VARCHAR) = 'running' THEN NOW() ELSE NULL END,
                        :retry_count
                    )
                    ON CONFLICT (run_id, step_name)
                    DO UPDATE SET
                        status = CAST(:status AS VARCHAR),
                        started_at = CASE
                            WHEN CAST(:status AS VARCHAR) = 'running' THEN NOW()
                            ELSE steps.started_at
                        END,
                        completed_at = CASE
                            WHEN CAST(:status AS VARCHAR) IN ('completed', 'failed') THEN NOW()
                            ELSE NULL
                        END,
                        error_message = :error_message,
                        retry_count = :retry_count
                """),
                {
                    "run_id": request.run_id,
                    "step_name": request.step_name,
                    "status": request.status,
                    "error_message": request.error_message,
                    "retry_count": request.retry_count,
                },
            )
            await session.commit()

        return {"ok": True}

    except Exception as e:
        logger.error(f"Failed to update step status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update step status") from e


# =============================================================================
# Artifact Endpoints
# =============================================================================


@app.get("/api/runs/{run_id}/files", response_model=list[ArtifactRef])
async def list_artifacts(run_id: str, user: AuthUser = Depends(get_current_user)) -> list[ArtifactRef]:
    """List all artifacts for a run.

    Falls back to MinIO listing if DB artifacts table is empty.
    """
    from datetime import datetime

    from sqlalchemy import select

    tenant_id = user.tenant_id
    logger.debug(
        "Listing artifacts",
        extra={"run_id": run_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    db_manager = get_tenant_db_manager()
    store = get_artifact_store()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # Verify run belongs to tenant
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # Build step_id -> step_name mapping
            steps_query = select(Step).where(Step.run_id == run_id)
            steps_result = await session.execute(steps_query)
            steps = steps_result.scalars().all()
            step_id_to_name = {str(s.id): s.step_name for s in steps}

            # Query artifacts from DB
            artifact_query = select(ArtifactModel).where(ArtifactModel.run_id == run_id)
            artifact_result = await session.execute(artifact_query)
            artifacts = artifact_result.scalars().all()

            # If DB has artifacts, return them
            if artifacts:
                return [
                    ArtifactRef(
                        id=str(a.id),
                        step_id=str(a.step_id) if a.step_id else "",
                        step_name=step_id_to_name.get(str(a.step_id), "") if a.step_id else "",
                        ref_path=a.ref_path,
                        digest=a.digest or "",
                        content_type=a.content_type or a.artifact_type,
                        size_bytes=a.size_bytes or 0,
                        created_at=a.created_at.isoformat(),
                    )
                    for a in artifacts
                ]

            # Fallback: List artifacts directly from MinIO storage
            logger.info(f"No artifacts in DB for run {run_id}, listing from MinIO")
            try:
                paths = await store.list_run_artifacts(tenant_id, run_id)
                artifact_refs = []

                for path in paths:
                    # Parse path: storage/{tenant_id}/{run_id}/{step}/{filename}
                    parts = path.split("/")
                    if len(parts) >= 5:
                        step_name = parts[3]
                        filename = parts[4]

                        # Skip non-output files (checkpoints, metadata)
                        if filename.startswith("checkpoint_") or filename == "metadata.json":
                            continue
                        # Only include output files (output.json, .html, .md)
                        if not (filename.endswith(".json") or filename.endswith(".html") or filename.endswith(".md")):
                            continue

                        # Get file stat from MinIO for size
                        try:
                            stat = store.client.stat_object(store.bucket, path)
                            size_bytes = stat.size if stat.size is not None else 0
                            created_at = stat.last_modified.isoformat() if stat.last_modified else datetime.now().isoformat()
                        except Exception:
                            size_bytes = 0
                            created_at = datetime.now().isoformat()

                        # Determine content type
                        content_type = "application/json"
                        if filename.endswith(".html"):
                            content_type = "text/html"
                        elif filename.endswith(".md"):
                            content_type = "text/markdown"

                        artifact_refs.append(
                            ArtifactRef(
                                id=f"{run_id}:{step_name}:{filename}",  # Synthetic ID
                                step_id="",
                                step_name=step_name,
                                ref_path=path,
                                digest="",  # Not available without reading file
                                content_type=content_type,
                                size_bytes=size_bytes,
                                created_at=created_at,
                            )
                        )

                return artifact_refs
            except Exception as e:
                logger.warning(f"Failed to list from MinIO: {e}")
                return []

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to list artifacts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list artifacts") from e


@app.get("/api/runs/{run_id}/files/{step}", response_model=list[ArtifactRef])
async def get_step_artifacts(
    run_id: str,
    step: str,
    user: AuthUser = Depends(get_current_user),
) -> list[ArtifactRef]:
    """Get artifacts for a specific step."""
    from sqlalchemy import select

    tenant_id = user.tenant_id
    logger.debug(
        "Getting step artifacts",
        extra={"run_id": run_id, "step": step, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    db_manager = get_tenant_db_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # Verify run belongs to tenant
            run_query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            run_result = await session.execute(run_query)
            run = run_result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # Build step_id -> step_name mapping
            steps_query = select(Step).where(Step.run_id == run_id)
            steps_result = await session.execute(steps_query)
            steps = steps_result.scalars().all()
            step_id_to_name = {str(s.id): s.step_name for s in steps}

            # Query artifacts for specific step (via step_id -> steps.step_name)
            # First, find step by name
            step_query = select(Step).where(
                Step.run_id == run_id,
                Step.step_name == step,
            )
            step_result = await session.execute(step_query)
            step_record = step_result.scalar_one_or_none()

            if step_record:
                # Query artifacts by step_id
                artifact_query = select(ArtifactModel).where(
                    ArtifactModel.run_id == run_id,
                    ArtifactModel.step_id == step_record.id,
                )
            else:
                # Fallback: query all artifacts and filter by artifact_type containing step name
                artifact_query = select(ArtifactModel).where(
                    ArtifactModel.run_id == run_id,
                )

            artifact_result = await session.execute(artifact_query)
            artifacts = artifact_result.scalars().all()

            return [
                ArtifactRef(
                    id=str(a.id),
                    step_id=str(a.step_id) if a.step_id else "",
                    step_name=step_id_to_name.get(str(a.step_id), "") if a.step_id else "",
                    ref_path=a.ref_path,
                    digest=a.digest or "",
                    content_type=a.content_type or a.artifact_type,
                    size_bytes=a.size_bytes or 0,
                    created_at=a.created_at.isoformat(),
                )
                for a in artifacts
            ]

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to get step artifacts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get step artifacts") from e


@app.get("/api/runs/{run_id}/files/{artifact_id}/content", response_model=ArtifactContent)
async def get_artifact_content(
    run_id: str,
    artifact_id: str,
    user: AuthUser = Depends(get_current_user),
) -> ArtifactContent:
    """Get artifact content by ID.

    Supports both DB artifact IDs (UUID) and synthetic MinIO IDs ({run_id}:{step}:{filename}).
    """
    import base64
    from datetime import datetime

    from sqlalchemy import select

    tenant_id = user.tenant_id
    logger.debug(
        "Getting artifact content",
        extra={"run_id": run_id, "artifact_id": artifact_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    db_manager = get_tenant_db_manager()
    store = get_artifact_store()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # Verify run belongs to tenant
            run_query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            run_result = await session.execute(run_query)
            run = run_result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # Check if artifact_id is a synthetic MinIO ID (format: {run_id}:{step}:{filename})
            if ":" in artifact_id:
                # Parse synthetic ID
                parts = artifact_id.split(":", 2)
                if len(parts) == 3:
                    _, step_name, filename = parts
                    ref_path = f"storage/{tenant_id}/{run_id}/{step_name}/{filename}"

                    # Get content directly from MinIO
                    try:
                        content_bytes = await store.get_by_path(tenant_id, run_id, step_name, filename)
                        if content_bytes is None:
                            raise HTTPException(status_code=404, detail="Artifact not found in storage")
                    except ArtifactStoreError:
                        raise HTTPException(status_code=404, detail="Artifact not found in storage")

                    # Decode content
                    try:
                        content = content_bytes.decode("utf-8")
                        encoding = "utf-8"
                    except UnicodeDecodeError:
                        content = base64.b64encode(content_bytes).decode("ascii")
                        encoding = "base64"

                    # Determine content type
                    content_type = "application/json"
                    if filename.endswith(".html"):
                        content_type = "text/html"
                    elif filename.endswith(".md"):
                        content_type = "text/markdown"

                    # Get file stat for size
                    try:
                        stat = store.client.stat_object(store.bucket, ref_path)
                        size_bytes = stat.size if stat.size is not None else len(content_bytes)
                        created_at = stat.last_modified.isoformat() if stat.last_modified else datetime.now().isoformat()
                    except Exception:
                        size_bytes = len(content_bytes)
                        created_at = datetime.now().isoformat()

                    return ArtifactContent(
                        ref=ArtifactRef(
                            id=artifact_id,
                            step_id="",
                            step_name=step_name,
                            ref_path=ref_path,
                            digest="",
                            content_type=content_type,
                            size_bytes=size_bytes,
                            created_at=created_at,
                        ),
                        content=content,
                        encoding=encoding,
                    )

            # Standard DB artifact lookup
            artifact_query = (
                select(ArtifactModel)
                .join(Run, ArtifactModel.run_id == Run.id)
                .where(
                    ArtifactModel.id == artifact_id,
                    Run.id == run_id,
                    Run.tenant_id == tenant_id,
                )
            )
            artifact_result = await session.execute(artifact_query)
            artifact = artifact_result.scalar_one_or_none()

            if not artifact:
                raise HTTPException(status_code=404, detail="Artifact not found")

            # Get content from storage with tenant check
            storage_ref = StorageArtifactRef(
                path=artifact.ref_path,
                digest=artifact.digest or "",
                content_type=artifact.content_type or artifact.artifact_type,
                size_bytes=artifact.size_bytes or 0,
                created_at=artifact.created_at,
            )

            try:
                content_bytes = await store.get_with_tenant_check(
                    tenant_id=tenant_id,
                    ref=storage_ref,
                    verify=True,
                )
            except ArtifactNotFoundError:
                raise HTTPException(status_code=404, detail="Artifact content not found in storage")

            try:
                content = content_bytes.decode("utf-8")
                encoding = "utf-8"
            except UnicodeDecodeError:
                content = base64.b64encode(content_bytes).decode("ascii")
                encoding = "base64"

            # Log download for audit
            audit = AuditLogger(session)
            await audit.log(
                user_id=user.user_id,
                action="download",
                resource_type="artifact",
                resource_id=artifact_id,
                details={"run_id": run_id, "step_id": artifact.step_id},
            )

            # Get step_name if step_id is available
            step_name = ""
            if artifact.step_id:
                step_query = select(Step).where(Step.id == artifact.step_id)
                step_result = await session.execute(step_query)
                step_record = step_result.scalar_one_or_none()
                if step_record:
                    step_name = step_record.step_name

            return ArtifactContent(
                ref=ArtifactRef(
                    id=str(artifact.id),
                    step_id=str(artifact.step_id) if artifact.step_id else "",
                    step_name=step_name,
                    ref_path=artifact.ref_path,
                    digest=artifact.digest or "",
                    content_type=artifact.content_type or artifact.artifact_type,
                    size_bytes=artifact.size_bytes or 0,
                    created_at=artifact.created_at.isoformat(),
                ),
                content=content,
                encoding=encoding,
            )

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except ArtifactStoreError as e:
        logger.error(f"Storage error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve artifact content") from e
    except Exception as e:
        logger.error(f"Failed to get artifact content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get artifact content") from e


@app.get("/api/runs/{run_id}/preview", response_class=HTMLResponse)
async def get_run_preview(
    run_id: str,
    article: int = Query(default=1, ge=1, le=4, description="記事番号 (1-4)"),
    user: AuthUser = Depends(get_current_user),
) -> HTMLResponse:
    """Get HTML preview of generated article.

    Args:
        run_id: Run ID
        article: Article number (1-4) for multi-article support
        user: Authenticated user
    """
    from sqlalchemy import select

    tenant_id = user.tenant_id
    logger.debug(
        "Getting preview",
        extra={"run_id": run_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    db_manager = get_tenant_db_manager()
    store = get_artifact_store()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # Verify run belongs to tenant
            run_query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            run_result = await session.execute(run_query)
            run = run_result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            html_content = None

            # First priority: Step11 output with images (if completed)
            step11_state = run.step11_state or {}
            if step11_state.get("phase") == "completed":
                try:
                    # Step11 uses a different path convention: tenants/{tenant_id}/runs/{run_id}/step11/output.json
                    step11_path = f"tenants/{tenant_id}/runs/{run_id}/step11/output.json"
                    response = store.client.get_object(
                        bucket_name=store.bucket,
                        object_name=step11_path,
                    )
                    step11_bytes = response.read()
                    response.close()
                    response.release_conn()

                    if step11_bytes:
                        import json

                        step11_data = json.loads(step11_bytes.decode("utf-8"))
                        html_content = step11_data.get("html_with_images")
                        if html_content:
                            logger.debug("Found HTML with images at step11/output.json")
                except Exception as e:
                    logger.debug(f"Could not get step11 output: {e}")

            # Second priority: step10/preview.html
            if not html_content:
                try:
                    content_bytes = await store.get_by_path(
                        tenant_id=tenant_id,
                        run_id=run_id,
                        step="step10",
                        filename="preview.html",
                    )
                    if content_bytes:
                        html_content = content_bytes.decode("utf-8")
                        logger.debug("Found HTML preview at step10/preview.html")
                except Exception:
                    # Fallback: look for HTML artifact in DB (legacy support)
                    logger.debug("No preview.html at step10, checking DB artifacts")

            if not html_content:
                # Look for HTML artifact from final step in DB
                artifact_query = (
                    select(ArtifactModel)
                    .where(
                        ArtifactModel.run_id == run_id,
                        ArtifactModel.content_type.in_(["text/html", "html"]),
                    )
                    .order_by(ArtifactModel.created_at.desc())
                    .limit(1)
                )
                artifact_result = await session.execute(artifact_query)
                artifact = artifact_result.scalar_one_or_none()

                if not artifact:
                    # Final fallback: try to extract html_content from step10/output.json
                    try:
                        output_bytes = await store.get_by_path(
                            tenant_id=tenant_id,
                            run_id=run_id,
                            step="step10",
                            filename="output.json",
                        )
                        if output_bytes:
                            import json

                            output_data = json.loads(output_bytes.decode("utf-8"))

                            # Multi-article support: check for articles array
                            articles = output_data.get("articles", [])
                            if articles and article <= len(articles):
                                # Get specific article by number
                                target_article = articles[article - 1]
                                html_content = target_article.get("html_content", target_article.get("content", ""))
                                if html_content:
                                    logger.debug(f"Extracted article {article} html_content from step10/output.json")
                            elif not articles:
                                # Fallback to legacy single article format
                                html_content = output_data.get("html_content")
                                if html_content:
                                    logger.debug("Extracted html_content from step10/output.json (legacy)")
                    except Exception as e:
                        logger.debug(f"Could not extract from output.json: {e}")

                if not html_content and artifact:
                    # Get content from DB artifact reference
                    storage_ref = StorageArtifactRef(
                        path=artifact.ref_path,
                        digest=artifact.digest or "",
                        content_type=artifact.content_type or "text/html",
                        size_bytes=artifact.size_bytes or 0,
                        created_at=artifact.created_at,
                    )

                    try:
                        content_bytes = await store.get_with_tenant_check(
                            tenant_id=tenant_id,
                            ref=storage_ref,
                            verify=True,
                        )
                        html_content = content_bytes.decode("utf-8")
                    except ArtifactNotFoundError:
                        pass

            if not html_content:
                raise HTTPException(status_code=404, detail="Preview not available")

            return HTMLResponse(content=html_content)

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to get preview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get preview") from e


# =============================================================================
# Events Endpoint
# =============================================================================


@app.get("/api/runs/{run_id}/events", response_model=list[EventResponse])
async def list_events(
    run_id: str,
    step: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    user: AuthUser = Depends(get_current_user),
) -> list[EventResponse]:
    """List events/audit logs for a run."""
    from sqlalchemy import select

    tenant_id = user.tenant_id
    logger.debug(
        "Listing events",
        extra={"run_id": run_id, "tenant_id": tenant_id, "step": step, "user_id": user.user_id},
    )

    db_manager = get_tenant_db_manager()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # Verify run belongs to tenant
            run_query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            run_result = await session.execute(run_query)
            run = run_result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # Query audit logs for this run
            audit = AuditLogger(session)
            logs = await audit.get_logs(
                resource_type="run",
                resource_id=run_id,
                limit=limit,
            )

            # Also get artifact-related logs for this run
            artifact_logs = await audit.get_logs(
                resource_type="artifact",
                limit=limit,
            )
            # Filter artifact logs that belong to this run
            artifact_logs = [log for log in artifact_logs if log.details and log.details.get("run_id") == run_id]

            # Combine and sort by created_at
            all_logs = logs + artifact_logs
            all_logs.sort(key=lambda x: x.created_at, reverse=True)

            # Apply step filter if provided
            if step:
                all_logs = [log for log in all_logs if log.details and log.details.get("step") == step]

            return [
                EventResponse(
                    id=str(log.id),
                    event_type=log.action,
                    payload={
                        "user_id": log.user_id,
                        "resource_type": log.resource_type,
                        "resource_id": log.resource_id,
                        "details": log.details,
                        "entry_hash": log.entry_hash[:16] + "...",
                    },
                    created_at=log.created_at.isoformat(),
                )
                for log in all_logs[:limit]
            ]

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to list events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list events") from e


# =============================================================================
# Configuration Endpoints - Models and Workflow Settings
# =============================================================================


class ProviderConfig(BaseModel):
    """Provider configuration with available models."""

    provider: str
    default_model: str
    available_models: list[str]
    supports_grounding: bool = False


class StepDefaultConfig(BaseModel):
    """Default configuration for a workflow step."""

    step_id: str
    label: str
    description: str
    ai_model: str  # gemini, openai, anthropic
    model_name: str
    temperature: float
    grounding: bool
    retry_limit: int
    repair_enabled: bool
    is_configurable: bool
    recommended_model: str


class ModelsConfigResponse(BaseModel):
    """Response for GET /api/config/models."""

    providers: list[ProviderConfig]
    step_defaults: list[StepDefaultConfig]


# Step default configurations (source of truth for FE)
WORKFLOW_STEP_DEFAULTS: list[StepDefaultConfig] = [
    StepDefaultConfig(
        step_id="step-1",
        label="入力",
        description="キーワードとターゲット情報の入力",
        ai_model="gemini",
        model_name=os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash"),
        temperature=0.7,
        grounding=False,
        retry_limit=3,
        repair_enabled=True,
        is_configurable=False,
        recommended_model="gemini",
    ),
    StepDefaultConfig(
        step_id="step0",
        label="キーワード選定",
        description="キーワードの分析と最適化",
        ai_model="gemini",
        model_name=os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash"),
        temperature=0.7,
        grounding=True,
        retry_limit=3,
        repair_enabled=True,
        is_configurable=True,
        recommended_model="gemini",
    ),
    StepDefaultConfig(
        step_id="step1",
        label="競合記事取得",
        description="SERP分析と競合コンテンツの収集",
        ai_model="gemini",
        model_name=os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash"),
        temperature=0.5,
        grounding=True,
        retry_limit=3,
        repair_enabled=True,
        is_configurable=True,
        recommended_model="gemini",
    ),
    StepDefaultConfig(
        step_id="step2",
        label="CSV検証",
        description="取得データの形式検証",
        ai_model="gemini",
        model_name=os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash"),
        temperature=0.3,
        grounding=False,
        retry_limit=3,
        repair_enabled=True,
        is_configurable=True,
        recommended_model="gemini",
    ),
    StepDefaultConfig(
        step_id="step3a",
        label="クエリ分析",
        description="検索クエリとペルソナの分析",
        ai_model="gemini",
        model_name=os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash"),
        temperature=0.7,
        grounding=True,
        retry_limit=3,
        repair_enabled=True,
        is_configurable=True,
        recommended_model="gemini",
    ),
    StepDefaultConfig(
        step_id="step3b",
        label="共起語抽出",
        description="関連キーワードと共起語の抽出",
        ai_model="gemini",
        model_name=os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash"),
        temperature=0.7,
        grounding=True,
        retry_limit=3,
        repair_enabled=True,
        is_configurable=True,
        recommended_model="gemini",
    ),
    StepDefaultConfig(
        step_id="step3c",
        label="競合分析",
        description="競合記事の差別化ポイント分析",
        ai_model="gemini",
        model_name=os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash"),
        temperature=0.7,
        grounding=False,
        retry_limit=3,
        repair_enabled=True,
        is_configurable=True,
        recommended_model="gemini",
    ),
    StepDefaultConfig(
        step_id="approval",
        label="承認待ち",
        description="人間による確認・承認ポイント",
        ai_model="gemini",
        model_name="",
        temperature=0,
        grounding=False,
        retry_limit=1,
        repair_enabled=False,
        is_configurable=False,
        recommended_model="gemini",
    ),
    StepDefaultConfig(
        step_id="step4",
        label="アウトライン",
        description="戦略的な記事構成の作成",
        ai_model="anthropic",
        model_name=os.getenv("ANTHROPIC_DEFAULT_MODEL", "claude-sonnet-4-20250514"),
        temperature=0.7,
        grounding=False,
        retry_limit=3,
        repair_enabled=True,
        is_configurable=True,
        recommended_model="anthropic",
    ),
    StepDefaultConfig(
        step_id="step5",
        label="一次情報収集",
        description="Web検索による一次情報の収集",
        ai_model="gemini",
        model_name=os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash"),
        temperature=0.5,
        grounding=True,
        retry_limit=3,
        repair_enabled=True,
        is_configurable=True,
        recommended_model="gemini",
    ),
    StepDefaultConfig(
        step_id="step6",
        label="アウトライン強化",
        description="一次情報を組み込んだ構成改善",
        ai_model="anthropic",
        model_name=os.getenv("ANTHROPIC_DEFAULT_MODEL", "claude-sonnet-4-20250514"),
        temperature=0.7,
        grounding=False,
        retry_limit=3,
        repair_enabled=True,
        is_configurable=True,
        recommended_model="anthropic",
    ),
    StepDefaultConfig(
        step_id="step6.5",
        label="統合パッケージ",
        description="全情報の統合とパッケージ化",
        ai_model="anthropic",
        model_name=os.getenv("ANTHROPIC_DEFAULT_MODEL", "claude-sonnet-4-20250514"),
        temperature=0.5,
        grounding=False,
        retry_limit=3,
        repair_enabled=True,
        is_configurable=True,
        recommended_model="anthropic",
    ),
    StepDefaultConfig(
        step_id="step7a",
        label="本文生成",
        description="初稿の本文生成",
        ai_model="anthropic",
        model_name=os.getenv("ANTHROPIC_DEFAULT_MODEL", "claude-sonnet-4-20250514"),
        temperature=0.8,
        grounding=False,
        retry_limit=3,
        repair_enabled=True,
        is_configurable=True,
        recommended_model="anthropic",
    ),
    StepDefaultConfig(
        step_id="step7b",
        label="ブラッシュアップ",
        description="文章の磨き上げと最適化",
        ai_model="gemini",
        model_name=os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash"),
        temperature=0.6,
        grounding=False,
        retry_limit=3,
        repair_enabled=True,
        is_configurable=True,
        recommended_model="gemini",
    ),
    StepDefaultConfig(
        step_id="step8",
        label="ファクトチェック",
        description="事実確認とFAQ生成",
        ai_model="gemini",
        model_name=os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash"),
        temperature=0.3,
        grounding=True,
        retry_limit=3,
        repair_enabled=True,
        is_configurable=True,
        recommended_model="gemini",
    ),
    StepDefaultConfig(
        step_id="step9",
        label="最終リライト",
        description="品質管理と最終調整",
        ai_model="anthropic",
        model_name=os.getenv("ANTHROPIC_DEFAULT_MODEL", "claude-sonnet-4-20250514"),
        temperature=0.5,
        grounding=False,
        retry_limit=3,
        repair_enabled=True,
        is_configurable=True,
        recommended_model="anthropic",
    ),
    StepDefaultConfig(
        step_id="step10",
        label="最終出力",
        description="HTML/Markdown形式での出力",
        ai_model="anthropic",
        model_name=os.getenv("ANTHROPIC_DEFAULT_MODEL", "claude-sonnet-4-20250514"),
        temperature=0.3,
        grounding=False,
        retry_limit=3,
        repair_enabled=True,
        is_configurable=True,
        recommended_model="anthropic",
    ),
]


@app.get("/api/config/models", response_model=ModelsConfigResponse)
async def get_models_config() -> ModelsConfigResponse:
    """Get available models and default workflow step configurations.

    This endpoint provides:
    - Available LLM providers with their default models
    - Default configuration for each workflow step

    The frontend should use this as the source of truth for model names
    and step configurations.
    """
    gemini_default = os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash")
    openai_default = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o")
    anthropic_default = os.getenv("ANTHROPIC_DEFAULT_MODEL", "claude-sonnet-4-20250514")

    providers = [
        ProviderConfig(
            provider="gemini",
            default_model=gemini_default,
            available_models=[
                gemini_default,
                "gemini-2.0-flash",
                "gemini-1.5-pro",
                "gemini-1.5-flash",
            ],
            supports_grounding=True,
        ),
        ProviderConfig(
            provider="openai",
            default_model=openai_default,
            available_models=[
                openai_default,
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-4-turbo",
            ],
            supports_grounding=False,
        ),
        ProviderConfig(
            provider="anthropic",
            default_model=anthropic_default,
            available_models=[
                anthropic_default,
                "claude-sonnet-4-20250514",
                "claude-3-5-sonnet-20241022",
                "claude-3-5-haiku-20241022",
            ],
            supports_grounding=False,
        ),
    ]

    return ModelsConfigResponse(
        providers=providers,
        step_defaults=WORKFLOW_STEP_DEFAULTS,
    )


# =============================================================================
# Cost Tracking Endpoint (GAP-021)
# =============================================================================


class CostBreakdown(BaseModel):
    """Cost breakdown by step."""

    step: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float


class CostResponse(BaseModel):
    """Cost response for a run."""

    run_id: str
    total_cost: float
    total_input_tokens: int
    total_output_tokens: int
    breakdown: list[CostBreakdown]
    currency: str = "USD"


# Default cost rates (per 1K tokens)
DEFAULT_COST_RATES: dict[str, dict[str, float]] = {
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.00375},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    "gemini-2.0-flash-exp": {"input": 0.0001, "output": 0.0004},
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    "claude-3-5-haiku-20241022": {"input": 0.0008, "output": 0.004},
}


@app.get("/api/runs/{run_id}/cost", response_model=CostResponse)
async def get_run_cost(
    run_id: str,
    user: AuthUser = Depends(get_current_user),
) -> CostResponse:
    """Get cost breakdown for a run.

    Calculates cost based on token usage stored in artifacts.
    """
    from sqlalchemy import select

    tenant_id = user.tenant_id
    logger.debug(
        "Getting run cost",
        extra={"run_id": run_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    db_manager = get_tenant_db_manager()
    store = get_artifact_store()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # Verify run belongs to tenant
            run_query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            run_result = await session.execute(run_query)
            run = run_result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # Get all artifacts for this run
            artifact_query = select(ArtifactModel).where(ArtifactModel.run_id == run_id)
            artifact_result = await session.execute(artifact_query)
            artifacts = artifact_result.scalars().all()

            # Calculate costs from artifact content
            breakdown: list[CostBreakdown] = []
            total_input_tokens = 0
            total_output_tokens = 0
            total_cost = 0.0

            for artifact in artifacts:
                content_type = artifact.content_type or artifact.artifact_type
                if content_type not in ["application/json", "json"]:
                    continue

                # Try to read artifact content for token usage
                try:
                    storage_ref = StorageArtifactRef(
                        path=artifact.ref_path,
                        digest=artifact.digest or "",
                        content_type=content_type,
                        size_bytes=artifact.size_bytes or 0,
                        created_at=artifact.created_at,
                    )
                    content_bytes = await store.get_with_tenant_check(
                        tenant_id=tenant_id,
                        ref=storage_ref,
                        verify=False,
                    )
                    content = json.loads(content_bytes.decode("utf-8"))

                    # Extract usage if present
                    usage = content.get("usage", {})
                    model = content.get("model", "unknown")

                    if usage:
                        input_tokens = usage.get("input_tokens", 0)
                        output_tokens = usage.get("output_tokens", 0)

                        # Calculate cost
                        rates = DEFAULT_COST_RATES.get(model, {"input": 0.001, "output": 0.002})
                        step_cost = (input_tokens / 1000) * rates["input"] + (output_tokens / 1000) * rates["output"]

                        # Get step name from step_id if available
                        step_name = artifact.artifact_type
                        if artifact.step_id:
                            step_query = select(Step).where(Step.id == artifact.step_id)
                            step_result = await session.execute(step_query)
                            step_record = step_result.scalar_one_or_none()
                            if step_record:
                                step_name = step_record.step_name

                        breakdown.append(
                            CostBreakdown(
                                step=step_name,
                                model=model,
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                cost=round(step_cost, 6),
                            )
                        )

                        total_input_tokens += input_tokens
                        total_output_tokens += output_tokens
                        total_cost += step_cost

                except Exception:
                    # Skip artifacts that can't be parsed
                    continue

            return CostResponse(
                run_id=run_id,
                total_cost=round(total_cost, 6),
                total_input_tokens=total_input_tokens,
                total_output_tokens=total_output_tokens,
                breakdown=breakdown,
            )

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to get run cost: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get run cost") from e


# =============================================================================
# Prompt Management Endpoints (JSON File Based)
# =============================================================================


class PromptJsonResponse(BaseModel):
    """Prompt response from JSON file."""

    step: str
    version: int
    content: str
    variables: dict[str, Any] | None = None


class PromptListJsonResponse(BaseModel):
    """List of prompts from JSON file."""

    pack_id: str
    prompts: list[PromptJsonResponse]
    total: int


class UpdatePromptJsonInput(BaseModel):
    """Request to update a prompt in JSON file."""

    content: str = Field(..., description="Updated prompt content")
    variables: dict[str, Any] | None = Field(None, description="Updated variable definitions")


@app.get("/api/prompts", response_model=PromptListJsonResponse)
async def list_prompts(
    pack_id: str = Query(default="default", description="Prompt pack ID"),
    step: str | None = Query(default=None, description="Filter by step name"),
) -> PromptListJsonResponse:
    """List all prompts from JSON file."""
    logger.debug("Listing prompts from JSON", extra={"pack_id": pack_id, "step": step})

    try:
        loader = PromptPackLoader()
        pack = loader.load(pack_id)

        prompts = []
        for step_id, template in pack.prompts.items():
            if step and step_id != step:
                continue
            prompts.append(
                PromptJsonResponse(
                    step=template.step,
                    version=template.version,
                    content=template.content,
                    variables=template.variables if template.variables else None,
                )
            )

        # Sort by step name
        prompts.sort(key=lambda p: p.step)

        return PromptListJsonResponse(
            pack_id=pack_id,
            prompts=prompts,
            total=len(prompts),
        )

    except PromptPackNotFoundError as e:
        logger.error(f"Prompt pack not found: {e}")
        raise HTTPException(status_code=404, detail=f"Prompt pack '{pack_id}' not found") from e
    except Exception as e:
        logger.error(f"Failed to list prompts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list prompts") from e


@app.get("/api/prompts/step/{step}", response_model=PromptJsonResponse)
async def get_prompt_by_step(
    step: str,
    pack_id: str = Query(default="default", description="Prompt pack ID"),
) -> PromptJsonResponse:
    """Get a specific prompt by step name from JSON file."""
    logger.debug("Getting prompt by step from JSON", extra={"pack_id": pack_id, "step": step})

    try:
        loader = PromptPackLoader()
        pack = loader.load(pack_id)
        template = pack.get_prompt(step)

        return PromptJsonResponse(
            step=template.step,
            version=template.version,
            content=template.content,
            variables=template.variables if template.variables else None,
        )

    except PromptPackNotFoundError as e:
        logger.error(f"Prompt pack not found: {e}")
        raise HTTPException(status_code=404, detail=f"Prompt pack '{pack_id}' not found") from e
    except Exception as e:
        logger.error(f"Failed to get prompt: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=f"Prompt not found for step: {step}") from e


@app.put("/api/prompts/step/{step}", response_model=PromptJsonResponse)
async def update_prompt_by_step(
    step: str,
    data: UpdatePromptJsonInput,
    pack_id: str = Query(default="default", description="Prompt pack ID"),
) -> PromptJsonResponse:
    """Update a prompt by step name in JSON file."""
    import json
    from pathlib import Path

    logger.info("Updating prompt in JSON file", extra={"pack_id": pack_id, "step": step})

    try:
        # Load current JSON file
        packs_dir = Path(__file__).parent / "prompts" / "packs"
        json_path = packs_dir / f"{pack_id}.json"

        if not json_path.exists():
            raise HTTPException(status_code=404, detail=f"Prompt pack '{pack_id}' not found")

        with open(json_path, encoding="utf-8") as f:
            pack_data = json.load(f)

        # Check if step exists
        if step not in pack_data.get("prompts", {}):
            raise HTTPException(status_code=404, detail=f"Prompt not found for step: {step}")

        # Update the prompt
        current_version = pack_data["prompts"][step].get("version", 1)
        pack_data["prompts"][step]["content"] = data.content
        pack_data["prompts"][step]["version"] = current_version + 1
        if data.variables is not None:
            pack_data["prompts"][step]["variables"] = data.variables

        # Write back to JSON file
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(pack_data, f, ensure_ascii=False, indent=2)

        # Clear loader cache
        loader = PromptPackLoader()
        loader.invalidate(pack_id)

        logger.info(
            "Prompt updated in JSON file",
            extra={"pack_id": pack_id, "step": step, "new_version": current_version + 1},
        )

        return PromptJsonResponse(
            step=step,
            version=current_version + 1,
            content=data.content,
            variables=data.variables,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update prompt: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update prompt") from e


# =============================================================================
# WebSocket Progress Streaming
# =============================================================================


class ConnectionManager:
    """WebSocket connection manager for real-time updates."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, run_id: str, websocket: WebSocket) -> None:
        """Track a WebSocket connection (acceptは呼び出し側で実施済み)."""
        if run_id not in self.active_connections:
            self.active_connections[run_id] = []
        self.active_connections[run_id].append(websocket)
        logger.info("WebSocket connected", extra={"run_id": run_id})

    def disconnect(self, run_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if run_id in self.active_connections:
            if websocket in self.active_connections[run_id]:
                self.active_connections[run_id].remove(websocket)
            if not self.active_connections[run_id]:
                del self.active_connections[run_id]
        logger.info("WebSocket disconnected", extra={"run_id": run_id})

    async def broadcast(self, run_id: str, message: dict[str, Any]) -> None:
        """Broadcast message to all connections for a run."""
        if run_id in self.active_connections:
            disconnected = []
            for websocket in self.active_connections[run_id]:
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.append(websocket)
            for ws in disconnected:
                self.disconnect(run_id, ws)

    async def broadcast_run_update(
        self,
        run_id: str,
        event_type: str,
        status: str,
        current_step: str | None = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        """Broadcast a run status update event.

        Args:
            run_id: The run ID to broadcast to
            event_type: Event type (e.g., 'run.status_changed', 'step.started')
            status: Current run status
            current_step: Current step name if applicable
            error: Error details if applicable
        """
        message: dict[str, Any] = {
            "type": event_type,
            "run_id": run_id,
            "status": status,
            "current_step": current_step,
            "timestamp": datetime.now().isoformat(),
        }
        if error:
            message["error"] = error
        await self.broadcast(run_id, message)

    async def broadcast_step_event(
        self,
        run_id: str,
        step: str,
        event_type: str,
        status: str,
        progress: int = 0,
        message: str = "",
        attempt: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Broadcast a step-level event.

        Args:
            run_id: The run ID to broadcast to
            step: Step name (e.g., 'step0', 'step3a')
            event_type: Event type (e.g., 'step_started', 'step_completed')
            status: Step status
            progress: Progress percentage (0-100)
            message: Human-readable status message
            attempt: Attempt number if applicable
            details: Additional details
        """
        # Match frontend ProgressEvent type
        event_message: dict[str, Any] = {
            "type": event_type,
            "run_id": run_id,
            "step": step,  # Frontend expects 'step', not 'step_id'
            "status": status,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        if attempt is not None:
            event_message["attempt"] = attempt
        if details:
            event_message["details"] = details
        await self.broadcast(run_id, event_message)


# Global connection manager
ws_manager = ConnectionManager()


@app.websocket("/ws/runs/{run_id}")
async def websocket_progress(websocket: WebSocket, run_id: str) -> None:
    """WebSocket endpoint for real-time progress updates.

    NOTE: 開発段階では認証を無効化
    """
    await websocket.accept()
    await ws_manager.connect(run_id, websocket)
    logger.info("WebSocket connected", extra={"run_id": run_id})

    try:
        while True:
            data = await websocket.receive_text()
            logger.debug("WebSocket received", extra={"run_id": run_id, "payload": data})

            if data == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        ws_manager.disconnect(run_id, websocket)


# =============================================================================
# Error Handlers (VULN-009: 内部情報を隠蔽)
# =============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler with request correlation."""
    import uuid

    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]

    logger.error(
        f"Unhandled exception [request_id={request_id}]: {exc}",
        exc_info=True,
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
        },
    )

    is_development = os.getenv("ENVIRONMENT", "development") == "development"

    if is_development:
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
                "request_id": request_id,
            },
        )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "request_id": request_id,
        },
    )


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "apps.api.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("ENVIRONMENT", "development") == "development",
    )
