"""LLM-based failure diagnostics service.

Analyzes error logs to determine root cause and recommend recovery steps.
"""

import logging
import time
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.core.errors import ErrorCategory
from apps.api.db.models import DiagnosticReport
from apps.api.llm.base import LLMInterface, get_llm_client
from apps.api.llm.schemas import LLMCallMetadata, LLMRequestConfig

from .error_collector import ErrorCollector

logger = logging.getLogger(__name__)


# =============================================================================
# Diagnostic Response Schema
# =============================================================================


class RecommendedAction(BaseModel):
    """A single recommended action for recovery."""

    priority: int = Field(..., ge=1, le=10, description="Priority (1=highest)")
    action: str = Field(..., description="Action to take")
    rationale: str = Field(..., description="Why this action is recommended")
    step_to_resume: str | None = Field(
        default=None, description="Workflow step to resume from"
    )


class DiagnosticResult(BaseModel):
    """LLM diagnostic analysis result."""

    root_cause: str = Field(..., description="Root cause analysis")
    recommended_actions: list[RecommendedAction] = Field(
        ..., description="Ordered list of recommended recovery actions"
    )
    resume_step: str | None = Field(
        default=None, description="Suggested step to resume workflow from"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence score (0.0-1.0)"
    )
    summary: str = Field(..., description="Brief summary for operators")


# =============================================================================
# Diagnostic Service
# =============================================================================


DIAGNOSTIC_SYSTEM_PROMPT = """You are an expert systems diagnostician analyzing workflow execution failures.

Your task is to:
1. Analyze the error logs and execution history
2. Identify the root cause of the failure
3. Recommend specific recovery actions
4. Suggest which workflow step to resume from (if applicable)

## Workflow Steps (in order):
- step0: Initial setup and validation
- step1: Data collection and preparation
- step2: Content analysis
- step3a/step3b/step3c: Parallel processing stages
- step4: Aggregation
- step5: Draft generation
- step6: Review preparation
- step6_5: Additional processing
- step7a/step7b: Finalization stages
- step8: Quality check
- step9: Final formatting
- step10: Output generation

## Error Categories:
- retryable: Temporary failures (network, rate limits, timeouts) - can retry
- non_retryable: Permanent failures (auth, invalid config) - need fix before retry
- validation_fail: Output format issues - may need different approach

## Guidelines:
- Be specific about the root cause
- Order actions by priority (1 = most important)
- Only suggest resume_step if the workflow can safely resume from there
- Consider if earlier steps need to be re-executed due to state corruption
- Confidence should reflect how certain you are about the diagnosis
"""


DIAGNOSTIC_USER_PROMPT_TEMPLATE = """Analyze this workflow failure and provide diagnosis:

## Run Information
- Run ID: {run_id}
- Status: {run_status}
- Current Step: {current_step}
- Final Error: {final_error}

## Error Summary
- Total Errors: {total_errors}
- By Category: {by_category}
- By Step: {by_step}
- By Type: {by_type}

## Error Timeline
{error_timeline}

## Step Execution History
{step_history}

## Run Configuration
{config}

Provide a structured diagnosis with root cause, recommended actions, and recovery steps.
"""


class DiagnosticsService:
    """LLM-based failure diagnostics.

    Analyzes error logs to provide:
    - Root cause analysis
    - Recommended recovery actions
    - Resume step suggestions

    Usage:
        diagnostics = DiagnosticsService(session, llm_provider="anthropic")

        # Analyze a failed run
        report = await diagnostics.analyze_failure("run-123")

        # Get latest diagnosis for a run
        report = await diagnostics.get_latest_diagnosis("run-123")
    """

    DEFAULT_PROVIDER = "anthropic"
    DEFAULT_MODEL = "claude-sonnet-4-20250514"

    def __init__(
        self,
        session: AsyncSession,
        llm_provider: str | None = None,
        llm_model: str | None = None,
        llm_client: LLMInterface | None = None,
    ) -> None:
        """Initialize diagnostics service.

        Args:
            session: Async database session
            llm_provider: LLM provider name (anthropic, openai, gemini)
            llm_model: Specific model to use (optional)
            llm_client: Pre-configured LLM client (optional)
        """
        self._session = session
        self._error_collector = ErrorCollector(session)
        self._provider = llm_provider or self.DEFAULT_PROVIDER
        self._model = llm_model

        if llm_client:
            self._llm = llm_client
        else:
            self._llm = get_llm_client(self._provider)

    async def analyze_failure(
        self,
        run_id: str,
        tenant_id: str | None = None,
    ) -> DiagnosticReport:
        """Analyze a failed run and generate diagnostic report.

        Args:
            run_id: Run identifier to analyze
            tenant_id: Tenant identifier (for metadata)

        Returns:
            DiagnosticReport saved to database
        """
        start_time = time.time()

        # Build diagnostic context
        context = await self._error_collector.build_diagnostic_context(run_id)

        if context["error_summary"]["total_errors"] == 0:
            logger.warning(f"No errors found for run {run_id}, creating minimal diagnosis")
            return await self._create_minimal_diagnosis(run_id, context)

        # Format the prompt
        user_prompt = self._format_user_prompt(context)

        # Call LLM for analysis
        metadata = LLMCallMetadata(
            run_id=run_id,
            step_id="diagnostics",
            tenant_id=tenant_id,
            attempt=1,
        )

        config = LLMRequestConfig(
            temperature=0.3,  # Lower temperature for more consistent analysis
            max_tokens=4096,
        )

        # Define expected schema
        response_schema = {
            "type": "object",
            "properties": {
                "root_cause": {"type": "string"},
                "recommended_actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "priority": {"type": "integer"},
                            "action": {"type": "string"},
                            "rationale": {"type": "string"},
                            "step_to_resume": {"type": "string", "nullable": True},
                        },
                        "required": ["priority", "action", "rationale"],
                    },
                },
                "resume_step": {"type": "string", "nullable": True},
                "confidence": {"type": "number"},
                "summary": {"type": "string"},
            },
            "required": [
                "root_cause",
                "recommended_actions",
                "confidence",
                "summary",
            ],
        }

        try:
            result_dict = await self._llm.generate_json(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=DIAGNOSTIC_SYSTEM_PROMPT,
                schema=response_schema,
                config=config,
                metadata=metadata,
            )

            # Parse and validate result
            result = DiagnosticResult(**result_dict)

        except Exception as e:
            logger.error(f"LLM diagnosis failed for run {run_id}: {e}")
            # Create fallback diagnosis based on error patterns
            # NOTE: This is NOT a fallback to a different model/provider
            # It's a rule-based fallback when LLM is unavailable
            result = self._create_fallback_diagnosis(context)

        latency_ms = int((time.time() - start_time) * 1000)

        # Save to database
        report = await self._save_report(
            run_id=run_id,
            result=result,
            latency_ms=latency_ms,
        )

        logger.info(
            f"Diagnostic report generated for run {run_id}",
            extra={
                "run_id": run_id,
                "confidence": result.confidence,
                "resume_step": result.resume_step,
                "latency_ms": latency_ms,
            },
        )

        return report

    async def get_latest_diagnosis(self, run_id: str) -> DiagnosticReport | None:
        """Get the most recent diagnostic report for a run.

        Args:
            run_id: Run identifier

        Returns:
            Latest DiagnosticReport or None if not found
        """
        from sqlalchemy import select

        stmt = (
            select(DiagnosticReport)
            .where(DiagnosticReport.run_id == run_id)
            .order_by(DiagnosticReport.created_at.desc())
            .limit(1)
        )

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    def _format_user_prompt(self, context: dict[str, Any]) -> str:
        """Format the user prompt with diagnostic context."""
        summary = context["error_summary"]

        # Format error timeline
        timeline_lines = []
        for entry in summary.get("timeline", []):
            timeline_lines.append(
                f"- [{entry['timestamp']}] {entry['step'] or 'N/A'}: "
                f"{entry['type']} (attempt {entry['attempt']}): {entry['message']}"
            )
        error_timeline = "\n".join(timeline_lines) or "No error timeline available"

        # Format step history
        step_lines = []
        for step in context.get("step_history", []):
            status = step.get("status", "unknown")
            step_name = step.get("step_name", "unknown")
            error_msg = step.get("error_message", "")
            retry_count = step.get("retry_count", 0)
            step_lines.append(
                f"- {step_name}: {status}"
                + (f" (retries: {retry_count})" if retry_count > 0 else "")
                + (f" - {error_msg[:100]}" if error_msg else "")
            )
        step_history = "\n".join(step_lines) or "No step history available"

        return DIAGNOSTIC_USER_PROMPT_TEMPLATE.format(
            run_id=context["run_id"],
            run_status=context["run_status"],
            current_step=context["current_step"] or "N/A",
            final_error=context["final_error"] or "No final error recorded",
            total_errors=summary["total_errors"],
            by_category=summary.get("by_category", {}),
            by_step=summary.get("by_step", {}),
            by_type=summary.get("by_type", {}),
            error_timeline=error_timeline,
            step_history=step_history,
            config=context.get("config", {}),
        )

    def _create_fallback_diagnosis(self, context: dict[str, Any]) -> DiagnosticResult:
        """Create a fallback diagnosis when LLM fails.

        Uses pattern matching on error types to provide basic guidance.
        NOTE: This is NOT switching to a different LLM - it's rule-based.
        """
        summary = context["error_summary"]
        by_category = summary.get("by_category", {})

        # Determine primary error category
        if by_category.get("non_retryable", 0) > 0:
            root_cause = (
                "Non-retryable errors detected. These typically indicate "
                "configuration issues, authentication problems, or invalid inputs."
            )
            actions = [
                RecommendedAction(
                    priority=1,
                    action="Review and fix configuration/credentials",
                    rationale="Non-retryable errors require manual intervention",
                    step_to_resume=None,
                )
            ]
        elif by_category.get("validation_fail", 0) > 0:
            root_cause = (
                "Validation failures detected. The LLM output did not meet "
                "expected format or quality requirements."
            )
            actions = [
                RecommendedAction(
                    priority=1,
                    action="Review prompts and output validation rules",
                    rationale="Validation failures may require prompt adjustments",
                    step_to_resume=context.get("current_step"),
                )
            ]
        else:
            root_cause = (
                "Retryable errors exhausted retry attempts. "
                "This may indicate persistent service issues."
            )
            actions = [
                RecommendedAction(
                    priority=1,
                    action="Wait and retry the workflow",
                    rationale="Temporary issues may resolve with time",
                    step_to_resume=context.get("current_step"),
                )
            ]

        return DiagnosticResult(
            root_cause=root_cause,
            recommended_actions=actions,
            resume_step=context.get("current_step"),
            confidence=0.3,  # Low confidence for fallback
            summary="Automated fallback diagnosis - LLM analysis unavailable",
        )

    async def _create_minimal_diagnosis(
        self, run_id: str, context: dict[str, Any]
    ) -> DiagnosticReport:
        """Create minimal diagnosis when no errors are found."""
        result = DiagnosticResult(
            root_cause="No error logs found. The run may have failed during initialization or the errors were not properly logged.",
            recommended_actions=[
                RecommendedAction(
                    priority=1,
                    action="Check application logs for additional error details",
                    rationale="Error logs may not have been persisted to database",
                    step_to_resume=None,
                )
            ],
            resume_step=None,
            confidence=0.2,
            summary="No error logs available for analysis",
        )

        return await self._save_report(
            run_id=run_id,
            result=result,
            latency_ms=0,
        )

    async def _save_report(
        self,
        run_id: str,
        result: DiagnosticResult,
        latency_ms: int,
    ) -> DiagnosticReport:
        """Save diagnostic result to database."""
        report = DiagnosticReport(
            run_id=run_id,
            root_cause_analysis=result.root_cause,
            recommended_actions=[
                {
                    "priority": a.priority,
                    "action": a.action,
                    "rationale": a.rationale,
                    "step_to_resume": a.step_to_resume,
                }
                for a in result.recommended_actions
            ],
            resume_step=result.resume_step,
            confidence_score=result.confidence,
            llm_provider=self._provider,
            llm_model=self._model or self._llm.default_model,
            latency_ms=latency_ms,
        )

        self._session.add(report)
        await self._session.flush()
        return report


# =============================================================================
# Convenience Functions
# =============================================================================


async def diagnose_run_failure(
    session: AsyncSession,
    run_id: str,
    tenant_id: str | None = None,
    llm_provider: str | None = None,
) -> DiagnosticReport:
    """Convenience function to diagnose a failed run.

    Args:
        session: Database session
        run_id: Run identifier
        tenant_id: Tenant identifier
        llm_provider: LLM provider to use (default: anthropic)

    Returns:
        DiagnosticReport with analysis results
    """
    service = DiagnosticsService(session, llm_provider=llm_provider)
    return await service.analyze_failure(run_id, tenant_id)
