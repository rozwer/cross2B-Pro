"""Settings provider service for API keys and model configuration.

Provides a unified interface to retrieve settings from:
1. Database (api_settings table) - highest priority
2. Environment variables - fallback

This service is used by LLM clients and external service integrations
to obtain API keys without direct coupling to DB or env implementation.

SECURITY:
- All API keys are decrypted only when needed
- tenant_id must always be provided for DB lookups
- Environment variable fallback is tenant-agnostic
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select

from apps.api.db.models import ApiSetting
from apps.api.db.tenant import TenantDBManager
from apps.api.services.encryption import decrypt

logger = logging.getLogger(__name__)


@dataclass
class ServiceSettings:
    """Settings for a single service."""

    service: str
    api_key: str | None = None
    default_model: str | None = None
    config: dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    source: str = "none"  # "db", "env", "none"


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


class SettingsProvider:
    """Provider for service settings.

    Retrieves settings from DB with fallback to environment variables.
    Designed to be used in async contexts (FastAPI, Temporal activities).

    Example usage:
        provider = SettingsProvider(tenant_db_manager)
        settings = await provider.get_settings("gemini", tenant_id="tenant-123")
        if settings.api_key:
            client = GeminiClient(api_key=settings.api_key, model=settings.default_model)
    """

    def __init__(self, tenant_manager: TenantDBManager | None = None):
        """Initialize the settings provider.

        Args:
            tenant_manager: TenantDBManager instance. If None, only
                           environment variables will be used.
        """
        self._tenant_manager = tenant_manager

    async def get_settings(
        self,
        service: str,
        tenant_id: str | None = None,
    ) -> ServiceSettings:
        """Get settings for a service.

        Lookup order:
        1. If tenant_id provided and tenant_manager available: check DB
        2. Fall back to environment variables

        Args:
            service: Service name (gemini, openai, anthropic, serp, etc.)
            tenant_id: Tenant ID for DB lookup. If None, uses env vars only.

        Returns:
            ServiceSettings with api_key, default_model, and config
        """
        service = service.lower()

        # Try DB first if tenant context is available
        if tenant_id and self._tenant_manager:
            try:
                db_settings = await self._get_from_db(service, tenant_id)
                if db_settings and db_settings.api_key:
                    logger.debug(f"Using DB settings for {service} (tenant: {tenant_id})")
                    return db_settings
            except Exception as e:
                logger.warning(f"Failed to get DB settings for {service}: {e}")

        # Fall back to environment variables
        env_settings = self._get_from_env(service)
        if env_settings.api_key:
            logger.debug(f"Using env settings for {service}")
        return env_settings

    async def _get_from_db(
        self,
        service: str,
        tenant_id: str,
    ) -> ServiceSettings | None:
        """Get settings from database.

        Args:
            service: Service name
            tenant_id: Tenant ID for scoped lookup

        Returns:
            ServiceSettings if found and has API key, None otherwise
        """
        if not self._tenant_manager:
            return None

        async with self._tenant_manager.get_session(tenant_id) as session:
            result = await session.execute(
                select(ApiSetting).where(
                    ApiSetting.tenant_id == tenant_id,
                    ApiSetting.service == service,
                )
            )
            setting = result.scalar_one_or_none()

            if not setting or not setting.api_key_encrypted:
                return None

            if not setting.is_active:
                logger.debug(f"Service {service} is inactive for tenant {tenant_id}")
                return ServiceSettings(
                    service=service,
                    api_key=None,
                    is_active=False,
                    source="db",
                )

            try:
                decrypted_key = decrypt(setting.api_key_encrypted)
            except Exception as e:
                logger.error(f"Failed to decrypt API key for {service}: {e}")
                return None

            return ServiceSettings(
                service=service,
                api_key=decrypted_key,
                default_model=setting.default_model,
                config=setting.config or {},
                is_active=setting.is_active,
                source="db",
            )

    def _get_from_env(self, service: str) -> ServiceSettings:
        """Get settings from environment variables.

        Args:
            service: Service name

        Returns:
            ServiceSettings with values from environment
        """
        env_var = ENV_VAR_MAP.get(service)
        api_key = os.getenv(env_var) if env_var else None

        model_env = DEFAULT_MODEL_ENV_MAP.get(service)
        default_model = os.getenv(model_env) if model_env else None

        return ServiceSettings(
            service=service,
            api_key=api_key,
            default_model=default_model,
            config={},
            is_active=True,
            source="env" if api_key else "none",
        )

    async def get_llm_settings(
        self,
        provider: str,
        tenant_id: str | None = None,
    ) -> ServiceSettings:
        """Convenience method for LLM providers.

        Same as get_settings() but validates the provider name.

        Args:
            provider: LLM provider (gemini, openai, anthropic)
            tenant_id: Tenant ID for DB lookup

        Returns:
            ServiceSettings for the LLM provider

        Raises:
            ValueError: If provider is not a valid LLM provider
        """
        llm_providers = {"gemini", "openai", "anthropic"}
        if provider.lower() not in llm_providers:
            raise ValueError(f"Unknown LLM provider: {provider}. Valid: {llm_providers}")

        return await self.get_settings(provider, tenant_id)


# Global singleton for convenience (initialized lazily)
_settings_provider: SettingsProvider | None = None


def get_settings_provider(tenant_manager: TenantDBManager | None = None) -> SettingsProvider:
    """Get or create the global settings provider.

    For dependency injection in FastAPI, prefer passing tenant_manager explicitly.
    This is provided for convenience in Temporal activities and other contexts.

    Args:
        tenant_manager: TenantDBManager to use. If None and provider not initialized,
                       creates a provider that only uses env vars.

    Returns:
        SettingsProvider instance
    """
    global _settings_provider

    if _settings_provider is None:
        _settings_provider = SettingsProvider(tenant_manager)
    elif tenant_manager is not None and _settings_provider._tenant_manager is None:
        # Upgrade provider with tenant manager
        _settings_provider._tenant_manager = tenant_manager

    return _settings_provider


def reset_settings_provider() -> None:
    """Reset the global settings provider. Mainly for testing."""
    global _settings_provider
    _settings_provider = None
