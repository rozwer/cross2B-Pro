"""Cost tracking router.

Handles cost breakdown and token usage for runs.
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from apps.api.auth import get_current_user
from apps.api.auth.schemas import AuthUser
from apps.api.db import Artifact as ArtifactModel
from apps.api.db import Run, Step, TenantIdValidationError
from apps.api.storage import ArtifactRef as StorageArtifactRef

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cost"])


# =============================================================================
# Lazy imports to avoid circular dependencies
# =============================================================================


def _get_tenant_db_manager() -> Any:
    """Get tenant DB manager."""
    from apps.api.db.tenant import get_tenant_manager

    return get_tenant_manager()


def _get_artifact_store() -> Any:
    """Get artifact store instance."""
    from apps.api.main import get_artifact_store

    return get_artifact_store()


# =============================================================================
# Pydantic Models
# =============================================================================


class CostBreakdown(BaseModel):
    """Cost breakdown by step."""

    step: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float


class CostResponse(BaseModel):
    """Cost response for a run."""

    run_id: str
    total_cost: float
    total_input_tokens: int
    total_output_tokens: int
    breakdown: list[CostBreakdown]
    currency: str = "USD"


# Default cost rates (per 1K tokens)
DEFAULT_COST_RATES: dict[str, dict[str, float]] = {
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.00375},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
    "gemini-2.0-flash-exp": {"input": 0.0001, "output": 0.0004},
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    "claude-3-5-haiku-20241022": {"input": 0.0008, "output": 0.004},
}


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/api/runs/{run_id}/cost", response_model=CostResponse)
async def get_run_cost(
    run_id: str,
    user: AuthUser = Depends(get_current_user),
) -> CostResponse:
    """Get cost breakdown for a run.

    Calculates cost based on token usage stored in artifacts.
    """
    tenant_id = user.tenant_id
    logger.debug(
        "Getting run cost",
        extra={"run_id": run_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    db_manager = _get_tenant_db_manager()
    store = _get_artifact_store()

    try:
        async with db_manager.get_session(tenant_id) as session:
            # Verify run belongs to tenant
            run_query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            run_result = await session.execute(run_query)
            run = run_result.scalar_one_or_none()

            if not run:
                raise HTTPException(status_code=404, detail="Run not found")

            # Get all artifacts for this run
            artifact_query = select(ArtifactModel).where(ArtifactModel.run_id == run_id)
            artifact_result = await session.execute(artifact_query)
            artifacts = artifact_result.scalars().all()

            # Calculate costs from artifact content
            breakdown: list[CostBreakdown] = []
            total_input_tokens = 0
            total_output_tokens = 0
            total_cost = 0.0

            for artifact in artifacts:
                content_type = artifact.content_type or artifact.artifact_type
                if content_type not in ["application/json", "json"]:
                    continue

                # Try to read artifact content for token usage
                try:
                    storage_ref = StorageArtifactRef(
                        path=artifact.ref_path,
                        digest=artifact.digest or "",
                        content_type=content_type,
                        size_bytes=artifact.size_bytes or 0,
                        created_at=artifact.created_at,
                    )
                    content_bytes = await store.get_with_tenant_check(
                        tenant_id=tenant_id,
                        ref=storage_ref,
                        verify=False,
                    )
                    content = json.loads(content_bytes.decode("utf-8"))

                    # Extract usage if present
                    usage = content.get("usage", {})
                    model = content.get("model", "unknown")

                    if usage:
                        input_tokens = usage.get("input_tokens", 0)
                        output_tokens = usage.get("output_tokens", 0)

                        # Calculate cost
                        rates = DEFAULT_COST_RATES.get(model, {"input": 0.001, "output": 0.002})
                        step_cost = (input_tokens / 1000) * rates["input"] + (output_tokens / 1000) * rates["output"]

                        # Get step name from step_id if available
                        step_name = artifact.artifact_type
                        if artifact.step_id:
                            step_query = select(Step).where(Step.id == artifact.step_id)
                            step_result = await session.execute(step_query)
                            step_record = step_result.scalar_one_or_none()
                            if step_record:
                                step_name = step_record.step_name

                        breakdown.append(
                            CostBreakdown(
                                step=step_name,
                                model=model,
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                cost=round(step_cost, 6),
                            )
                        )

                        total_input_tokens += input_tokens
                        total_output_tokens += output_tokens
                        total_cost += step_cost

                except Exception:
                    # Skip artifacts that can't be parsed
                    continue

            return CostResponse(
                run_id=run_id,
                total_cost=round(total_cost, 6),
                total_input_tokens=total_input_tokens,
                total_output_tokens=total_output_tokens,
                breakdown=breakdown,
            )

    except HTTPException:
        raise
    except TenantIdValidationError as e:
        logger.error(f"Invalid tenant_id: {e}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID") from e
    except Exception as e:
        logger.error(f"Failed to get run cost: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get run cost") from e
