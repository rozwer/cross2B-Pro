"""FastAPI application entry point.

SEO Article Generator API server with endpoints for:
- Run management (create, list, get, approve, reject, retry, cancel)
- Artifact retrieval
- WebSocket progress streaming
"""

import asyncio
import json
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from apps.api.auth import get_current_tenant, get_current_user
from apps.api.auth.middleware import (
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
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


class RunInput(BaseModel):
    """Run input data."""

    keyword: str
    target_audience: str | None = None
    competitor_urls: list[str] | None = None
    additional_requirements: str | None = None


class RunOptions(BaseModel):
    """Run execution options."""

    retry_limit: int = 3
    repair_enabled: bool = True


class CreateRunInput(BaseModel):
    """Request to create a new run - matches UI CreateRunInput."""

    input: RunInput
    model_config_data: ModelConfig = Field(alias="model_config")
    tool_config: ToolConfig | None = None
    options: RunOptions | None = None

    class Config:
        populate_by_name = True


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


class StepAttempt(BaseModel):
    """Step attempt record."""

    id: str
    step_id: str
    attempt_num: int
    status: str  # running, succeeded, failed
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
        warnings.append(
            "No LLM API key set. Set at least one of: "
            f"{', '.join(llm_keys)} or set USE_MOCK_LLM=true"
        )

    return warnings


# =============================================================================
# Application Lifecycle
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
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

    yield

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
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    max_age=3600,
)


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
    """Detailed health check with service status."""
    # TODO: Implement actual service checks
    return DetailedHealthResponse(
        status="healthy",
        version="0.1.0",
        environment=os.getenv("ENVIRONMENT", "development"),
        services={
            "postgres": "unknown",
            "minio": "unknown",
            "temporal": "unknown",
        },
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


# =============================================================================
# Run Management Endpoints
# =============================================================================


@app.post("/api/runs", response_model=RunResponse)
async def create_run(data: CreateRunInput, user: AuthUser = Depends(get_current_user)) -> RunResponse:
    """Create a new workflow run (認証必須)."""
    tenant_id = user.tenant_id

    # TODO: Implement with Temporal workflow start
    # For now, return a mock response showing the correct structure
    import uuid

    run_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    return RunResponse(
        id=run_id,
        tenant_id=tenant_id,
        status=RunStatus.PENDING,
        current_step=None,
        input=data.input,
        model_config=data.model_config_data,
        tool_config=data.tool_config,
        options=data.options,
        steps=[],
        created_at=now,
        updated_at=now,
        started_at=None,
        completed_at=None,
        error=None,
    )


@app.get("/api/runs")
async def list_runs(
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """List runs with optional filtering."""
    tenant_id = user.tenant_id
    offset = (page - 1) * limit

    # TODO: Implement with database query filtered by tenant_id
    logger.debug(
        "Listing runs",
        extra={"tenant_id": tenant_id, "status": status, "page": page, "user_id": user.user_id},
    )

    return {"runs": [], "total": 0, "limit": limit, "offset": offset}


@app.get("/api/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, user: AuthUser = Depends(get_current_user)) -> RunResponse:
    """Get run details."""
    tenant_id = user.tenant_id

    # TODO: Implement with database query
    # Ensure tenant_id matches (prevent cross-tenant access)
    logger.debug(
        "Getting run",
        extra={"run_id": run_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    raise HTTPException(status_code=404, detail="Run not found")


@app.post("/api/runs/{run_id}/approve")
async def approve_run(
    run_id: str,
    comment: str | None = None,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, bool]:
    """Approve a run waiting for approval.

    Sends approval signal to Temporal workflow.
    """
    tenant_id = user.tenant_id
    logger.info(
        "Approving run",
        extra={"run_id": run_id, "tenant_id": tenant_id, "comment": comment, "user_id": user.user_id},
    )

    # TODO: Implement with Temporal signal
    # 1. Verify run exists and belongs to tenant
    # 2. Verify run is in waiting_approval status
    # 3. Send signal to Temporal workflow
    # 4. Record in audit_logs

    raise HTTPException(status_code=501, detail="Not implemented")


@app.post("/api/runs/{run_id}/reject")
async def reject_run(
    run_id: str,
    reason: str = "",
    user: AuthUser = Depends(get_current_user),
) -> dict[str, bool]:
    """Reject a run waiting for approval.

    Sends rejection signal to Temporal workflow.
    """
    tenant_id = user.tenant_id
    logger.info(
        "Rejecting run",
        extra={"run_id": run_id, "tenant_id": tenant_id, "reason": reason, "user_id": user.user_id},
    )

    # TODO: Implement with Temporal signal

    raise HTTPException(status_code=501, detail="Not implemented")


@app.post("/api/runs/{run_id}/retry/{step}")
async def retry_step(
    run_id: str,
    step: str,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Retry a failed step.

    Same conditions only - no fallback to different model/tool.
    """
    tenant_id = user.tenant_id
    logger.info(
        "Retrying step",
        extra={"run_id": run_id, "step": step, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    # TODO: Implement with Temporal signal
    # Return: { success: bool, new_attempt_id: str }

    raise HTTPException(status_code=501, detail="Not implemented")


@app.post("/api/runs/{run_id}/resume/{step}")
async def resume_from_step(
    run_id: str,
    step: str,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Resume/restart workflow from a specific step.

    Creates a new run starting from the specified step.
    """
    tenant_id = user.tenant_id
    logger.info(
        "Resuming run",
        extra={"run_id": run_id, "step": step, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    # TODO: Implement
    # 1. Verify original run exists and belongs to tenant
    # 2. Copy config and artifacts from completed steps
    # 3. Create new run starting from specified step
    # Return: { success: bool, new_run_id: str }

    raise HTTPException(status_code=501, detail="Not implemented")


@app.post("/api/runs/{run_id}/clone", response_model=RunResponse)
async def clone_run(
    run_id: str,
    overrides: dict[str, Any] | None = None,
    user: AuthUser = Depends(get_current_user),
) -> RunResponse:
    """Clone an existing run with optional config overrides."""
    tenant_id = user.tenant_id
    logger.info(
        "Cloning run",
        extra={"run_id": run_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    # TODO: Implement
    # 1. Verify original run exists and belongs to tenant
    # 2. Copy run config, optionally applying overrides
    # 3. Create new run with copied config

    raise HTTPException(status_code=501, detail="Not implemented")


@app.delete("/api/runs/{run_id}")
async def cancel_run(run_id: str, user: AuthUser = Depends(get_current_user)) -> dict[str, bool]:
    """Cancel a running workflow."""
    tenant_id = user.tenant_id
    logger.info(
        "Cancelling run",
        extra={"run_id": run_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    # TODO: Implement with Temporal cancellation
    # Return: { success: bool }

    raise HTTPException(status_code=501, detail="Not implemented")


# =============================================================================
# Artifact Endpoints
# =============================================================================


@app.get("/api/runs/{run_id}/files", response_model=list[ArtifactRef])
async def list_artifacts(run_id: str, user: AuthUser = Depends(get_current_user)) -> list[ArtifactRef]:
    """List all artifacts for a run."""
    tenant_id = user.tenant_id
    logger.debug(
        "Listing artifacts",
        extra={"run_id": run_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    # TODO: Implement with database/storage query
    return []


@app.get("/api/runs/{run_id}/files/{step}", response_model=list[ArtifactRef])
async def get_step_artifacts(
    run_id: str,
    step: str,
    user: AuthUser = Depends(get_current_user),
) -> list[ArtifactRef]:
    """Get artifacts for a specific step."""
    tenant_id = user.tenant_id
    logger.debug(
        "Getting step artifacts",
        extra={"run_id": run_id, "step": step, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    # TODO: Implement with storage retrieval
    raise HTTPException(status_code=404, detail="Artifact not found")


@app.get("/api/runs/{run_id}/files/{artifact_id}/content", response_model=ArtifactContent)
async def get_artifact_content(
    run_id: str,
    artifact_id: str,
    user: AuthUser = Depends(get_current_user),
) -> ArtifactContent:
    """Get artifact content by ID."""
    tenant_id = user.tenant_id
    logger.debug(
        "Getting artifact content",
        extra={"run_id": run_id, "artifact_id": artifact_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    # TODO: Implement with storage retrieval
    raise HTTPException(status_code=404, detail="Artifact not found")


@app.get("/api/runs/{run_id}/preview", response_class=HTMLResponse)
async def get_run_preview(run_id: str, user: AuthUser = Depends(get_current_user)) -> HTMLResponse:
    """Get HTML preview of generated article."""
    tenant_id = user.tenant_id
    logger.debug(
        "Getting preview",
        extra={"run_id": run_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    # TODO: Implement - return generated HTML from final step
    raise HTTPException(status_code=404, detail="Preview not available")


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
    tenant_id = user.tenant_id
    logger.debug(
        "Listing events",
        extra={"run_id": run_id, "tenant_id": tenant_id, "step": step, "user_id": user.user_id},
    )

    # TODO: Implement with audit_logs query
    return []


# =============================================================================
# Diagnostics Endpoints
# =============================================================================


class ErrorLogResponse(BaseModel):
    """Error log entry response."""

    id: int
    step_id: str | None
    error_category: str
    error_type: str
    error_message: str
    context: dict[str, Any] | None = None
    attempt: int
    created_at: str


class DiagnosticReportResponse(BaseModel):
    """Diagnostic report response."""

    id: int
    run_id: str
    root_cause_analysis: str
    recommended_actions: list[dict[str, Any]]
    resume_step: str | None = None
    confidence_score: float | None = None
    llm_provider: str
    llm_model: str
    created_at: str


class DiagnosticsRequest(BaseModel):
    """Request to generate diagnostics."""

    llm_provider: str | None = None  # anthropic, openai, gemini


@app.get("/api/runs/{run_id}/errors", response_model=list[ErrorLogResponse])
async def list_error_logs(
    run_id: str,
    step: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    user: AuthUser = Depends(get_current_user),
) -> list[ErrorLogResponse]:
    """List error logs for a run."""
    from apps.api.db.tenant import get_tenant_manager
    from apps.api.observability.error_collector import ErrorCollector

    tenant_id = user.tenant_id
    logger.debug(
        "Listing error logs",
        extra={"run_id": run_id, "tenant_id": tenant_id, "step": step, "user_id": user.user_id},
    )

    try:
        manager = get_tenant_manager()
        async with manager.get_session(tenant_id) as session:
            collector = ErrorCollector(session)
            errors = await collector.get_errors_for_run(run_id, step_id=step, limit=limit)

            return [
                ErrorLogResponse(
                    id=e.id,
                    step_id=e.step_id,
                    error_category=e.error_category,
                    error_type=e.error_type,
                    error_message=e.error_message,
                    context=e.context,
                    attempt=e.attempt,
                    created_at=e.created_at.isoformat(),
                )
                for e in errors
            ]
    except Exception as e:
        logger.error(f"Failed to list error logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve error logs")


@app.get("/api/runs/{run_id}/errors/summary")
async def get_error_summary(
    run_id: str,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get error summary for a run."""
    from apps.api.db.tenant import get_tenant_manager
    from apps.api.observability.error_collector import ErrorCollector

    tenant_id = user.tenant_id
    logger.debug(
        "Getting error summary",
        extra={"run_id": run_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    try:
        manager = get_tenant_manager()
        async with manager.get_session(tenant_id) as session:
            collector = ErrorCollector(session)
            return await collector.get_error_summary(run_id)
    except Exception as e:
        logger.error(f"Failed to get error summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve error summary")


@app.post("/api/runs/{run_id}/diagnose", response_model=DiagnosticReportResponse)
async def diagnose_run(
    run_id: str,
    request: DiagnosticsRequest | None = None,
    user: AuthUser = Depends(get_current_user),
) -> DiagnosticReportResponse:
    """Generate LLM-based diagnostic analysis for a failed run.

    Analyzes collected error logs and provides:
    - Root cause analysis
    - Recommended recovery actions
    - Suggested step to resume from
    """
    from apps.api.db.tenant import get_tenant_manager
    from apps.api.observability.diagnostics import DiagnosticsService

    tenant_id = user.tenant_id
    llm_provider = request.llm_provider if request else None

    logger.info(
        "Generating diagnostics",
        extra={
            "run_id": run_id,
            "tenant_id": tenant_id,
            "llm_provider": llm_provider,
            "user_id": user.user_id,
        },
    )

    try:
        manager = get_tenant_manager()
        async with manager.get_session(tenant_id) as session:
            diagnostics = DiagnosticsService(session, llm_provider=llm_provider)
            report = await diagnostics.analyze_failure(run_id, tenant_id)

            return DiagnosticReportResponse(
                id=report.id,
                run_id=run_id,
                root_cause_analysis=report.root_cause_analysis,
                recommended_actions=report.recommended_actions,
                resume_step=report.resume_step,
                confidence_score=float(report.confidence_score) if report.confidence_score else None,
                llm_provider=report.llm_provider,
                llm_model=report.llm_model,
                created_at=report.created_at.isoformat(),
            )
    except Exception as e:
        logger.error(f"Failed to generate diagnostics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate diagnostics: {str(e)}")


@app.get("/api/runs/{run_id}/diagnostics", response_model=list[DiagnosticReportResponse])
async def list_diagnostics(
    run_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    user: AuthUser = Depends(get_current_user),
) -> list[DiagnosticReportResponse]:
    """List all diagnostic reports for a run."""
    from sqlalchemy import select

    from apps.api.db.models import DiagnosticReport
    from apps.api.db.tenant import get_tenant_manager

    tenant_id = user.tenant_id
    logger.debug(
        "Listing diagnostics",
        extra={"run_id": run_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    try:
        manager = get_tenant_manager()
        async with manager.get_session(tenant_id) as session:
            stmt = (
                select(DiagnosticReport)
                .where(DiagnosticReport.run_id == run_id)
                .order_by(DiagnosticReport.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            reports = result.scalars().all()

            return [
                DiagnosticReportResponse(
                    id=r.id,
                    run_id=run_id,
                    root_cause_analysis=r.root_cause_analysis,
                    recommended_actions=r.recommended_actions,
                    resume_step=r.resume_step,
                    confidence_score=float(r.confidence_score) if r.confidence_score else None,
                    llm_provider=r.llm_provider,
                    llm_model=r.llm_model,
                    created_at=r.created_at.isoformat(),
                )
                for r in reports
            ]
    except Exception as e:
        logger.error(f"Failed to list diagnostics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve diagnostics")


# =============================================================================
# WebSocket Progress Streaming (VULN-006: 認証対応)
# =============================================================================

# 認証タイムアウト（秒）
WS_AUTH_TIMEOUT = 10.0


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


# Global connection manager
ws_manager = ConnectionManager()


@app.websocket("/ws/runs/{run_id}")
async def websocket_progress(websocket: WebSocket, run_id: str) -> None:
    """WebSocket endpoint for real-time progress updates with JWT auth."""
    await websocket.accept()

    try:
        # 認証メッセージを待機（タイムアウト付き）
        try:
            data = await asyncio.wait_for(
                websocket.receive_text(),
                timeout=WS_AUTH_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.warning("WebSocket auth timeout", extra={"run_id": run_id})
            await websocket.close(code=1008, reason="Auth timeout")
            return

        try:
            auth_msg = json.loads(data)
        except json.JSONDecodeError:
            await websocket.send_json({"type": "auth_error", "reason": "Invalid message format"})
            await websocket.close(code=1008, reason="Invalid auth message")
            return

        if auth_msg.get("type") != "auth":
            await websocket.send_json({"type": "auth_error", "reason": "Authentication required"})
            await websocket.close(code=1008, reason="Auth required")
            return

        token = auth_msg.get("token")
        if not token:
            await websocket.send_json({"type": "auth_error", "reason": "Missing token"})
            await websocket.close(code=1008, reason="Missing token")
            return

        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            tenant_id = payload.get("tenant_id")
            user_id = payload.get("sub")

            if not tenant_id:
                await websocket.send_json({"type": "auth_error", "reason": "Invalid token"})
                await websocket.close(code=1008, reason="Invalid token")
                return

        except JWTError as e:
            logger.warning("WebSocket JWT error", extra={"run_id": run_id, "error": str(e)})
            await websocket.send_json({"type": "auth_error", "reason": "Invalid token"})
            await websocket.close(code=1008, reason="Invalid token")
            return

        # TODO: データベースから run の tenant_id を取得して比較（テナント越境防止）

        await websocket.send_json({"type": "auth_success"})
        await ws_manager.connect(run_id, websocket)
        logger.info(
            "WebSocket authenticated",
            extra={"run_id": run_id, "user_id": user_id, "tenant_id": tenant_id},
        )

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
