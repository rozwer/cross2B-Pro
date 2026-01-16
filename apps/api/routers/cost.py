"""Cost tracking router.

Handles cost breakdown and token usage for runs.

Architecture:
- Reads token usage directly from storage (MinIO) artifacts
- Each step's output.json contains token_usage field
- Supports input, output, and thinking (reasoning) tokens
- Cost rates are per 1K tokens, stored in DEFAULT_COST_RATES
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from apps.api.auth import get_current_user
from apps.api.auth.schemas import AuthUser
from apps.api.db import Run, TenantIdValidationError

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
    thinking_tokens: int = 0  # Reasoning/thinking tokens (Gemini 2.5, o1, etc.)
    cost: float


class CostResponse(BaseModel):
    """Cost response for a run."""

    run_id: str
    total_cost: float
    total_input_tokens: int
    total_output_tokens: int
    total_thinking_tokens: int = 0  # Total reasoning/thinking tokens
    breakdown: list[CostBreakdown]
    currency: str = "USD"


# Default cost rates (per 1K tokens)
# Rates from official pricing pages as of 2025-01
# thinking: rate for reasoning/thinking tokens (different pricing tier)
DEFAULT_COST_RATES: dict[str, dict[str, float]] = {
    # Gemini models
    "gemini-1.5-pro": {"input": 0.00125, "output": 0.005, "thinking": 0.00125},
    "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003, "thinking": 0.000075},
    "gemini-2.0-flash": {"input": 0.0001, "output": 0.0004, "thinking": 0.0001},
    "gemini-2.0-flash-exp": {"input": 0.0001, "output": 0.0004, "thinking": 0.0001},
    "gemini-2.0-flash-lite": {"input": 0.000075, "output": 0.0003, "thinking": 0.000075},
    "gemini-2.5-pro": {"input": 0.00125, "output": 0.01, "thinking": 0.00125},
    "gemini-2.5-flash": {"input": 0.00015, "output": 0.0006, "thinking": 0.00015},
    "gemini-2.5-flash-preview-05-20": {"input": 0.00015, "output": 0.0035, "thinking": 0.00015},
    # OpenAI models
    "gpt-4o": {"input": 0.0025, "output": 0.01, "thinking": 0.0025},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006, "thinking": 0.00015},
    "gpt-4.1": {"input": 0.002, "output": 0.008, "thinking": 0.002},
    "gpt-4.1-mini": {"input": 0.0004, "output": 0.0016, "thinking": 0.0004},
    "gpt-4.1-nano": {"input": 0.0001, "output": 0.0004, "thinking": 0.0001},
    "o1": {"input": 0.015, "output": 0.06, "thinking": 0.015},
    "o1-mini": {"input": 0.003, "output": 0.012, "thinking": 0.003},
    "o1-pro": {"input": 0.15, "output": 0.6, "thinking": 0.15},
    "o3-mini": {"input": 0.0011, "output": 0.0044, "thinking": 0.0011},
    # Anthropic models
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015, "thinking": 0.003},
    "claude-3-5-haiku-20241022": {"input": 0.0008, "output": 0.004, "thinking": 0.0008},
    "claude-3-7-sonnet": {"input": 0.003, "output": 0.015, "thinking": 0.003},
    "claude-sonnet-4": {"input": 0.003, "output": 0.015, "thinking": 0.003},
    "claude-opus-4": {"input": 0.015, "output": 0.075, "thinking": 0.015},
}


# =============================================================================
# Helper Functions
# =============================================================================


def _extract_step_name(path: str) -> str:
    """Extract step name from storage path.

    Path format: storage/{tenant_id}/{run_id}/{step}/output.json
    """
    parts = path.split("/")
    if len(parts) >= 4:
        return parts[3]  # step is the 4th component
    return "unknown"


def _calculate_step_cost(
    usage: dict[str, Any],
    model: str,
) -> tuple[int, int, int, float]:
    """Calculate cost for a step based on token usage.

    Args:
        usage: Token usage dict with input/output/thinking keys
        model: Model name for rate lookup

    Returns:
        Tuple of (input_tokens, output_tokens, thinking_tokens, cost)
    """
    input_tokens = usage.get("input", usage.get("input_tokens", 0))
    output_tokens = usage.get("output", usage.get("output_tokens", 0))
    thinking_tokens = usage.get("thinking", usage.get("thinking_tokens", 0))

    # Get rates for this model (with fallback for unknown models)
    rates = DEFAULT_COST_RATES.get(model, {"input": 0.001, "output": 0.002, "thinking": 0.001})

    cost = (
        (input_tokens / 1000) * rates.get("input", 0.001)
        + (output_tokens / 1000) * rates.get("output", 0.002)
        + (thinking_tokens / 1000) * rates.get("thinking", 0.001)
    )

    return input_tokens, output_tokens, thinking_tokens, cost


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/api/runs/{run_id}/cost", response_model=CostResponse)
async def get_run_cost(
    run_id: str,
    user: AuthUser = Depends(get_current_user),
) -> CostResponse:
    """Get cost breakdown for a run.

    Reads token usage directly from storage artifacts (MinIO).
    Each step's output.json contains model and token_usage fields.

    Supports:
    - input_tokens: Prompt/input tokens
    - output_tokens: Completion/output tokens
    - thinking_tokens: Reasoning tokens (Gemini 2.5 thinking, o1, etc.)
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

        # List all artifacts in storage for this run
        artifact_paths = store.list_run_artifacts(tenant_id, run_id)

        # Filter to only output.json files
        output_files = [p for p in artifact_paths if p.endswith("/output.json")]

        # Calculate costs from artifact content
        breakdown: list[CostBreakdown] = []
        total_input_tokens = 0
        total_output_tokens = 0
        total_thinking_tokens = 0
        total_cost = 0.0

        for path in output_files:
            step_name = _extract_step_name(path)

            try:
                # Read artifact content directly from storage
                content_bytes = await store.get_by_path(tenant_id, run_id, step_name)
                if not content_bytes:
                    continue

                content = json.loads(content_bytes.decode("utf-8"))

                # Extract usage if present
                usage = content.get("token_usage") or content.get("usage")
                if not usage:
                    logger.debug(f"No token_usage in {step_name}")
                    continue

                model = content.get("model", "unknown")

                # Calculate cost
                input_tok, output_tok, thinking_tok, step_cost = _calculate_step_cost(usage, model)

                breakdown.append(
                    CostBreakdown(
                        step=step_name,
                        model=model,
                        input_tokens=input_tok,
                        output_tokens=output_tok,
                        thinking_tokens=thinking_tok,
                        cost=round(step_cost, 6),
                    )
                )

                total_input_tokens += input_tok
                total_output_tokens += output_tok
                total_thinking_tokens += thinking_tok
                total_cost += step_cost

            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON in {path}: {e}")
                continue
            except Exception as e:
                logger.debug(f"Error reading {path}: {e}")
                continue

        # Sort breakdown by step name for consistent ordering
        breakdown.sort(key=lambda x: x.step)

        return CostResponse(
            run_id=run_id,
            total_cost=round(total_cost, 6),
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_thinking_tokens=total_thinking_tokens,
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
