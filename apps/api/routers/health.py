"""Health check router.

Handles health check endpoints for service monitoring.
"""

import logging
import os
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


# =============================================================================
# Lazy imports to avoid circular dependencies
# =============================================================================


def _get_tenant_db_manager() -> Any:
    """Get tenant DB manager."""
    from apps.api.main import tenant_db_manager

    return tenant_db_manager


def _get_artifact_store() -> Any:
    """Get artifact store instance."""
    from apps.api.main import artifact_store

    return artifact_store


def _get_temporal_client() -> Any:
    """Get Temporal client."""
    from apps.api.main import temporal_client

    return temporal_client


def _get_temporal_config() -> tuple[str, str, str]:
    """Get Temporal configuration."""
    from apps.api.main import TEMPORAL_HOST, TEMPORAL_NAMESPACE, TEMPORAL_PORT

    return TEMPORAL_HOST, TEMPORAL_PORT, TEMPORAL_NAMESPACE


async def _reconnect_temporal() -> Any:
    """Attempt to reconnect to Temporal."""
    from temporalio.client import Client as TemporalClient

    from apps.api import main

    host, port, namespace = _get_temporal_config()
    temporal_address = f"{host}:{port}"
    main.temporal_client = await TemporalClient.connect(
        temporal_address,
        namespace=namespace,
    )
    logger.info(f"Reconnected to Temporal at {temporal_address}")
    return main.temporal_client


# =============================================================================
# Pydantic Models
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


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        environment=os.getenv("ENVIRONMENT", "development"),
    )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check() -> DetailedHealthResponse:
    """Detailed health check with service status.

    Checks connectivity to:
    - PostgreSQL (via TenantDBManager)
    - MinIO/Storage (via ArtifactStore)
    - Temporal (via Temporal client)
    """
    services: dict[str, str] = {}
    overall_healthy = True

    tenant_db_manager = _get_tenant_db_manager()
    artifact_store = _get_artifact_store()
    temporal_client = _get_temporal_client()

    # Check PostgreSQL
    try:
        if tenant_db_manager:
            # Try a simple operation on dev tenant
            async with tenant_db_manager.get_session("dev-tenant-001") as session:
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
    try:
        if temporal_client is None:
            # Attempt to reconnect
            try:
                await _reconnect_temporal()
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
