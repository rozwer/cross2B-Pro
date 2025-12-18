"""Base Activity class with idempotency and observability.

All workflow activities inherit from BaseActivity to ensure:
- Idempotency: If artifact exists with same input hash, skip re-execution
- Observability: All state changes emit events
- Error handling: Consistent error classification and logging
- Storage: All outputs stored via ArtifactStore (path/digest only returned)
"""

import hashlib
import json
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, TypeVar

import httpx
from temporalio import activity

# API base URL for internal communication (Worker -> API)
API_BASE_URL = os.environ.get("API_BASE_URL", "http://api:8000")

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory, StepError
from apps.api.core.state import GraphState
from apps.api.observability.events import Event, EventEmitter, EventType
from apps.api.storage.artifact_store import ArtifactStore
from apps.api.storage.schemas import ArtifactRef
from apps.api.validation.schemas import ValidationReport

T = TypeVar("T")


async def load_step_data(
    store: ArtifactStore,
    tenant_id: str,
    run_id: str,
    step: str,
) -> dict[str, Any] | None:
    """Load step output data from storage.

    Helper function for activities that need to load previous step data.

    Args:
        store: ArtifactStore instance
        tenant_id: Tenant identifier
        run_id: Run identifier
        step: Step identifier (e.g., 'step0', 'step3a')

    Returns:
        dict with step output data, or None if not found
    """
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"[load_step_data] Loading {step} for tenant={tenant_id}, run={run_id}")

    try:
        data = await store.get_by_path(tenant_id, run_id, step)
        if data:
            logger.info(f"[load_step_data] Found {step} data: {len(data)} bytes")
            return json.loads(data.decode("utf-8"))
        logger.warning(f"[load_step_data] No data found for {step}")
        return None
    except Exception as e:
        logger.error(f"[load_step_data] Failed to load {step}: {type(e).__name__}: {e}")
        return None


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
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[BaseActivity.run] START: step={self.step_id}, tenant={tenant_id}, run={run_id}")

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

        # Update step status in DB via API
        await self._update_step_status(
            run_id=run_id,
            step_name=self.step_id,
            status="running",
            retry_count=attempt,
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

            logger.info(f"[BaseActivity.run] Calling execute() for {self.step_id}")
            # Execute the step
            result = await self.execute(ctx, state)
            logger.info(f"[BaseActivity.run] execute() completed for {self.step_id}")

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

            # Update step status in DB via API
            await self._update_step_status(
                run_id=run_id,
                step_name=self.step_id,
                status="completed",
            )

            # Return ONLY artifact_ref to avoid gRPC message size limits
            # Downstream steps should load data from storage if needed
            return {
                "artifact_ref": artifact_ref.model_dump(),
                "duration_ms": duration_ms,
                "skipped": False,
                "step": self.step_id,
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
            # Update step status in DB via API
            await self._update_step_status(
                run_id=run_id,
                step_name=self.step_id,
                status="failed",
                error_message=str(e),
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
            # Update step status in DB via API
            await self._update_step_status(
                run_id=run_id,
                step_name=self.step_id,
                status="failed",
                error_message=str(e),
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

    async def _update_step_status(
        self,
        run_id: str,
        step_name: str,
        status: str,
        error_message: str | None = None,
        retry_count: int = 0,
    ) -> None:
        """Update step status via internal API.

        Sends HTTP request to API to record step progress in DB.
        Failures are logged but not raised to avoid blocking workflow.
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{API_BASE_URL}/api/internal/steps/update",
                    json={
                        "run_id": run_id,
                        "step_name": step_name,
                        "status": status,
                        "error_message": error_message,
                        "retry_count": retry_count,
                    },
                )
                if response.status_code != 200:
                    logger.warning(
                        f"Failed to update step status: {response.status_code} {response.text}"
                    )
                else:
                    logger.info(f"Step status updated: {step_name} -> {status}")
        except Exception as e:
            # Log but don't raise - step status update is not critical
            logger.warning(f"Failed to update step status via API: {e}")

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
