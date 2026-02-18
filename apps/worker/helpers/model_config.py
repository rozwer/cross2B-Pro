"""Per-step model configuration with intelligent defaults.

Provides centralized model selection logic. All steps default to the
global model_config (Gemini 3 Pro). Per-step overrides can be set via
step_configs from the UI.

Priority order:
1. step_configs (per-step user override from UI)
2. STEP_DEFAULT_MODELS (per-step hardcoded defaults)
3. model_config (global config)
"""

import logging

logger = logging.getLogger(__name__)

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
    provider = model_config.get("platform", config.get("llm_provider", "gemini"))
    model = model_config.get("model", config.get("llm_model"))
    return provider, model
