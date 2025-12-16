"""FastAPI application entry point.

SEO Article Generator API server with endpoints for:
- Run management (create, list, get, approve, reject, retry, cancel)
- Artifact retrieval
- WebSocket progress streaming
"""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

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

# CORS middleware
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
# Helper Functions
# =============================================================================


def get_tenant_id_from_request(request: Request) -> str:
    """Extract tenant_id from request (JWT auth in production).

    For now, returns a default tenant for development.
    TODO: Implement proper JWT authentication.
    """
    # In production, this would extract from JWT token
    # For development, use header or default
    tenant_id = request.headers.get("X-Tenant-ID", "default-tenant")
    return tenant_id


def datetime_to_iso(dt: datetime | None) -> str | None:
    """Convert datetime to ISO string."""
    if dt is None:
        return None
    return dt.isoformat()


# =============================================================================
# Run Management Endpoints
# =============================================================================


@app.post("/api/runs", response_model=RunResponse)
async def create_run(request: Request, data: CreateRunInput) -> RunResponse:
    """Create a new workflow run."""
    tenant_id = get_tenant_id_from_request(request)

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
    request: Request,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, Any]:
    """List runs with optional filtering."""
    tenant_id = get_tenant_id_from_request(request)
    offset = (page - 1) * limit

    # TODO: Implement with database query filtered by tenant_id
    logger.debug(f"Listing runs for tenant {tenant_id}, status={status}, page={page}")

    return {"runs": [], "total": 0, "limit": limit, "offset": offset}


@app.get("/api/runs/{run_id}", response_model=RunResponse)
async def get_run(request: Request, run_id: str) -> RunResponse:
    """Get run details."""
    tenant_id = get_tenant_id_from_request(request)

    # TODO: Implement with database query
    # Ensure tenant_id matches (prevent cross-tenant access)
    logger.debug(f"Getting run {run_id} for tenant {tenant_id}")

    raise HTTPException(status_code=404, detail="Run not found")


@app.post("/api/runs/{run_id}/approve")
async def approve_run(
    request: Request, run_id: str, comment: str | None = None
) -> dict[str, bool]:
    """Approve a run waiting for approval.

    Sends approval signal to Temporal workflow.
    """
    tenant_id = get_tenant_id_from_request(request)
    logger.info(f"Approving run {run_id} for tenant {tenant_id}, comment={comment}")

    # TODO: Implement with Temporal signal
    # 1. Verify run exists and belongs to tenant
    # 2. Verify run is in waiting_approval status
    # 3. Send signal to Temporal workflow
    # 4. Record in audit_logs

    raise HTTPException(status_code=501, detail="Not implemented")


@app.post("/api/runs/{run_id}/reject")
async def reject_run(
    request: Request, run_id: str, reason: str = ""
) -> dict[str, bool]:
    """Reject a run waiting for approval.

    Sends rejection signal to Temporal workflow.
    """
    tenant_id = get_tenant_id_from_request(request)
    logger.info(f"Rejecting run {run_id} for tenant {tenant_id}, reason={reason}")

    # TODO: Implement with Temporal signal

    raise HTTPException(status_code=501, detail="Not implemented")


@app.post("/api/runs/{run_id}/retry/{step}")
async def retry_step(
    request: Request, run_id: str, step: str
) -> dict[str, Any]:
    """Retry a failed step.

    Same conditions only - no fallback to different model/tool.
    """
    tenant_id = get_tenant_id_from_request(request)
    logger.info(f"Retrying step {step} of run {run_id} for tenant {tenant_id}")

    # TODO: Implement with Temporal signal
    # Return: { success: bool, new_attempt_id: str }

    raise HTTPException(status_code=501, detail="Not implemented")


@app.post("/api/runs/{run_id}/resume/{step}")
async def resume_from_step(
    request: Request, run_id: str, step: str
) -> dict[str, Any]:
    """Resume/restart workflow from a specific step.

    Creates a new run starting from the specified step.
    """
    tenant_id = get_tenant_id_from_request(request)
    logger.info(f"Resuming from step {step} of run {run_id} for tenant {tenant_id}")

    # TODO: Implement
    # 1. Verify original run exists and belongs to tenant
    # 2. Copy config and artifacts from completed steps
    # 3. Create new run starting from specified step
    # Return: { success: bool, new_run_id: str }

    raise HTTPException(status_code=501, detail="Not implemented")


@app.post("/api/runs/{run_id}/clone", response_model=RunResponse)
async def clone_run(
    request: Request, run_id: str, overrides: dict[str, Any] | None = None
) -> RunResponse:
    """Clone an existing run with optional config overrides."""
    tenant_id = get_tenant_id_from_request(request)
    logger.info(f"Cloning run {run_id} for tenant {tenant_id}")

    # TODO: Implement
    # 1. Verify original run exists and belongs to tenant
    # 2. Copy run config, optionally applying overrides
    # 3. Create new run with copied config

    raise HTTPException(status_code=501, detail="Not implemented")


@app.delete("/api/runs/{run_id}")
async def cancel_run(request: Request, run_id: str) -> dict[str, bool]:
    """Cancel a running workflow."""
    tenant_id = get_tenant_id_from_request(request)
    logger.info(f"Cancelling run {run_id} for tenant {tenant_id}")

    # TODO: Implement with Temporal cancellation
    # Return: { success: bool }

    raise HTTPException(status_code=501, detail="Not implemented")


# =============================================================================
# Artifact Endpoints
# =============================================================================


@app.get("/api/runs/{run_id}/files", response_model=list[ArtifactRef])
async def list_artifacts(request: Request, run_id: str) -> list[ArtifactRef]:
    """List all artifacts for a run."""
    tenant_id = get_tenant_id_from_request(request)
    logger.debug(f"Listing artifacts for run {run_id}, tenant {tenant_id}")

    # TODO: Implement with database/storage query
    return []


@app.get("/api/runs/{run_id}/files/{step}", response_model=list[ArtifactRef])
async def get_step_artifacts(
    request: Request, run_id: str, step: str
) -> list[ArtifactRef]:
    """Get artifacts for a specific step."""
    tenant_id = get_tenant_id_from_request(request)
    logger.debug(f"Getting artifacts for run {run_id}, step {step}, tenant {tenant_id}")

    # TODO: Implement with storage retrieval
    raise HTTPException(status_code=404, detail="Artifact not found")


@app.get("/api/runs/{run_id}/files/{artifact_id}/content", response_model=ArtifactContent)
async def get_artifact_content(
    request: Request, run_id: str, artifact_id: str
) -> ArtifactContent:
    """Get artifact content by ID."""
    tenant_id = get_tenant_id_from_request(request)
    logger.debug(
        f"Getting artifact content {artifact_id} for run {run_id}, tenant {tenant_id}"
    )

    # TODO: Implement with storage retrieval
    raise HTTPException(status_code=404, detail="Artifact not found")


@app.get("/api/runs/{run_id}/preview", response_class=HTMLResponse)
async def get_run_preview(request: Request, run_id: str) -> HTMLResponse:
    """Get HTML preview of generated article."""
    tenant_id = get_tenant_id_from_request(request)
    logger.debug(f"Getting preview for run {run_id}, tenant {tenant_id}")

    # TODO: Implement - return generated HTML from final step
    raise HTTPException(status_code=404, detail="Preview not available")


# =============================================================================
# Events Endpoint
# =============================================================================


@app.get("/api/runs/{run_id}/events", response_model=list[EventResponse])
async def list_events(
    request: Request,
    run_id: str,
    step: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[EventResponse]:
    """List events/audit logs for a run."""
    tenant_id = get_tenant_id_from_request(request)
    logger.debug(f"Listing events for run {run_id}, tenant {tenant_id}, step={step}")

    # TODO: Implement with audit_logs query
    return []


# =============================================================================
# WebSocket Progress Streaming
# =============================================================================


class ConnectionManager:
    """WebSocket connection manager for real-time updates."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, run_id: str, websocket: WebSocket) -> None:
        """Accept and track a WebSocket connection."""
        await websocket.accept()
        if run_id not in self.active_connections:
            self.active_connections[run_id] = []
        self.active_connections[run_id].append(websocket)
        logger.info(f"WebSocket connected for run {run_id}")

    def disconnect(self, run_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if run_id in self.active_connections:
            if websocket in self.active_connections[run_id]:
                self.active_connections[run_id].remove(websocket)
            if not self.active_connections[run_id]:
                del self.active_connections[run_id]
        logger.info(f"WebSocket disconnected for run {run_id}")

    async def broadcast(self, run_id: str, message: dict[str, Any]) -> None:
        """Broadcast message to all connections for a run."""
        if run_id in self.active_connections:
            disconnected = []
            for websocket in self.active_connections[run_id]:
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.append(websocket)
            # Clean up disconnected
            for ws in disconnected:
                self.disconnect(run_id, ws)


# Global connection manager
ws_manager = ConnectionManager()


def convert_event_type(be_type: str) -> str:
    """Convert BE event type to UI format.

    BE: step.started, step.succeeded, step.failed
    UI: step_started, step_completed, step_failed
    """
    # Replace dots with underscores
    ui_type = be_type.replace(".", "_")
    # Map succeeded to completed
    ui_type = ui_type.replace("_succeeded", "_completed")
    return ui_type


@app.websocket("/ws/runs/{run_id}")
async def websocket_progress(websocket: WebSocket, run_id: str) -> None:
    """WebSocket endpoint for real-time progress updates."""
    await ws_manager.connect(run_id, websocket)

    try:
        # Send connected confirmation
        await websocket.send_json({
            "type": "connected",
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
        })

        while True:
            # Wait for messages (keep connection alive)
            # Client can send ping messages
            data = await websocket.receive_text()
            logger.debug(f"WebSocket received from {run_id}: {data}")

            # Echo back pong for ping
            if data == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        ws_manager.disconnect(run_id, websocket)


# =============================================================================
# Error Handlers
# =============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Internal server error",
            }
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
