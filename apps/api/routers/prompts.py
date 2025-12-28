"""Prompts router.

Handles prompt management (JSON file based).
"""

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from apps.api.prompts.loader import PromptPackLoader, PromptPackNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


# =============================================================================
# Pydantic Models
# =============================================================================


class PromptJsonResponse(BaseModel):
    """Prompt response from JSON file."""

    step: str
    version: int
    content: str
    variables: dict[str, Any] | None = None


class PromptListJsonResponse(BaseModel):
    """List of prompts from JSON file."""

    pack_id: str
    prompts: list[PromptJsonResponse]
    total: int


class UpdatePromptJsonInput(BaseModel):
    """Request to update a prompt in JSON file."""

    content: str = Field(..., description="Updated prompt content")
    variables: dict[str, Any] | None = Field(None, description="Updated variable definitions")


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=PromptListJsonResponse)
async def list_prompts(
    pack_id: str = Query(default="default", description="Prompt pack ID"),
    step: str | None = Query(default=None, description="Filter by step name"),
) -> PromptListJsonResponse:
    """List all prompts from JSON file."""
    logger.debug("Listing prompts from JSON", extra={"pack_id": pack_id, "step": step})

    try:
        loader = PromptPackLoader()
        pack = loader.load(pack_id)

        prompts = []
        for step_id, template in pack.prompts.items():
            if step and step_id != step:
                continue
            prompts.append(
                PromptJsonResponse(
                    step=template.step,
                    version=template.version,
                    content=template.content,
                    variables=template.variables if template.variables else None,
                )
            )

        # Sort by step name
        prompts.sort(key=lambda p: p.step)

        return PromptListJsonResponse(
            pack_id=pack_id,
            prompts=prompts,
            total=len(prompts),
        )

    except PromptPackNotFoundError as e:
        logger.error(f"Prompt pack not found: {e}")
        raise HTTPException(status_code=404, detail=f"Prompt pack '{pack_id}' not found") from e
    except Exception as e:
        logger.error(f"Failed to list prompts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list prompts") from e


@router.get("/step/{step}", response_model=PromptJsonResponse)
async def get_prompt_by_step(
    step: str,
    pack_id: str = Query(default="default", description="Prompt pack ID"),
) -> PromptJsonResponse:
    """Get a specific prompt by step name from JSON file."""
    logger.debug("Getting prompt by step from JSON", extra={"pack_id": pack_id, "step": step})

    try:
        loader = PromptPackLoader()
        pack = loader.load(pack_id)
        template = pack.get_prompt(step)

        return PromptJsonResponse(
            step=template.step,
            version=template.version,
            content=template.content,
            variables=template.variables if template.variables else None,
        )

    except PromptPackNotFoundError as e:
        logger.error(f"Prompt pack not found: {e}")
        raise HTTPException(status_code=404, detail=f"Prompt pack '{pack_id}' not found") from e
    except Exception as e:
        logger.error(f"Failed to get prompt: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail=f"Prompt not found for step: {step}") from e


@router.put("/step/{step}", response_model=PromptJsonResponse)
async def update_prompt_by_step(
    step: str,
    data: UpdatePromptJsonInput,
    pack_id: str = Query(default="default", description="Prompt pack ID"),
) -> PromptJsonResponse:
    """Update a prompt by step name in JSON file."""
    logger.info("Updating prompt in JSON file", extra={"pack_id": pack_id, "step": step})

    try:
        # Load current JSON file
        packs_dir = Path(__file__).parent.parent / "prompts" / "packs"
        json_path = packs_dir / f"{pack_id}.json"

        if not json_path.exists():
            raise HTTPException(status_code=404, detail=f"Prompt pack '{pack_id}' not found")

        with open(json_path, encoding="utf-8") as f:
            pack_data = json.load(f)

        # Check if step exists
        if step not in pack_data.get("prompts", {}):
            raise HTTPException(status_code=404, detail=f"Prompt not found for step: {step}")

        # Update the prompt
        current_version = pack_data["prompts"][step].get("version", 1)
        pack_data["prompts"][step]["content"] = data.content
        pack_data["prompts"][step]["version"] = current_version + 1
        if data.variables is not None:
            pack_data["prompts"][step]["variables"] = data.variables

        # Write back to JSON file
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(pack_data, f, ensure_ascii=False, indent=2)

        # Clear loader cache
        loader = PromptPackLoader()
        loader.invalidate(pack_id)

        logger.info(
            "Prompt updated in JSON file",
            extra={"pack_id": pack_id, "step": step, "new_version": current_version + 1},
        )

        return PromptJsonResponse(
            step=step,
            version=current_version + 1,
            content=data.content,
            variables=data.variables,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update prompt: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update prompt") from e
