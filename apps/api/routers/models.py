"""Models router for LLM provider and model configuration.

Handles CRUD operations for LLM providers and models.
Models are stored in the common DB (llm_providers, llm_models tables).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from apps.api.db.models import LLMModel, LLMProvider
from apps.api.db.tenant import TenantDBManager, get_tenant_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/models", tags=["models"])


# =============================================================================
# Pydantic Models
# =============================================================================


class ModelResponse(BaseModel):
    """Response model for a single LLM model."""

    id: int
    provider_id: str
    model_name: str
    model_class: str
    is_active: bool


class ProviderResponse(BaseModel):
    """Response model for a provider with its models."""

    id: str
    display_name: str
    is_active: bool
    models: list[ModelResponse]


class ProvidersListResponse(BaseModel):
    """Response model for providers list."""

    providers: list[ProviderResponse]


class ModelCreateRequest(BaseModel):
    """Request model for creating a new LLM model."""

    provider_id: str = Field(..., description="Provider ID (gemini, openai, anthropic)")
    model_name: str = Field(..., min_length=1, max_length=128, description="Model name")
    model_class: str = Field("standard", description="Model class (standard, pro)")


class ModelUpdateRequest(BaseModel):
    """Request model for updating an LLM model."""

    model_class: str | None = Field(None, description="Model class (standard, pro)")
    is_active: bool | None = Field(None, description="Whether the model is active")


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=ProvidersListResponse)
async def get_all_models(
    tenant_manager: TenantDBManager = Depends(get_tenant_manager),
) -> ProvidersListResponse:
    """Get all LLM providers with their models.

    Returns providers and their available models from the database.
    """
    import os

    tenant_id = os.getenv("DEV_TENANT_ID", os.getenv("DEFAULT_TENANT_ID", "default"))

    async with tenant_manager.get_session(tenant_id) as session:
        # Get all providers
        providers_result = await session.execute(select(LLMProvider).order_by(LLMProvider.id))
        providers = providers_result.scalars().all()

        # Get all models
        models_result = await session.execute(select(LLMModel).order_by(LLMModel.provider_id, LLMModel.model_name))
        models = models_result.scalars().all()

        # Group models by provider
        models_by_provider: dict[str, list[ModelResponse]] = {}
        for model in models:
            if model.provider_id not in models_by_provider:
                models_by_provider[model.provider_id] = []
            models_by_provider[model.provider_id].append(
                ModelResponse(
                    id=model.id,
                    provider_id=model.provider_id,
                    model_name=model.model_name,
                    model_class=model.model_class,
                    is_active=model.is_active,
                )
            )

        # Build response
        provider_responses = []
        for provider in providers:
            provider_responses.append(
                ProviderResponse(
                    id=provider.id,
                    display_name=provider.display_name,
                    is_active=provider.is_active,
                    models=models_by_provider.get(provider.id, []),
                )
            )

        return ProvidersListResponse(providers=provider_responses)


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider_models(
    provider_id: str,
    tenant_manager: TenantDBManager = Depends(get_tenant_manager),
) -> ProviderResponse:
    """Get a specific provider with its models."""
    import os

    tenant_id = os.getenv("DEV_TENANT_ID", os.getenv("DEFAULT_TENANT_ID", "default"))

    async with tenant_manager.get_session(tenant_id) as session:
        # Get provider
        provider_result = await session.execute(select(LLMProvider).where(LLMProvider.id == provider_id))
        provider = provider_result.scalar_one_or_none()

        if not provider:
            raise HTTPException(
                status_code=404,
                detail=f"Provider not found: {provider_id}",
            )

        # Get models for this provider
        models_result = await session.execute(select(LLMModel).where(LLMModel.provider_id == provider_id).order_by(LLMModel.model_name))
        models = models_result.scalars().all()

        return ProviderResponse(
            id=provider.id,
            display_name=provider.display_name,
            is_active=provider.is_active,
            models=[
                ModelResponse(
                    id=m.id,
                    provider_id=m.provider_id,
                    model_name=m.model_name,
                    model_class=m.model_class,
                    is_active=m.is_active,
                )
                for m in models
            ],
        )


@router.post("", response_model=ModelResponse)
async def create_model(
    request: ModelCreateRequest,
    tenant_manager: TenantDBManager = Depends(get_tenant_manager),
) -> ModelResponse:
    """Create a new LLM model."""
    import os

    tenant_id = os.getenv("DEV_TENANT_ID", os.getenv("DEFAULT_TENANT_ID", "default"))

    async with tenant_manager.get_session(tenant_id) as session:
        # Verify provider exists
        provider_result = await session.execute(select(LLMProvider).where(LLMProvider.id == request.provider_id))
        provider = provider_result.scalar_one_or_none()

        if not provider:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown provider: {request.provider_id}. Valid: gemini, openai, anthropic",
            )

        # Check for duplicate
        existing_result = await session.execute(
            select(LLMModel).where(
                LLMModel.provider_id == request.provider_id,
                LLMModel.model_name == request.model_name,
            )
        )
        if existing_result.scalar_one_or_none():
            raise HTTPException(
                status_code=409,
                detail=f"Model already exists: {request.provider_id}/{request.model_name}",
            )

        # Create model
        model = LLMModel(
            provider_id=request.provider_id,
            model_name=request.model_name,
            model_class=request.model_class,
            is_active=True,
        )
        session.add(model)
        await session.flush()

        logger.info(f"Created LLM model: {request.provider_id}/{request.model_name}")

        return ModelResponse(
            id=model.id,
            provider_id=model.provider_id,
            model_name=model.model_name,
            model_class=model.model_class,
            is_active=model.is_active,
        )


@router.patch("/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: int,
    request: ModelUpdateRequest,
    tenant_manager: TenantDBManager = Depends(get_tenant_manager),
) -> ModelResponse:
    """Update an LLM model."""
    import os

    tenant_id = os.getenv("DEV_TENANT_ID", os.getenv("DEFAULT_TENANT_ID", "default"))

    async with tenant_manager.get_session(tenant_id) as session:
        result = await session.execute(select(LLMModel).where(LLMModel.id == model_id))
        model = result.scalar_one_or_none()

        if not model:
            raise HTTPException(
                status_code=404,
                detail=f"Model not found: {model_id}",
            )

        if request.model_class is not None:
            model.model_class = request.model_class
        if request.is_active is not None:
            model.is_active = request.is_active

        await session.flush()

        logger.info(f"Updated LLM model: {model.provider_id}/{model.model_name}")

        return ModelResponse(
            id=model.id,
            provider_id=model.provider_id,
            model_name=model.model_name,
            model_class=model.model_class,
            is_active=model.is_active,
        )


@router.delete("/{model_id}")
async def delete_model(
    model_id: int,
    tenant_manager: TenantDBManager = Depends(get_tenant_manager),
) -> dict[str, str]:
    """Delete an LLM model."""
    import os

    tenant_id = os.getenv("DEV_TENANT_ID", os.getenv("DEFAULT_TENANT_ID", "default"))

    async with tenant_manager.get_session(tenant_id) as session:
        result = await session.execute(select(LLMModel).where(LLMModel.id == model_id))
        model = result.scalar_one_or_none()

        if not model:
            raise HTTPException(
                status_code=404,
                detail=f"Model not found: {model_id}",
            )

        model_info = f"{model.provider_id}/{model.model_name}"
        await session.delete(model)
        await session.flush()

        logger.info(f"Deleted LLM model: {model_info}")

        return {"message": f"Model deleted: {model_info}"}
