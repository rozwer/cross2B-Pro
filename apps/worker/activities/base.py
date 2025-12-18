"""Base Activity class with idempotency and observability.

All workflow activities inherit from BaseActivity to ensure:
- Idempotency: If artifact exists with same input hash, skip re-execution
- Observability: All state changes emit events
- Error handling: Consistent error classification and logging
- Error collection: All errors logged for LLM-based diagnostics
- Storage: All outputs stored via ArtifactStore (path/digest only returned)
"""

import hashlib
import json
import time
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, TypeVar

from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory, StepError
from apps.api.core.state import GraphState
from apps.api.observability.events import Event, EventEmitter, EventType
from apps.api.storage.artifact_store import ArtifactStore
from apps.api.storage.schemas import ArtifactRef
from apps.api.validation.schemas import ValidationReport

T = TypeVar("T")


class ActivityError(Exception):
    """Base exception for activity errors."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.RETRYABLE,
        details: dict[str, Any] | None = None,
    ):
        self.category = category
        self.details = details or {}
        super().__init__(message)


class ValidationError(ActivityError):
    """Output validation failed."""

    def __init__(self, report: ValidationReport, message: str = ""):
        self.report = report
        super().__init__(
            message or f"Validation failed: {report.error_count()} errors",
            category=ErrorCategory.VALIDATION_FAIL,
            details={"issues": [i.model_dump() for i in report.issues]},
        )


class BaseActivity(ABC):
    """Base class for all workflow activities.

    Provides:
    - Idempotent execution via input hashing
    - Artifact storage with integrity verification
    - Event emission for observability
    - Consistent error handling

    Subclasses must implement:
    - step_id: Unique step identifier
    - execute(): Core execution logic
    """

    def __init__(
        self,
        store: ArtifactStore | None = None,
        emitter: EventEmitter | None = None,
    ):
        """Initialize activity with dependencies.

        Args:
            store: Artifact storage (default: new ArtifactStore)
            emitter: Event emitter (default: new EventEmitter)
        """
        self.store = store or ArtifactStore()
        self.emitter = emitter or EventEmitter()

    @property
    @abstractmethod
    def step_id(self) -> str:
        """Unique identifier for this step (e.g., 'step0', 'step3a')."""
        ...

    @abstractmethod
    async def execute(
        self,
        ctx: ExecutionContext,
        state: GraphState,
    ) -> dict[str, Any]:
        """Execute the step logic.

        Args:
            ctx: Execution context with run info
            state: Current workflow state

        Returns:
            dict with step output data

        Raises:
            ActivityError: On execution failure
        """
        ...

    async def run(
        self,
        tenant_id: str,
        run_id: str,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Entry point for activity execution with idempotency.

        This method:
        1. Computes input hash for idempotency
        2. Checks if output already exists
        3. If not, executes the step
        4. Stores output and emits events

        Args:
            tenant_id: Tenant identifier
            run_id: Run identifier
            config: Step configuration

        Returns:
            dict with artifact_ref and metadata
        """
        start_time = time.time()

        # Get attempt number from Temporal
        attempt = activity.info().attempt

        # Build execution context
        ctx = ExecutionContext(
            run_id=run_id,
            step_id=self.step_id,
            attempt=attempt,
            tenant_id=tenant_id,
            started_at=datetime.now(),
            timeout_seconds=config.get("timeout", 120),
            config=config,
        )

        # Compute input digest for idempotency
        input_digest = self._compute_input_digest(tenant_id, run_id, config)

        # Check for existing output (idempotency)
        output_path = self.store.build_path(
            tenant_id=tenant_id,
            run_id=run_id,
            step=self.step_id,
        )

        existing_ref = await self._check_existing_output(output_path, input_digest)
        if existing_ref:
            activity.logger.info(
                f"Step {self.step_id}: Using existing output (idempotent skip)"
            )
            return {
                "artifact_ref": existing_ref.model_dump(),
                "skipped": True,
                "reason": "existing_output",
            }

        # Emit step started event
        await self._emit_event(
            EventType.STEP_STARTED,
            ctx,
            {"attempt": attempt, "input_digest": input_digest},
        )

        try:
            # Build minimal state for execution
            state = GraphState(
                run_id=run_id,
                tenant_id=tenant_id,
                current_step=self.step_id,
                status="running",
                step_outputs={},
                validation_reports=[],
                errors=[],
                config=config,
                metadata={},
            )

            # Execute the step
            result = await self.execute(ctx, state)

            # Store output
            artifact_ref = await self._store_output(
                ctx=ctx,
                output=result,
                input_digest=input_digest,
            )

            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Emit success event
            await self._emit_event(
                EventType.STEP_SUCCEEDED,
                ctx,
                {
                    "duration_ms": duration_ms,
                    "artifact_path": artifact_ref.path,
                    "artifact_digest": artifact_ref.digest,
                },
            )

            return {
                "artifact_ref": artifact_ref.model_dump(),
                "duration_ms": duration_ms,
                "skipped": False,
            }

        except ActivityError as e:
            # Emit failure event
            await self._emit_event(
                EventType.STEP_FAILED,
                ctx,
                {
                    "error": str(e),
                    "category": e.category.value,
                    "details": e.details,
                },
            )

            # Collect error for diagnostics
            await self._collect_error(
                ctx=ctx,
                error=e,
                category=e.category,
                context=e.details,
            )
            raise

        except Exception as e:
            # Wrap unexpected errors
            await self._emit_event(
                EventType.STEP_FAILED,
                ctx,
                {
                    "error": str(e),
                    "category": ErrorCategory.RETRYABLE.value,
                    "unexpected": True,
                },
            )

            # Collect error for diagnostics
            await self._collect_error(
                ctx=ctx,
                error=e,
                category=ErrorCategory.RETRYABLE,
                context={"unexpected": True},
            )

            raise ActivityError(
                message=f"Unexpected error in {self.step_id}: {e}",
                category=ErrorCategory.RETRYABLE,
                details={"original_error": str(e)},
            ) from e

    def _compute_input_digest(
        self,
        tenant_id: str,
        run_id: str,
        config: dict[str, Any],
    ) -> str:
        """Compute SHA256 hash of inputs for idempotency check."""
        # Normalize config for consistent hashing
        input_data = {
            "tenant_id": tenant_id,
            "run_id": run_id,
            "step_id": self.step_id,
            "config": config,
        }
        input_json = json.dumps(input_data, sort_keys=True)
        return hashlib.sha256(input_json.encode()).hexdigest()

    async def _check_existing_output(
        self,
        path: str,
        input_digest: str,
    ) -> ArtifactRef | None:
        """Check if valid output already exists.

        Args:
            path: Expected output path
            input_digest: Input hash for verification

        Returns:
            ArtifactRef if valid output exists, None otherwise
        """
        try:
            # Check if artifact exists by trying to get metadata
            # The metadata file stores the input_digest for verification
            # meta_path = path.replace("/output.json", "/metadata.json")
            # TODO: Use meta_path for proper caching with input_digest verification

            # For now, simple existence check
            # In production, verify input_digest matches
            # This is a simplified version - full implementation would
            # store and verify input_digest in metadata
            _ = path  # Mark as used, actual caching to be implemented
            return None  # Always re-run for now; enable caching later

        except Exception:
            return None

    async def _store_output(
        self,
        ctx: ExecutionContext,
        output: dict[str, Any],
        input_digest: str,
    ) -> ArtifactRef:
        """Store output and return reference.

        Args:
            ctx: Execution context
            output: Output data to store
            input_digest: Input hash for metadata

        Returns:
            ArtifactRef to stored content
        """
        # Serialize output
        content = json.dumps(output, ensure_ascii=False, indent=2)
        content_bytes = content.encode("utf-8")

        # Build path
        path = self.store.build_path(
            tenant_id=ctx.tenant_id,
            run_id=ctx.run_id,
            step=self.step_id,
        )

        # Store artifact
        artifact_ref = await self.store.put(
            content=content_bytes,
            path=path,
            content_type="application/json",
        )

        # Store metadata (for idempotency verification)
        meta_content = json.dumps({
            "input_digest": input_digest,
            "step_id": self.step_id,
            "created_at": datetime.now().isoformat(),
            "attempt": ctx.attempt,
        })
        meta_path = path.replace("/output.json", "/metadata.json")
        await self.store.put(
            content=meta_content.encode("utf-8"),
            path=meta_path,
            content_type="application/json",
        )

        return artifact_ref

    async def _emit_event(
        self,
        event_type: EventType,
        ctx: ExecutionContext,
        payload: dict[str, Any],
    ) -> None:
        """Emit an event for observability."""
        event = Event(
            event_type=event_type,
            run_id=ctx.run_id,
            step_id=ctx.step_id,
            tenant_id=ctx.tenant_id,
            payload=payload,
        )
        await self.emitter.emit(event)

    def create_step_error(
        self,
        message: str,
        category: ErrorCategory,
        details: dict[str, Any] | None = None,
    ) -> StepError:
        """Create a StepError for recording in state."""
        return StepError(
            step_id=self.step_id,
            category=category,
            message=message,
            details=details,
            occurred_at=datetime.now(),
            attempt=activity.info().attempt,
        )

    async def _collect_error(
        self,
        ctx: ExecutionContext,
        error: Exception,
        category: ErrorCategory,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Collect error for LLM-based diagnostics.

        Stores error details in the error_logs table for later analysis
        by the diagnostics service.

        Args:
            ctx: Execution context
            error: The exception that occurred
            category: Error classification
            context: Additional context (LLM model, tool, params, etc.)
        """
        try:
            from sqlalchemy import text

            from apps.api.db.tenant import get_tenant_engine

            # Get tenant database engine
            engine = await get_tenant_engine(ctx.tenant_id)

            # Build error context
            error_context = context or {}
            error_context.update({
                "step_id": ctx.step_id,
                "timeout_seconds": ctx.timeout_seconds,
                "config_keys": list(ctx.config.keys()) if ctx.config else [],
            })

            # Get stack trace
            stack_trace = "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )

            async with engine.connect() as conn:
                await conn.execute(
                    text(
                        """
                        INSERT INTO error_logs
                        (run_id, step_id, error_category, error_type,
                         error_message, stack_trace, context, attempt)
                        VALUES
                        (:run_id, :step_id, :error_category, :error_type,
                         :error_message, :stack_trace, :context, :attempt)
                        """
                    ),
                    {
                        "run_id": ctx.run_id,
                        "step_id": ctx.step_id,
                        "error_category": category.value,
                        "error_type": type(error).__name__,
                        "error_message": str(error),
                        "stack_trace": stack_trace,
                        "context": error_context,
                        "attempt": ctx.attempt,
                    },
                )
                await conn.commit()

            activity.logger.debug(
                f"Error logged for diagnostics: {type(error).__name__} in {ctx.step_id}"
            )

        except Exception as log_error:
            # Don't fail the activity if error logging fails
            activity.logger.warning(
                f"Failed to log error for diagnostics: {log_error}"
            )
