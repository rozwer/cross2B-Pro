"""Settings router for API key and model configuration.

Handles CRUD operations for external service settings.
All API keys are encrypted at rest and masked in responses.

SECURITY:
- API keys are encrypted with AES-256-GCM
- Keys are masked in all responses (show only last 4 chars, or first 4 for GitHub)
- GitHub tokens get extra warnings about exposure risks
- All changes are logged to audit_logs
"""

import logging
import os
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from apps.api.db.audit import AuditLogger
from apps.api.db.models import ApiSetting
from apps.api.db.tenant import TenantDBManager, get_tenant_manager
from apps.api.services.connection_test import ConnectionTestResult, ConnectionTestService
from apps.api.services.encryption import EncryptionError, decrypt, encrypt, mask_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


# =============================================================================
# Pydantic Models
# =============================================================================


class ServiceConfig(BaseModel):
    """Service-specific configuration."""

    grounding: bool | None = None  # For Gemini
    temperature: float | None = None
    # GitHub-specific options
    default_repo_url: str | None = None  # Default repository URL
    default_dir_path: str | None = None  # Default directory path in repo
    repository_urls: list[str] | None = None  # Saved repository URLs for dropdown


class SettingResponse(BaseModel):
    """Response model for a single service setting."""

    service: str
    api_key_masked: str | None = None
    default_model: str | None = None
    config: ServiceConfig | None = None
    is_active: bool = True
    verified_at: str | None = None
    env_fallback: bool = False  # True if using environment variable


class SettingsListResponse(BaseModel):
    """Response model for settings list."""

    settings: list[SettingResponse]


class SettingUpdateRequest(BaseModel):
    """Request model for updating a service setting."""

    api_key: str | None = Field(None, description="API key (optional, keep existing if not provided)")
    default_model: str | None = Field(None, description="Default model for LLM providers")
    config: ServiceConfig | None = Field(None, description="Service-specific configuration")
    is_active: bool = Field(True, description="Whether the service is active")


class ConnectionTestResponse(BaseModel):
    """Response model for connection test."""

    success: bool
    service: str
    latency_ms: int | None = None
    error_message: str | None = None
    details: dict[str, Any] | None = None
    # GitHub specific: scope validation
    scopes: list[str] | None = None
    missing_scopes: list[str] | None = None
    scope_warning: str | None = None


# =============================================================================
# Service definitions
# =============================================================================

# LLM services with model support
LLM_SERVICES = {"gemini", "openai", "anthropic"}

# External services without model support
EXTERNAL_SERVICES = {"serp", "google_ads", "github"}

# All supported services
ALL_SERVICES = LLM_SERVICES | EXTERNAL_SERVICES

# Environment variable mapping
ENV_VAR_MAP = {
    "gemini": "GEMINI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "serp": "SERP_API_KEY",
    "google_ads": "GOOGLE_ADS_API_KEY",
    "github": "GITHUB_TOKEN",
}

# Default model environment variables
DEFAULT_MODEL_ENV_MAP = {
    "gemini": "GEMINI_DEFAULT_MODEL",
    "openai": "OPENAI_DEFAULT_MODEL",
    "anthropic": "ANTHROPIC_DEFAULT_MODEL",
}


# =============================================================================
# Dependencies
# =============================================================================


def get_current_tenant_id() -> str:
    """Get current tenant ID from authentication.

    TODO: Implement proper auth - currently returns default tenant.
    """
    return os.getenv("DEV_TENANT_ID", os.getenv("DEFAULT_TENANT_ID", "default"))


# =============================================================================
# Helper Functions
# =============================================================================


def _get_env_fallback(service: str) -> tuple[str | None, str | None]:
    """Get API key and default model from environment variables.

    Returns:
        Tuple of (api_key, default_model)
    """
    env_var = ENV_VAR_MAP.get(service)
    api_key = os.getenv(env_var) if env_var else None

    model_env = DEFAULT_MODEL_ENV_MAP.get(service)
    default_model = os.getenv(model_env) if model_env else None

    return api_key, default_model


async def _get_setting(
    tenant_manager: TenantDBManager,
    tenant_id: str,
    service: str,
) -> ApiSetting | None:
    """Get setting from database."""
    async with tenant_manager.get_session(tenant_id) as session:
        result = await session.execute(
            select(ApiSetting).where(
                ApiSetting.tenant_id == tenant_id,
                ApiSetting.service == service,
            )
        )
        return result.scalar_one_or_none()


def _setting_to_response(
    setting: ApiSetting | None,
    service: str,
) -> SettingResponse:
    """Convert DB setting to response model."""
    if setting and setting.api_key_encrypted:
        # Use DB setting
        try:
            decrypted_key = decrypt(setting.api_key_encrypted)
            masked_key = mask_api_key(decrypted_key, service)
            return SettingResponse(
                service=service,
                api_key_masked=masked_key,
                default_model=setting.default_model,
                config=ServiceConfig(**(setting.config or {})) if setting.config else None,
                is_active=setting.is_active,
                verified_at=setting.verified_at.isoformat() if setting.verified_at else None,
                env_fallback=False,
            )
        except EncryptionError:
            # Decryption failed - fall through to env fallback
            logger.warning(f"Failed to decrypt API key for {service}, falling back to env")

    # Fall back to environment variable (no DB setting, inactive, or decryption failed)
    env_key, default_model = _get_env_fallback(service)
    if env_key:
        masked_key = mask_api_key(env_key, service)
        return SettingResponse(
            service=service,
            api_key_masked=masked_key,
            default_model=default_model,
            config=None,
            is_active=True,
            verified_at=None,
            env_fallback=True,
        )
    else:
        return SettingResponse(
            service=service,
            api_key_masked=None,
            default_model=default_model,
            config=None,
            is_active=False,
            verified_at=None,
            env_fallback=True,
        )


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=SettingsListResponse)
async def get_all_settings(
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_manager: TenantDBManager = Depends(get_tenant_manager),
) -> SettingsListResponse:
    """Get all service settings.

    Returns settings for all supported services.
    API keys are masked in responses.
    Falls back to environment variables if no DB setting exists.
    """
    settings_list = []

    async with tenant_manager.get_session(tenant_id) as session:
        result = await session.execute(select(ApiSetting).where(ApiSetting.tenant_id == tenant_id))
        db_settings = {s.service: s for s in result.scalars().all()}

    for service in sorted(ALL_SERVICES):
        setting = db_settings.get(service)
        settings_list.append(_setting_to_response(setting, service))

    return SettingsListResponse(settings=settings_list)


@router.get("/{service}", response_model=SettingResponse)
async def get_setting(
    service: str,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_manager: TenantDBManager = Depends(get_tenant_manager),
) -> SettingResponse:
    """Get setting for a specific service.

    API key is masked in response.
    """
    service = service.lower()
    if service not in ALL_SERVICES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown service: {service}. Supported: {', '.join(sorted(ALL_SERVICES))}",
        )

    setting = await _get_setting(tenant_manager, tenant_id, service)
    return _setting_to_response(setting, service)


@router.put("/{service}", response_model=SettingResponse)
async def update_setting(
    service: str,
    request: SettingUpdateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_manager: TenantDBManager = Depends(get_tenant_manager),
) -> SettingResponse:
    """Update setting for a service.

    If api_key is provided, it will be encrypted and stored.
    If api_key is None, the existing key is preserved.
    """
    service = service.lower()
    if service not in ALL_SERVICES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown service: {service}. Supported: {', '.join(sorted(ALL_SERVICES))}",
        )

    async with tenant_manager.get_session(tenant_id) as session:
        # Get existing setting
        result = await session.execute(
            select(ApiSetting).where(
                ApiSetting.tenant_id == tenant_id,
                ApiSetting.service == service,
            )
        )
        setting = result.scalar_one_or_none()

        if setting is None:
            # Create new setting
            setting = ApiSetting(
                tenant_id=tenant_id,
                service=service,
            )
            session.add(setting)

        # Update fields
        if request.api_key is not None:
            setting.api_key_encrypted = encrypt(request.api_key)
            setting.verified_at = None  # Reset verification when key changes

        if request.default_model is not None:
            setting.default_model = request.default_model

        if request.config is not None:
            setting.config = request.config.model_dump(exclude_none=True)

        setting.is_active = request.is_active
        setting.updated_at = datetime.now(UTC)

        await session.flush()

        # Log audit
        audit_logger = AuditLogger(session)
        await audit_logger.log(
            user_id=tenant_id,  # TODO: Use actual user ID
            action="update_setting",
            resource_type="api_setting",
            resource_id=service,
            details={
                "service": service,
                "has_api_key": request.api_key is not None,
                "default_model": request.default_model,
                "is_active": request.is_active,
            },
        )

    # Get updated setting
    updated_setting = await _get_setting(tenant_manager, tenant_id, service)
    return _setting_to_response(updated_setting, service)


@router.delete("/{service}")
async def delete_setting(
    service: str,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_manager: TenantDBManager = Depends(get_tenant_manager),
) -> dict[str, str]:
    """Delete setting for a service.

    This removes the DB setting and falls back to environment variables.
    """
    service = service.lower()
    if service not in ALL_SERVICES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown service: {service}. Supported: {', '.join(sorted(ALL_SERVICES))}",
        )

    async with tenant_manager.get_session(tenant_id) as session:
        result = await session.execute(
            select(ApiSetting).where(
                ApiSetting.tenant_id == tenant_id,
                ApiSetting.service == service,
            )
        )
        setting = result.scalar_one_or_none()

        if setting:
            await session.delete(setting)
            await session.flush()  # Ensure deletion is persisted before audit log

            # Log audit
            audit_logger = AuditLogger(session)
            await audit_logger.log(
                user_id=tenant_id,
                action="delete_setting",
                resource_type="api_setting",
                resource_id=service,
                details={"service": service},
            )

    return {"message": f"Setting for {service} deleted. Will fall back to environment variable."}


@router.post("/{service}/test", response_model=ConnectionTestResponse)
async def test_connection(
    service: str,
    api_key: str | None = None,
    model: str | None = None,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_manager: TenantDBManager = Depends(get_tenant_manager),
) -> ConnectionTestResponse:
    """Test connection to a service.

    If api_key is provided, tests with that key.
    Otherwise uses the stored setting or environment variable.

    For LLM services, optionally specify a model to test.
    """
    service = service.lower()
    if service not in ALL_SERVICES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown service: {service}. Supported: {', '.join(sorted(ALL_SERVICES))}",
        )

    # Determine which API key to use
    test_key = api_key
    test_model = model

    if not test_key:
        # Try DB setting first
        setting = await _get_setting(tenant_manager, tenant_id, service)
        if setting and setting.api_key_encrypted:
            try:
                test_key = decrypt(setting.api_key_encrypted)
                if not test_model and setting.default_model:
                    test_model = setting.default_model
            except Exception:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to decrypt stored API key",
                )
        else:
            # Fall back to environment
            test_key, env_model = _get_env_fallback(service)
            if not test_model:
                test_model = env_model

    if not test_key:
        return ConnectionTestResponse(
            success=False,
            service=service,
            error_message="No API key available. Provide one or configure in settings.",
        )

    # Run connection test
    test_service = ConnectionTestService()
    result: ConnectionTestResult = await test_service.test_connection(
        service=service,
        api_key=test_key,
        model=test_model,
    )

    # Update verified_at if test succeeded and using stored key
    if result.success and not api_key:
        async with tenant_manager.get_session(tenant_id) as session:
            db_result = await session.execute(
                select(ApiSetting).where(
                    ApiSetting.tenant_id == tenant_id,
                    ApiSetting.service == service,
                )
            )
            setting = db_result.scalar_one_or_none()
            if setting:
                setting.verified_at = datetime.now(UTC)
                await session.flush()  # Ensure verified_at is persisted

    return ConnectionTestResponse(
        success=result.success,
        service=result.service,
        latency_ms=result.latency_ms,
        error_message=result.error_message,
        details=result.details,
        scopes=result.scopes,
        missing_scopes=result.missing_scopes,
        scope_warning=result.scope_warning,
    )


# =============================================================================
# GitHub Repository URL Management
# =============================================================================


class AddRepoRequest(BaseModel):
    """Request model for adding a repository URL."""

    repo_url: str = Field(..., description="GitHub repository URL to add")


class RepoListResponse(BaseModel):
    """Response model for repository URL list."""

    repository_urls: list[str]
    default_repo_url: str | None = None


@router.post("/github/repositories", response_model=RepoListResponse)
async def add_repository_url(
    request: AddRepoRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_manager: TenantDBManager = Depends(get_tenant_manager),
) -> RepoListResponse:
    """Add a repository URL to the saved list.

    Used when creating a run with a new repository.
    Automatically deduplicates and maintains a list of used repositories.
    """
    import re

    # Validate URL format
    repo_url = request.repo_url.strip()
    if not re.match(r"^https://github\.com/[\w\-]+/[\w\-\.]+/?$", repo_url):
        raise HTTPException(
            status_code=422,
            detail="Invalid GitHub repository URL format",
        )

    # Remove trailing slash for consistency
    repo_url = repo_url.rstrip("/")

    async with tenant_manager.get_session(tenant_id) as session:
        result = await session.execute(
            select(ApiSetting).where(
                ApiSetting.tenant_id == tenant_id,
                ApiSetting.service == "github",
            )
        )
        setting = result.scalar_one_or_none()

        if setting:
            # Update existing setting
            config = setting.config or {}
            repo_urls = config.get("repository_urls", [])
            if repo_url not in repo_urls:
                repo_urls.insert(0, repo_url)  # Add to front (most recent first)
                # Keep max 20 URLs
                repo_urls = repo_urls[:20]
                config["repository_urls"] = repo_urls
                setting.config = config
        else:
            # Create new setting
            setting = ApiSetting(
                tenant_id=tenant_id,
                service="github",
                config={"repository_urls": [repo_url]},
                is_active=True,
            )
            session.add(setting)

        await session.flush()
        config = setting.config or {}

    return RepoListResponse(
        repository_urls=config.get("repository_urls", []),
        default_repo_url=config.get("default_repo_url"),
    )


@router.get("/github/repositories", response_model=RepoListResponse)
async def get_repository_urls(
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_manager: TenantDBManager = Depends(get_tenant_manager),
) -> RepoListResponse:
    """Get list of saved repository URLs.

    Returns all repository URLs saved for this tenant.
    """
    async with tenant_manager.get_session(tenant_id) as session:
        result = await session.execute(
            select(ApiSetting).where(
                ApiSetting.tenant_id == tenant_id,
                ApiSetting.service == "github",
            )
        )
        setting = result.scalar_one_or_none()

    if setting and setting.config:
        return RepoListResponse(
            repository_urls=setting.config.get("repository_urls", []),
            default_repo_url=setting.config.get("default_repo_url"),
        )

    return RepoListResponse(repository_urls=[], default_repo_url=None)


@router.delete("/github/repositories")
async def remove_repository_url(
    repo_url: str,
    tenant_id: str = Depends(get_current_tenant_id),
    tenant_manager: TenantDBManager = Depends(get_tenant_manager),
) -> RepoListResponse:
    """Remove a repository URL from the saved list."""
    repo_url = repo_url.strip().rstrip("/")

    async with tenant_manager.get_session(tenant_id) as session:
        result = await session.execute(
            select(ApiSetting).where(
                ApiSetting.tenant_id == tenant_id,
                ApiSetting.service == "github",
            )
        )
        setting = result.scalar_one_or_none()

        if setting and setting.config:
            config = setting.config
            repo_urls = config.get("repository_urls", [])
            if repo_url in repo_urls:
                repo_urls.remove(repo_url)
                config["repository_urls"] = repo_urls
                setting.config = config
                await session.flush()

            return RepoListResponse(
                repository_urls=repo_urls,
                default_repo_url=config.get("default_repo_url"),
            )

    return RepoListResponse(repository_urls=[], default_repo_url=None)
