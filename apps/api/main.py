"""FastAPI application entry point.

SEO Article Generator API server with endpoints for:
- Run management (create, list, get, approve, reject, retry, cancel)
- Artifact retrieval
- WebSocket progress streaming
- Authentication (JWT-based)
"""

import asyncio
import json
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import JWTError
from pydantic import BaseModel

from apps.api.auth.middleware import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_tenant,
)
from apps.api.auth.schemas import LoginRequest, RefreshRequest, TokenResponse

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
# Authentication Endpoints
# =============================================================================

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """Login endpoint for development/testing.

    In production, this should be replaced with proper authentication
    (OAuth, SAML, etc.) based on your identity provider.
    """
    # TODO: Replace with proper authentication in production
    # For development, accept any tenant/user with the dev secret
    dev_secret = os.getenv("DEV_AUTH_SECRET", "dev-secret")
    if request.secret != dev_secret:
        logger.warning(f"Login failed for tenant={request.tenant_id}, user={request.user_id}")
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    access_token = create_access_token(
        tenant_id=request.tenant_id,
        user_id=request.user_id,
    )
    refresh_token = create_refresh_token(
        tenant_id=request.tenant_id,
        user_id=request.user_id,
    )

    logger.info(f"Login successful for tenant={request.tenant_id}, user={request.user_id}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@app.post("/api/auth/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest) -> TokenResponse:
    """Refresh access token using refresh token."""
    try:
        payload = decode_token(request.refresh_token)

        # Verify this is a refresh token
        # Note: decode_token already validates expiration

        access_token = create_access_token(
            tenant_id=payload.tenant_id,
            user_id=payload.user_id,
        )
        new_refresh_token = create_refresh_token(
            tenant_id=payload.tenant_id,
            user_id=payload.user_id,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    except JWTError as e:
        logger.warning(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token",
        ) from e


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
    """WebSocket endpoint for real-time progress updates.

    Authentication flow:
    1. Client connects
    2. Server accepts connection
    3. Client sends auth message: {"type": "auth", "token": "..."}
    4. Server validates token and checks tenant access
    5. Server responds with auth_success or auth_error
    """
    await websocket.accept()

    try:
        # Wait for authentication message (10 second timeout)
        try:
            raw_data = await asyncio.wait_for(
                websocket.receive_text(),
                timeout=10.0
            )
            auth_msg = json.loads(raw_data)
        except asyncio.TimeoutError:
            await websocket.send_json({
                "type": "auth_error",
                "reason": "Authentication timeout",
            })
            await websocket.close(code=1008, reason="Auth timeout")
            return
        except json.JSONDecodeError:
            await websocket.send_json({
                "type": "auth_error",
                "reason": "Invalid message format",
            })
            await websocket.close(code=1008, reason="Invalid message")
            return

        # Validate auth message type
        if auth_msg.get("type") != "auth":
            await websocket.send_json({
                "type": "auth_error",
                "reason": "Authentication required",
            })
            await websocket.close(code=1008, reason="Auth required")
            return

        # Validate token
        token = auth_msg.get("token")
        if not token:
            await websocket.send_json({
                "type": "auth_error",
                "reason": "No token provided",
            })
            await websocket.close(code=1008, reason="No token")
            return

        try:
            payload = decode_token(token)
            tenant_id = payload.tenant_id
        except JWTError as e:
            logger.warning(f"WebSocket auth failed: {e}")
            await websocket.send_json({
                "type": "auth_error",
                "reason": "Invalid token",
            })
            await websocket.close(code=1008, reason="Invalid token")
            return

        # TODO: Check tenant access to run_id
        # In production, verify that the run belongs to this tenant
        # run = await get_run(run_id)
        # if run.tenant_id != tenant_id:
        #     await websocket.send_json({
        #         "type": "auth_error",
        #         "reason": "Access denied",
        #     })
        #     await websocket.close(code=1008, reason="Access denied")
        #     return

        # Authentication successful
        await websocket.send_json({
            "type": "auth_success",
            "run_id": run_id,
        })
        logger.info(f"WebSocket authenticated for run {run_id}, tenant {tenant_id}")

        # Handle messages
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received from tenant {tenant_id}: {data}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for run {run_id}")


# =============================================================================
# Error Handlers
# =============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler.

    Security: Never expose internal error details to clients.
    Internal details are logged server-side with an error_id for debugging.
    """
    import uuid

    # Generate unique error ID for tracking
    error_id = str(uuid.uuid4())[:8]

    # Log full details server-side (for debugging)
    logger.error(
        f"Unhandled exception [error_id={error_id}]: {exc}",
        exc_info=True,
        extra={
            "error_id": error_id,
            "path": request.url.path,
            "method": request.method,
        },
    )

    # Return sanitized error to client
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred. Please try again later.",
            "error_id": error_id,
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
