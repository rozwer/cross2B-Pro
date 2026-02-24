"""Per-step model configuration with intelligent defaults.

Provides centralized model selection logic. All steps default to the
global model_config (Gemini 3 Pro). Per-step overrides can be set via
step_configs from the UI.

Priority order:
1. step_configs (per-step user override from UI)
2. STEP_DEFAULT_MODELS (per-step hardcoded defaults)
3. model_config (global config)

API key resolution (via get_step_llm_client / get_config_llm_client):
1. Database (api_settings table) - keys set via UI settings
2. Environment variables (.env) - fallback
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.api.llm import LLMInterface

logger = logging.getLogger(__name__)

# Explicit default — logged when config omits provider so operators can spot misconfigurations
DEFAULT_LLM_PROVIDER = "gemini"

# Lazy singleton for DB access in worker process
_tenant_manager: Any = None

# No per-step overrides — all steps use global model_config (Gemini 3 Pro)
STEP_DEFAULT_MODELS: dict[str, dict[str, str]] = {}


def get_step_model_config(step_id: str, config: dict) -> tuple[str, str | None]:
    """Determine the model provider and model name for a given step.

    Args:
        step_id: The step identifier (e.g., "step6", "step9")
        config: The full activity config dict containing model_config and step_configs

    Returns:
        (provider, model) tuple
    """
    # 1. Check step_configs (user-specified per-step overrides from UI)
    step_configs = config.get("step_configs")
    if step_configs:
        for sc in step_configs:
            sc_id = sc.get("step_id") if isinstance(sc, dict) else getattr(sc, "step_id", None)
            if sc_id == step_id:
                provider = sc.get("platform") if isinstance(sc, dict) else getattr(sc, "platform", None)
                model = sc.get("model") if isinstance(sc, dict) else getattr(sc, "model", None)
                if provider and model:
                    logger.info(f"[{step_id}] Using UI override: {provider}/{model}")
                    return provider, model

    # 2. Check step-specific defaults for quality-critical steps
    if step_id in STEP_DEFAULT_MODELS:
        defaults = STEP_DEFAULT_MODELS[step_id]
        logger.info(f"[{step_id}] Using step default: {defaults['platform']}/{defaults['model']}")
        return defaults["platform"], defaults["model"]

    # 3. Fall back to global model_config
    model_config = config.get("model_config", {})
    provider = model_config.get("platform", config.get("llm_provider"))
    if not provider:
        provider = DEFAULT_LLM_PROVIDER
        logger.warning(f"[{step_id}] No llm_provider in config — defaulting to '{DEFAULT_LLM_PROVIDER}'")
    model = model_config.get("model", config.get("llm_model"))
    return provider, model


def _get_tenant_manager() -> Any:
    """Get or create lazy singleton TenantDBManager for worker process."""
    global _tenant_manager
    if _tenant_manager is None:
        from apps.api.db.tenant import TenantDBManager

        _tenant_manager = TenantDBManager()
    return _tenant_manager


async def get_step_llm_client(
    step_id: str,
    config: dict[str, Any],
    tenant_id: str | None = None,
) -> LLMInterface:
    """Get LLM client for a step, resolving API key from DB then ENV.

    Combines model selection (get_step_model_config) with settings-aware
    client creation. Use this in Activity.execute() methods.

    Args:
        step_id: Step identifier (e.g., "step0", "step6")
        config: Full activity config dict
        tenant_id: Tenant ID for DB key lookup

    Returns:
        Configured LLMInterface with correct API key and model
    """
    from apps.api.llm import get_llm_client_with_settings

    provider, model = get_step_model_config(step_id, config)

    kwargs: dict[str, Any] = {}
    if model:
        kwargs["model"] = model

    manager = _get_tenant_manager() if tenant_id else None
    return await get_llm_client_with_settings(
        provider,
        tenant_id=tenant_id,
        tenant_manager=manager,
        **kwargs,
    )


async def get_config_llm_client(
    config: dict[str, Any],
    tenant_id: str | None = None,
) -> LLMInterface:
    """Get LLM client from config dict, resolving API key from DB then ENV.

    Use this in graph functions that read provider/model from config directly
    (not via get_step_model_config).

    Args:
        config: Config dict with llm_provider and llm_model keys
        tenant_id: Tenant ID for DB key lookup

    Returns:
        Configured LLMInterface with correct API key and model
    """
    from apps.api.llm import get_llm_client_with_settings

    provider = config.get("llm_provider")
    if not provider:
        provider = DEFAULT_LLM_PROVIDER
        logger.warning(f"No llm_provider in config — defaulting to '{DEFAULT_LLM_PROVIDER}'")
    model = config.get("llm_model")

    kwargs: dict[str, Any] = {}
    if model:
        kwargs["model"] = model

    manager = _get_tenant_manager() if tenant_id else None
    return await get_llm_client_with_settings(
        provider,
        tenant_id=tenant_id,
        tenant_manager=manager,
        **kwargs,
    )
