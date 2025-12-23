"""Diagnostics API endpoints.

Provides endpoints for:
- Error log retrieval
- LLM-based failure diagnosis
- Diagnostic report management
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.db.models import DiagnosticReport
from apps.api.db.tenant import get_tenant_manager
from apps.api.observability.diagnostics import DiagnosticsService
from apps.api.observability.error_collector import ErrorCollector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/runs", tags=["diagnostics"])


# =============================================================================
# Response Models
# =============================================================================


class ErrorLogResponse(BaseModel):
    """Error log entry response."""

    id: str
    step_id: str | None
    source: str  # llm, tool, validation, storage, activity, api
    error_category: str
    error_type: str
    error_message: str
    context: dict[str, Any] | None = None
    attempt: int
    created_at: str


class DiagnosticReportResponse(BaseModel):
    """Diagnostic report response."""

    id: str
    run_id: str
    root_cause_analysis: str
    recommended_actions: list[dict[str, Any]]
    resume_step: str | None = None
    confidence_score: float | None = None
    llm_provider: str
    llm_model: str
    created_at: str


class DiagnosticsRequest(BaseModel):
    """Request to generate diagnostics."""

    llm_provider: str | None = None  # anthropic, openai, gemini


# =============================================================================
# Auth Dependency
# =============================================================================


class AuthUser(BaseModel):
    """Authenticated user info."""

    user_id: str
    tenant_id: str


async def get_current_user() -> AuthUser:
    """Get current authenticated user.

    TODO(SECURITY): Replace this placeholder before production deployment.
    This must be replaced with the actual authentication dependency that:
    1. Validates JWT/session tokens
    2. Extracts tenant_id from verified claims (not user input)
    3. Returns authenticated user info

    See main.py for the actual auth implementation pattern.
    """
    # DEVELOPMENT ONLY - returns hardcoded dev tenant
    return AuthUser(user_id="dev-user", tenant_id="dev-tenant-001")


# =============================================================================
# Security Helpers
# =============================================================================


async def verify_run_ownership(
    session: AsyncSession,
    run_id: str,
    tenant_id: str,
) -> None:
    """Verify that the run_id exists within the tenant's database.

    This prevents cross-tenant access by ensuring the run exists in the
    authenticated tenant's database before any operations.

    Args:
        session: Database session for the tenant
        run_id: Run identifier to verify
        tenant_id: Authenticated tenant identifier (for logging)

    Raises:
        HTTPException: 404 if run not found in tenant's database
    """
    collector = ErrorCollector(session)
    if not await collector.verify_run_exists(run_id):
        logger.warning(
            "Run not found in tenant database",
            extra={"run_id": run_id, "tenant_id": tenant_id},
        )
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/{run_id}/errors", response_model=list[ErrorLogResponse])
async def list_error_logs(
    run_id: str,
    step: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    user: AuthUser = Depends(get_current_user),
) -> list[ErrorLogResponse]:
    """List error logs for a run."""
    tenant_id = user.tenant_id
    logger.debug(
        "Listing error logs",
        extra={"run_id": run_id, "tenant_id": tenant_id, "step": step, "user_id": user.user_id},
    )

    try:
        manager = get_tenant_manager()
        async with manager.get_session(tenant_id) as session:
            # Security: Verify run belongs to authenticated tenant
            await verify_run_ownership(session, run_id, tenant_id)

            collector = ErrorCollector(session)
            errors = await collector.get_errors_for_run(run_id, step_id=step, limit=limit)

            return [
                ErrorLogResponse(
                    id=str(e.id),
                    step_id=str(e.step_id) if e.step_id else None,
                    source=e.source,
                    error_category=e.error_category,
                    error_type=e.error_type,
                    error_message=e.error_message,
                    context=e.context,
                    attempt=e.attempt,
                    created_at=e.created_at.isoformat(),
                )
                for e in errors
            ]
    except HTTPException:
        raise  # Re-raise 404 from verify_run_ownership
    except Exception as e:
        logger.error(f"Failed to list error logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve error logs")


@router.get("/{run_id}/errors/summary")
async def get_error_summary(
    run_id: str,
    user: AuthUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Get error summary for a run."""
    tenant_id = user.tenant_id
    logger.debug(
        "Getting error summary",
        extra={"run_id": run_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    try:
        manager = get_tenant_manager()
        async with manager.get_session(tenant_id) as session:
            # Security: Verify run belongs to authenticated tenant
            await verify_run_ownership(session, run_id, tenant_id)

            collector = ErrorCollector(session)
            return await collector.get_error_summary(run_id)
    except HTTPException:
        raise  # Re-raise 404 from verify_run_ownership
    except Exception as e:
        logger.error(f"Failed to get error summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve error summary")


@router.post("/{run_id}/diagnose", response_model=DiagnosticReportResponse)
async def diagnose_run(
    run_id: str,
    request: DiagnosticsRequest | None = None,
    user: AuthUser = Depends(get_current_user),
) -> DiagnosticReportResponse:
    """Generate LLM-based diagnostic analysis for a failed run.

    Analyzes collected error logs and provides:
    - Root cause analysis
    - Recommended recovery actions
    - Suggested step to resume from
    """
    tenant_id = user.tenant_id
    llm_provider = request.llm_provider if request else None

    logger.info(
        "Generating diagnostics",
        extra={
            "run_id": run_id,
            "tenant_id": tenant_id,
            "llm_provider": llm_provider,
            "user_id": user.user_id,
        },
    )

    try:
        manager = get_tenant_manager()
        async with manager.get_session(tenant_id) as session:
            # Security: Verify run belongs to authenticated tenant
            await verify_run_ownership(session, run_id, tenant_id)

            diagnostics = DiagnosticsService(session, llm_provider=llm_provider)
            report = await diagnostics.analyze_failure(run_id, tenant_id)

            return DiagnosticReportResponse(
                id=str(report.id),
                run_id=run_id,
                root_cause_analysis=report.root_cause_analysis,
                recommended_actions=report.recommended_actions,
                resume_step=report.resume_step,
                confidence_score=float(report.confidence_score) if report.confidence_score else None,
                llm_provider=report.llm_provider,
                llm_model=report.llm_model,
                created_at=report.created_at.isoformat(),
            )
    except HTTPException:
        raise  # Re-raise 404 from verify_run_ownership
    except Exception as e:
        logger.error(f"Failed to generate diagnostics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate diagnostics: {str(e)}")


@router.get("/{run_id}/diagnostics", response_model=list[DiagnosticReportResponse])
async def list_diagnostics(
    run_id: str,
    limit: int = Query(default=10, ge=1, le=50),
    user: AuthUser = Depends(get_current_user),
) -> list[DiagnosticReportResponse]:
    """List all diagnostic reports for a run."""
    tenant_id = user.tenant_id
    logger.debug(
        "Listing diagnostics",
        extra={"run_id": run_id, "tenant_id": tenant_id, "user_id": user.user_id},
    )

    try:
        manager = get_tenant_manager()
        async with manager.get_session(tenant_id) as session:
            # Security: Verify run belongs to authenticated tenant
            await verify_run_ownership(session, run_id, tenant_id)

            stmt = (
                select(DiagnosticReport).where(DiagnosticReport.run_id == run_id).order_by(DiagnosticReport.created_at.desc()).limit(limit)
            )
            result = await session.execute(stmt)
            reports = result.scalars().all()

            return [
                DiagnosticReportResponse(
                    id=str(r.id),
                    run_id=run_id,
                    root_cause_analysis=r.root_cause_analysis,
                    recommended_actions=r.recommended_actions,
                    resume_step=r.resume_step,
                    confidence_score=float(r.confidence_score) if r.confidence_score else None,
                    llm_provider=r.llm_provider,
                    llm_model=r.llm_model,
                    created_at=r.created_at.isoformat(),
                )
                for r in reports
            ]
    except HTTPException:
        raise  # Re-raise 404 from verify_run_ownership
    except Exception as e:
        logger.error(f"Failed to list diagnostics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve diagnostics")
