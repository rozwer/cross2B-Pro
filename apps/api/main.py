"""FastAPI application entry point.

SEO Article Generator API server.
All endpoints are organized into router modules under apps/api/routers/.
"""

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Temporal client for workflow management
from temporalio.client import Client as TemporalClient

from apps.api.db import TenantDBManager
from apps.api.routers import (
    articles,
    artifacts,
    auth,
    config,
    cost,
    diagnostics,
    events,
    github,
    health,
    hearing,
    help,
    internal,
    keywords,
    models,
    prompts,
    runs,
    settings,
    step11,
    step12,
    suggestions,
    websocket,
)
from apps.api.storage import ArtifactStore

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

# WebSocket manager (imported from websocket router)
ws_manager = websocket.ws_manager


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
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(runs.router)
app.include_router(artifacts.router)
app.include_router(events.router)
app.include_router(config.router)
app.include_router(cost.router)
app.include_router(prompts.router)
app.include_router(internal.router)
app.include_router(websocket.router)
app.include_router(diagnostics.router)
app.include_router(hearing.router)
app.include_router(keywords.router)
app.include_router(step11.router)
app.include_router(step12.router)
app.include_router(github.router)
app.include_router(settings.router)
app.include_router(models.router)
app.include_router(suggestions.router)
app.include_router(articles.router)
app.include_router(help.router)


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
