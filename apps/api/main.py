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

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        environment=os.getenv("ENVIRONMENT", "development"),
    )


# =============================================================================
# Run Management Endpoints
# =============================================================================

class RunCreateRequest(BaseModel):
    """Request to create a new run."""
    tenant_id: str
    input_data: dict[str, object]
    config: dict[str, object] | None = None


class RunResponse(BaseModel):
    """Run response model."""
    id: str
    tenant_id: str
    status: str
    current_step: str | None
    config: dict[str, object]
    created_at: str


@app.post("/api/runs", response_model=RunResponse)
async def create_run(request: RunCreateRequest) -> RunResponse:
    """Create a new workflow run."""
    # TODO: Implement run creation with Temporal
    raise HTTPException(status_code=501, detail="Not implemented")


@app.get("/api/runs")
async def list_runs(
    tenant_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, object]:
    """List runs with optional filtering."""
    # TODO: Implement with database query
    return {"runs": [], "total": 0, "limit": limit, "offset": offset}


@app.get("/api/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: str) -> RunResponse:
    """Get run details."""
    # TODO: Implement with database query
    raise HTTPException(status_code=404, detail="Run not found")


@app.post("/api/runs/{run_id}/approve")
async def approve_run(run_id: str, comment: str | None = None) -> dict[str, object]:
    """Approve a run waiting for approval.

    Sends approval signal to Temporal workflow.
    """
    # TODO: Implement with Temporal signal
    raise HTTPException(status_code=501, detail="Not implemented")


@app.post("/api/runs/{run_id}/reject")
async def reject_run(run_id: str, reason: str) -> dict[str, object]:
    """Reject a run waiting for approval.

    Sends rejection signal to Temporal workflow.
    """
    # TODO: Implement with Temporal signal
    raise HTTPException(status_code=501, detail="Not implemented")


@app.post("/api/runs/{run_id}/retry/{step}")
async def retry_step(run_id: str, step: str) -> dict[str, object]:
    """Retry a failed step.

    Same conditions only - no fallback to different model/tool.
    """
    # TODO: Implement with Temporal signal
    raise HTTPException(status_code=501, detail="Not implemented")


@app.delete("/api/runs/{run_id}")
async def cancel_run(run_id: str) -> dict[str, object]:
    """Cancel a running workflow."""
    # TODO: Implement with Temporal cancellation
    raise HTTPException(status_code=501, detail="Not implemented")


# =============================================================================
# Artifact Endpoints
# =============================================================================

@app.get("/api/runs/{run_id}/files")
async def list_artifacts(run_id: str) -> dict[str, object]:
    """List all artifacts for a run."""
    # TODO: Implement with database/storage query
    return {"artifacts": []}


@app.get("/api/runs/{run_id}/files/{step}")
async def get_step_artifact(run_id: str, step: str) -> dict[str, object]:
    """Get artifact for a specific step."""
    # TODO: Implement with storage retrieval
    raise HTTPException(status_code=404, detail="Artifact not found")


# =============================================================================
# WebSocket Progress Streaming
# =============================================================================

@app.websocket("/ws/runs/{run_id}")
async def websocket_progress(websocket: WebSocket, run_id: str) -> None:
    """WebSocket endpoint for real-time progress updates."""
    await websocket.accept()

    try:
        # TODO: Implement progress streaming
        await websocket.send_json({
            "type": "connected",
            "run_id": run_id,
        })

        while True:
            # Wait for messages (keep connection alive)
            data = await websocket.receive_text()
            logger.debug(f"Received: {data}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for run {run_id}")


# =============================================================================
# Error Handlers
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
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
