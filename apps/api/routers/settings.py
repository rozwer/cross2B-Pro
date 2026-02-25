"""Settings router for API key and model configuration.

Handles CRUD operations for external service settings.
All API keys are encrypted at rest and masked in responses.

SECURITY:
- API keys are encrypted with AES-256-GCM
- Keys are masked in all responses (show only last 4 chars, or first 4 for GitHub)
- GitHub tokens get extra warnings about exposure risks
- All changes are logged to audit_logs
"""

import asyncio
import logging
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
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
    # Google Ads-specific options (stored encrypted in config JSON)
    client_id: str | None = None
    client_secret: str | None = None
    refresh_token: str | None = None
    customer_id: str | None = None


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
    "google_ads": "GOOGLE_ADS_DEVELOPER_TOKEN",
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


def _build_google_ads_config_from_env() -> ServiceConfig | None:
    """Build Google Ads config from environment variables (masked)."""
    client_id = os.getenv("GOOGLE_ADS_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_ADS_CLIENT_SECRET")
    refresh_token = os.getenv("GOOGLE_ADS_REFRESH_TOKEN")
    customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID")
    if not any([client_id, client_secret, refresh_token, customer_id]):
        return None
    return ServiceConfig(
        client_id=mask_api_key(client_id, "google_ads") if client_id else None,
        client_secret=mask_api_key(client_secret, "google_ads") if client_secret else None,
        refresh_token=mask_api_key(refresh_token, "google_ads") if refresh_token else None,
        customer_id=customer_id,  # Not a secret, show full value
    )


def _mask_google_ads_config(config_data: dict) -> ServiceConfig:
    """Mask sensitive fields in Google Ads config from DB."""
    masked = dict(config_data)
    for secret_field in ("client_secret", "refresh_token"):
        if secret_field in masked and masked[secret_field]:
            try:
                decrypted = decrypt(masked[secret_field])
                masked[secret_field] = mask_api_key(decrypted, "google_ads")
            except EncryptionError:
                masked[secret_field] = "****"
    # client_id: not encrypted, mask it
    if "client_id" in masked and masked["client_id"]:
        masked["client_id"] = mask_api_key(masked["client_id"], "google_ads")
    # customer_id: not a secret, show full
    return ServiceConfig(**masked)


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
            # For Google Ads, mask sensitive config fields
            config = None
            if setting.config:
                if service == "google_ads":
                    config = _mask_google_ads_config(setting.config)
                else:
                    config = ServiceConfig(**(setting.config))
            return SettingResponse(
                service=service,
                api_key_masked=masked_key,
                default_model=setting.default_model,
                config=config,
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
        # For Google Ads, also return env-sourced config (masked)
        config = _build_google_ads_config_from_env() if service == "google_ads" else None
        return SettingResponse(
            service=service,
            api_key_masked=masked_key,
            default_model=default_model,
            config=config,
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
            config_data = request.config.model_dump(exclude_none=True)
            # Encrypt sensitive Google Ads fields in config
            if service == "google_ads":
                for secret_field in ("client_secret", "refresh_token"):
                    if secret_field in config_data and config_data[secret_field]:
                        config_data[secret_field] = encrypt(config_data[secret_field])
            setting.config = config_data

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


# =============================================================================
# Google Ads OAuth (Refresh Token Acquisition)
# =============================================================================

GOOGLE_OAUTH_SCOPE = "https://www.googleapis.com/auth/adwords"
GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

# Temporary in-memory store for OAuth state tokens (TTL: 5 minutes)
_oauth_states: dict[str, dict[str, Any]] = {}


class OAuthStartRequest(BaseModel):
    """Request to start Google Ads OAuth flow."""

    client_id: str = Field(..., description="OAuth Client ID")
    client_secret: str = Field(..., description="OAuth Client Secret")


class OAuthStartResponse(BaseModel):
    """Response with OAuth authorization URL."""

    auth_url: str
    state: str


def _get_oauth_redirect_uri() -> str:
    """Get the OAuth redirect URI for Google Ads OAuth flow."""
    base_url = os.getenv("API_BASE_URL", "http://localhost:28000")
    return f"{base_url}/api/settings/google-ads/oauth-callback"


def _cleanup_expired_oauth_states() -> None:
    """Remove OAuth states older than 5 minutes."""
    cutoff = datetime.now(UTC) - timedelta(minutes=5)
    expired = [k for k, v in _oauth_states.items() if v["created_at"] < cutoff]
    for k in expired:
        del _oauth_states[k]


@router.post("/google-ads/oauth-start", response_model=OAuthStartResponse)
async def google_ads_oauth_start(request: OAuthStartRequest) -> OAuthStartResponse:
    """Start Google Ads OAuth flow to obtain a refresh token.

    Generates an authorization URL and stores credentials temporarily
    for the callback to use when exchanging the authorization code.

    NOTE: The redirect URI must be registered in Google Cloud Console:
    APIs & Services > Credentials > OAuth 2.0 Client ID > Authorized redirect URIs
    """
    _cleanup_expired_oauth_states()

    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "client_id": request.client_id,
        "client_secret": request.client_secret,
        "created_at": datetime.now(UTC),
    }

    redirect_uri = _get_oauth_redirect_uri()
    params = urlencode({
        "client_id": request.client_id,
        "redirect_uri": redirect_uri,
        "scope": GOOGLE_OAUTH_SCOPE,
        "response_type": "code",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    })
    auth_url = f"{GOOGLE_AUTH_ENDPOINT}?{params}"

    return OAuthStartResponse(auth_url=auth_url, state=state)


@router.get("/google-ads/oauth-callback", response_class=HTMLResponse)
async def google_ads_oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> HTMLResponse:
    """Handle Google OAuth callback.

    Exchanges the authorization code for tokens and returns an HTML page
    that communicates the refresh token back to the opener window via postMessage.
    """
    if error:
        return HTMLResponse(content=_oauth_error_html(f"OAuth error: {error}"), status_code=400)

    if not code or not state:
        return HTMLResponse(content=_oauth_error_html("Missing code or state parameter"), status_code=400)

    _cleanup_expired_oauth_states()

    if state not in _oauth_states:
        return HTMLResponse(
            content=_oauth_error_html("認証セッションが無効または期限切れです。もう一度お試しください。"),
            status_code=400,
        )

    creds = _oauth_states.pop(state)
    redirect_uri = _get_oauth_redirect_uri()

    try:
        import requests as http_requests

        def _exchange_code() -> dict:
            resp = http_requests.post(
                GOOGLE_TOKEN_ENDPOINT,
                data={
                    "client_id": creds["client_id"],
                    "client_secret": creds["client_secret"],
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                timeout=30,
            )
            return resp.json()

        tokens = await asyncio.to_thread(_exchange_code)
    except Exception as e:
        logger.error(f"OAuth token exchange failed: {e}")
        return HTMLResponse(content=_oauth_error_html(f"Token exchange failed: {e}"), status_code=500)

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        error_desc = tokens.get("error_description", tokens.get("error", "No refresh token in response"))
        return HTMLResponse(content=_oauth_error_html(error_desc), status_code=400)

    return HTMLResponse(content=_oauth_success_html(refresh_token))


def _oauth_success_html(refresh_token: str) -> str:
    """Generate HTML page that sends refresh token via postMessage."""
    escaped_token = refresh_token.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
    return f"""<!DOCTYPE html>
<html lang="ja">
<head><meta charset="utf-8"><title>OAuth 認証成功</title>
<style>
  body {{ font-family: system-ui, sans-serif; display: flex; justify-content: center;
         align-items: center; min-height: 100vh; margin: 0; background: #f0fdf4; }}
  .card {{ background: white; padding: 2rem; border-radius: 12px;
           box-shadow: 0 4px 12px rgba(0,0,0,.1); text-align: center; max-width: 400px; }}
  .icon {{ font-size: 3rem; margin-bottom: 1rem; }}
  h2 {{ color: #166534; margin: 0 0 0.5rem; }}
  p {{ color: #6b7280; margin: 0; }}
</style></head>
<body>
<div class="card">
  <div class="icon">&#10004;</div>
  <h2>認証成功</h2>
  <p>Refresh Token を取得しました。<br>このタブは自動的に閉じます...</p>
</div>
<script>
  if (window.opener) {{
    window.opener.postMessage({{
      type: 'google-ads-oauth-callback',
      refresh_token: '{escaped_token}'
    }}, '*');
    setTimeout(function() {{ window.close(); }}, 2000);
  }}
</script>
</body></html>"""


def _oauth_error_html(error_message: str) -> str:
    """Generate HTML page for OAuth errors."""
    from html import escape

    escaped = escape(error_message)
    return f"""<!DOCTYPE html>
<html lang="ja">
<head><meta charset="utf-8"><title>OAuth エラー</title>
<style>
  body {{ font-family: system-ui, sans-serif; display: flex; justify-content: center;
         align-items: center; min-height: 100vh; margin: 0; background: #fef2f2; }}
  .card {{ background: white; padding: 2rem; border-radius: 12px;
           box-shadow: 0 4px 12px rgba(0,0,0,.1); text-align: center; max-width: 400px; }}
  .icon {{ font-size: 3rem; margin-bottom: 1rem; }}
  h2 {{ color: #991b1b; margin: 0 0 0.5rem; }}
  p {{ color: #6b7280; margin: 0; }}
  .error {{ color: #dc2626; font-size: 0.875rem; margin-top: 0.5rem; }}
</style></head>
<body>
<div class="card">
  <div class="icon">&#10060;</div>
  <h2>認証エラー</h2>
  <p class="error">{escaped}</p>
  <p style="margin-top: 1rem;">このタブを閉じて、もう一度お試しください。</p>
</div>
</body></html>"""
