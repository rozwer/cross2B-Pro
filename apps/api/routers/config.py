"""Configuration router.

Handles model configuration and workflow step defaults.
"""

import logging
import os

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from apps.api.db.models import LLMModel, LLMProvider
from apps.api.db.tenant import TenantDBManager, get_tenant_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["config"])


# =============================================================================
# Pydantic Models
# =============================================================================


class ProviderConfig(BaseModel):
    """Provider configuration with available models."""

    provider: str
    default_model: str
    available_models: list[str]
    supports_grounding: bool = False


class StepDefaultConfig(BaseModel):
    """Default configuration for a workflow step."""

    step_id: str
    label: str
    description: str
    ai_model: str  # gemini, openai, anthropic
    model_name: str
    temperature: float
    grounding: bool
    retry_limit: int
    repair_enabled: bool
    is_configurable: bool
    recommended_model: str


class ModelsConfigResponse(BaseModel):
    """Response for GET /api/config/models."""

    providers: list[ProviderConfig]
    step_defaults: list[StepDefaultConfig]


# =============================================================================
# Step Default Configurations (source of truth for FE)
# =============================================================================


def _get_workflow_step_defaults() -> list[StepDefaultConfig]:
    """Get workflow step defaults with current environment variables."""
    return [
        StepDefaultConfig(
            step_id="step-1",
            label="入力",
            description="キーワードとターゲット情報の入力",
            ai_model="gemini",
            model_name=os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash"),
            temperature=0.7,
            grounding=False,
            retry_limit=3,
            repair_enabled=True,
            is_configurable=False,
            recommended_model="gemini",
        ),
        StepDefaultConfig(
            step_id="step0",
            label="キーワード選定",
            description="キーワードの分析と最適化",
            ai_model="gemini",
            model_name=os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash"),
            temperature=0.7,
            grounding=True,
            retry_limit=3,
            repair_enabled=True,
            is_configurable=True,
            recommended_model="gemini",
        ),
        StepDefaultConfig(
            step_id="step1",
            label="競合記事取得",
            description="SERP分析と競合コンテンツの収集",
            ai_model="gemini",
            model_name=os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash"),
            temperature=0.5,
            grounding=True,
            retry_limit=3,
            repair_enabled=True,
            is_configurable=True,
            recommended_model="gemini",
        ),
        StepDefaultConfig(
            step_id="step1_5",
            label="関連KW競合抽出",
            description="関連キーワードの競合本文を抽出",
            ai_model="gemini",
            model_name=os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash"),
            temperature=0.3,
            grounding=True,
            retry_limit=3,
            repair_enabled=True,
            is_configurable=True,
            recommended_model="gemini",
        ),
        StepDefaultConfig(
            step_id="step2",
            label="CSV検証",
            description="取得データの形式検証",
            ai_model="gemini",
            model_name=os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash"),
            temperature=0.3,
            grounding=False,
            retry_limit=3,
            repair_enabled=True,
            is_configurable=True,
            recommended_model="gemini",
        ),
        StepDefaultConfig(
            step_id="step3a",
            label="クエリ分析",
            description="検索クエリとペルソナの分析",
            ai_model="gemini",
            model_name=os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash"),
            temperature=0.7,
            grounding=True,
            retry_limit=3,
            repair_enabled=True,
            is_configurable=True,
            recommended_model="gemini",
        ),
        StepDefaultConfig(
            step_id="step3b",
            label="共起語抽出",
            description="関連キーワードと共起語の抽出",
            ai_model="gemini",
            model_name=os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash"),
            temperature=0.7,
            grounding=True,
            retry_limit=3,
            repair_enabled=True,
            is_configurable=True,
            recommended_model="gemini",
        ),
        StepDefaultConfig(
            step_id="step3c",
            label="競合分析",
            description="競合記事の差別化ポイント分析",
            ai_model="gemini",
            model_name=os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash"),
            temperature=0.7,
            grounding=False,
            retry_limit=3,
            repair_enabled=True,
            is_configurable=True,
            recommended_model="gemini",
        ),
        StepDefaultConfig(
            step_id="step3_5",
            label="人間味生成",
            description="心情傾向・体験エピソードの生成",
            ai_model="gemini",
            model_name="gemini-1.5-pro",
            temperature=0.7,
            grounding=False,
            retry_limit=3,
            repair_enabled=True,
            is_configurable=True,
            recommended_model="gemini",
        ),
        StepDefaultConfig(
            step_id="approval",
            label="承認待ち",
            description="人間による確認・承認ポイント",
            ai_model="gemini",
            model_name="",
            temperature=0,
            grounding=False,
            retry_limit=1,
            repair_enabled=False,
            is_configurable=False,
            recommended_model="gemini",
        ),
        StepDefaultConfig(
            step_id="step4",
            label="アウトライン",
            description="戦略的な記事構成の作成",
            ai_model="anthropic",
            model_name=os.getenv("ANTHROPIC_DEFAULT_MODEL", "claude-sonnet-4-5-20250929"),
            temperature=0.7,
            grounding=False,
            retry_limit=3,
            repair_enabled=True,
            is_configurable=True,
            recommended_model="anthropic",
        ),
        StepDefaultConfig(
            step_id="step5",
            label="一次情報収集",
            description="Web検索による一次情報の収集",
            ai_model="gemini",
            model_name=os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash"),
            temperature=0.5,
            grounding=True,
            retry_limit=3,
            repair_enabled=True,
            is_configurable=True,
            recommended_model="gemini",
        ),
        StepDefaultConfig(
            step_id="step6",
            label="アウトライン強化",
            description="一次情報を組み込んだ構成改善",
            ai_model="anthropic",
            model_name=os.getenv("ANTHROPIC_DEFAULT_MODEL", "claude-sonnet-4-20250514"),
            temperature=0.7,
            grounding=False,
            retry_limit=3,
            repair_enabled=True,
            is_configurable=True,
            recommended_model="anthropic",
        ),
        StepDefaultConfig(
            step_id="step6.5",
            label="統合パッケージ",
            description="全情報の統合とパッケージ化",
            ai_model="anthropic",
            model_name=os.getenv("ANTHROPIC_DEFAULT_MODEL", "claude-sonnet-4-20250514"),
            temperature=0.5,
            grounding=False,
            retry_limit=3,
            repair_enabled=True,
            is_configurable=True,
            recommended_model="anthropic",
        ),
        StepDefaultConfig(
            step_id="step7a",
            label="本文生成",
            description="初稿の本文生成",
            ai_model="anthropic",
            model_name=os.getenv("ANTHROPIC_DEFAULT_MODEL", "claude-sonnet-4-20250514"),
            temperature=0.8,
            grounding=False,
            retry_limit=3,
            repair_enabled=True,
            is_configurable=True,
            recommended_model="anthropic",
        ),
        StepDefaultConfig(
            step_id="step7b",
            label="ブラッシュアップ",
            description="文章の磨き上げと最適化",
            ai_model="gemini",
            model_name=os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash"),
            temperature=0.6,
            grounding=False,
            retry_limit=3,
            repair_enabled=True,
            is_configurable=True,
            recommended_model="gemini",
        ),
        StepDefaultConfig(
            step_id="step8",
            label="ファクトチェック",
            description="事実確認とFAQ生成",
            ai_model="gemini",
            model_name=os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash"),
            temperature=0.3,
            grounding=True,
            retry_limit=3,
            repair_enabled=True,
            is_configurable=True,
            recommended_model="gemini",
        ),
        StepDefaultConfig(
            step_id="step9",
            label="最終リライト",
            description="品質管理と最終調整",
            ai_model="anthropic",
            model_name=os.getenv("ANTHROPIC_DEFAULT_MODEL", "claude-sonnet-4-20250514"),
            temperature=0.5,
            grounding=False,
            retry_limit=3,
            repair_enabled=True,
            is_configurable=True,
            recommended_model="anthropic",
        ),
        StepDefaultConfig(
            step_id="step10",
            label="最終出力",
            description="HTML/Markdown形式での出力",
            ai_model="anthropic",
            model_name=os.getenv("ANTHROPIC_DEFAULT_MODEL", "claude-sonnet-4-20250514"),
            temperature=0.3,
            grounding=False,
            retry_limit=3,
            repair_enabled=True,
            is_configurable=True,
            recommended_model="anthropic",
        ),
        StepDefaultConfig(
            step_id="step11",
            label="画像生成",
            description="AI画像生成と記事への挿入",
            ai_model="gemini",
            model_name=os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.0-flash"),
            temperature=0.7,
            grounding=False,
            retry_limit=3,
            repair_enabled=True,
            is_configurable=True,
            recommended_model="gemini",
        ),
        StepDefaultConfig(
            step_id="step12",
            label="WordPress HTML",
            description="Gutenbergブロック形式でのHTML生成",
            ai_model="anthropic",
            model_name=os.getenv("ANTHROPIC_DEFAULT_MODEL", "claude-sonnet-4-20250514"),
            temperature=0.3,
            grounding=False,
            retry_limit=3,
            repair_enabled=True,
            is_configurable=True,
            recommended_model="anthropic",
        ),
    ]


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/models", response_model=ModelsConfigResponse)
async def get_models_config(
    tenant_manager: TenantDBManager = Depends(get_tenant_manager),
) -> ModelsConfigResponse:
    """Get available models and default workflow step configurations.

    This endpoint provides:
    - Available LLM providers with their models (from database)
    - Default configuration for each workflow step

    The frontend should use this as the source of truth for model names
    and step configurations.
    """
    # Default models from environment variables
    default_models = {
        "gemini": os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.5-flash"),
        "openai": os.getenv("OPENAI_DEFAULT_MODEL", "gpt-5.2"),
        "anthropic": os.getenv("ANTHROPIC_DEFAULT_MODEL", "claude-sonnet-4-5-20250929"),
    }

    # Grounding support by provider
    grounding_support = {
        "gemini": True,
        "openai": False,
        "anthropic": False,
    }

    tenant_id = os.getenv("DEV_TENANT_ID", os.getenv("DEFAULT_TENANT_ID", "default"))

    providers: list[ProviderConfig] = []

    try:
        async with tenant_manager.get_session(tenant_id) as session:
            # Get all providers
            providers_result = await session.execute(
                select(LLMProvider).where(LLMProvider.is_active == True).order_by(LLMProvider.id)  # noqa: E712
            )
            db_providers = providers_result.scalars().all()

            # Get all active models
            models_result = await session.execute(
                select(LLMModel).where(LLMModel.is_active == True).order_by(LLMModel.model_name)  # noqa: E712
            )
            db_models = models_result.scalars().all()

            # Group models by provider
            models_by_provider: dict[str, list[str]] = {}
            for model in db_models:
                if model.provider_id not in models_by_provider:
                    models_by_provider[model.provider_id] = []
                models_by_provider[model.provider_id].append(model.model_name)

            # Build provider configs
            for provider in db_providers:
                provider_models = models_by_provider.get(provider.id, [])
                default_model = default_models.get(provider.id, provider_models[0] if provider_models else "")

                # Ensure default model is in the list
                if default_model and default_model not in provider_models:
                    provider_models.insert(0, default_model)

                providers.append(
                    ProviderConfig(
                        provider=provider.id,
                        default_model=default_model,
                        available_models=provider_models,
                        supports_grounding=grounding_support.get(provider.id, False),
                    )
                )
    except Exception as e:
        logger.warning(f"Failed to load models from DB, using fallback: {e}")
        # Fallback to hardcoded values if DB fails
        providers = [
            ProviderConfig(
                provider="gemini",
                default_model=default_models["gemini"],
                available_models=[default_models["gemini"], "gemini-2.5-flash", "gemini-2.5-pro"],
                supports_grounding=True,
            ),
            ProviderConfig(
                provider="openai",
                default_model=default_models["openai"],
                available_models=[default_models["openai"], "gpt-4o", "gpt-4o-mini"],
                supports_grounding=False,
            ),
            ProviderConfig(
                provider="anthropic",
                default_model=default_models["anthropic"],
                available_models=[default_models["anthropic"], "claude-3-5-sonnet-20241022"],
                supports_grounding=False,
            ),
        ]

    return ModelsConfigResponse(
        providers=providers,
        step_defaults=_get_workflow_step_defaults(),
    )
