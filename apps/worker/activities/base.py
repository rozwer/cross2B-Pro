"""Base Activity class with idempotency and observability.

All workflow activities inherit from BaseActivity to ensure:
- Idempotency: If artifact exists with same input hash, skip re-execution
- Observability: All state changes emit events
- Error handling: Consistent error classification and logging
- Storage: All outputs stored via ArtifactStore (path/digest only returned)
"""

import asyncio
import hashlib
import json
import os
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, TypeVar

import httpx
from temporalio import activity

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory, StepError
from apps.api.core.state import GraphState
from apps.api.observability.events import Event, EventEmitter, EventType
from apps.api.storage.artifact_store import ArtifactStore
from apps.api.storage.schemas import ArtifactRef
from apps.api.validation.schemas import ValidationReport

# API base URL for internal communication (Worker -> API)
API_BASE_URL = os.environ.get("API_BASE_URL", "http://api:8000")

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
        dict with step output data, or None if not found (artifact doesn't exist)

    Raises:
        Exception: If storage access fails (non-NotFound errors)
    """
    import logging

    from minio.error import S3Error

    logger = logging.getLogger(__name__)

    logger.info(f"[load_step_data] Loading {step} for tenant={tenant_id}, run={run_id}")

    try:
        data = await store.get_by_path(tenant_id, run_id, step)
        if data:
            logger.info(f"[load_step_data] Found {step} data: {len(data)} bytes")
            result: dict[str, Any] = json.loads(data.decode("utf-8"))
            return result
        logger.warning(f"[load_step_data] No data found for {step}")
        return None
    except S3Error as e:
        # NoSuchKey is expected when artifact doesn't exist - return None
        if e.code == "NoSuchKey":
            logger.warning(f"[load_step_data] No data found for {step} (NoSuchKey)")
            return None
        # Other S3 errors (permissions, network, etc.) should be raised
        logger.error(f"[load_step_data] S3 error loading {step}: {e.code}: {e}")
        raise
    except json.JSONDecodeError as e:
        # Corrupted data - should be raised as it indicates a serious problem
        logger.error(f"[load_step_data] Invalid JSON for {step}: {e}")
        raise
    except Exception as e:
        # Unexpected errors should be raised for proper handling upstream
        logger.error(f"[load_step_data] Failed to load {step}: {type(e).__name__}: {e}")
        raise


async def save_step_data(
    store: ArtifactStore,
    tenant_id: str,
    run_id: str,
    step: str,
    data: dict[str, Any],
    filename: str = "output.json",
) -> ArtifactRef:
    """Save step output data to storage.

    Helper function for activities that need to save intermediate or final step data.

    Args:
        store: ArtifactStore instance
        tenant_id: Tenant identifier
        run_id: Run identifier
        step: Step identifier (e.g., 'step11')
        data: Data to save
        filename: Output filename (default: output.json)

    Returns:
        ArtifactRef with path and digest

    Raises:
        Exception: If storage save fails (callers should handle appropriately)
    """
    import logging

    logger = logging.getLogger(__name__)

    logger.info(f"[save_step_data] Saving {step}/{filename} for tenant={tenant_id}, run={run_id}")

    try:
        path = store.build_path(tenant_id, run_id, step, filename)
        content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        ref = await store.put(content, path, "application/json")
        logger.info(f"[save_step_data] Saved {step}/{filename}: {len(content)} bytes")
        return ref
    except Exception as e:
        # Save failures are critical - raise for proper handling upstream
        logger.error(f"[save_step_data] Failed to save {step}/{filename}: {type(e).__name__}: {e}")
        raise


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

    @property
    def depends_on_steps(self) -> list[str]:
        """List of step IDs this step depends on.

        Override in subclasses to specify dependencies.
        Used for idempotency cache invalidation when upstream artifacts change.

        Returns:
            List of step IDs (e.g., ['step0', 'step1'])
        """
        return []

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

    async def _heartbeat_loop(
        self,
        step_id: str,
        interval_seconds: int = 30,
    ) -> None:
        """Background task to send periodic heartbeats.

        Args:
            step_id: Step identifier for heartbeat message
            interval_seconds: Interval between heartbeats (default: 30s)
        """
        import logging

        logger = logging.getLogger(__name__)
        elapsed = 0
        while True:
            await asyncio.sleep(interval_seconds)
            elapsed += interval_seconds
            try:
                activity.heartbeat(f"{step_id} running ({elapsed}s elapsed)")
                logger.debug(f"Heartbeat sent for {step_id} ({elapsed}s)")
            except Exception as e:
                # Heartbeat failure is not fatal, just log and continue
                logger.warning(f"Heartbeat failed for {step_id}: {e}")
                break

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

        # Compute input digest for idempotency (includes dependency digests)
        input_digest = await self._compute_input_digest(tenant_id, run_id, config)

        # Check for existing output (idempotency)
        output_path = self.store.build_path(
            tenant_id=tenant_id,
            run_id=run_id,
            step=self.step_id,
        )

        existing_ref = await self._check_existing_output(output_path, input_digest)
        if existing_ref:
            activity.logger.info(f"Step {self.step_id}: Using existing output (idempotent skip)")
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
            tenant_id=tenant_id,
            step_name=self.step_id,
            status="running",
            retry_count=attempt,
        )

        # Start heartbeat loop for long-running activities (timeout > 120s)
        timeout_seconds = config.get("timeout", 120)
        heartbeat_task: asyncio.Task[None] | None = None
        if timeout_seconds > 120:
            heartbeat_task = asyncio.create_task(self._heartbeat_loop(self.step_id, interval_seconds=30))
            logger.info(f"[BaseActivity.run] Started heartbeat loop for {self.step_id}")

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
                tenant_id=tenant_id,
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
            # Collect error for diagnostics
            await self._collect_error(
                ctx=ctx,
                error=e,
                category=e.category,
                source="activity",
                context=e.details,
            )
            # Update step status in DB via API (with error_code)
            await self._update_step_status(
                run_id=run_id,
                tenant_id=tenant_id,
                step_name=self.step_id,
                status="failed",
                error_code=e.category.value,
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
            # Collect error for diagnostics
            await self._collect_error(
                ctx=ctx,
                error=e,
                category=ErrorCategory.RETRYABLE,
                source="activity",
                context={"unexpected": True},
            )
            # Update step status in DB via API (with error_code)
            await self._update_step_status(
                run_id=run_id,
                tenant_id=tenant_id,
                step_name=self.step_id,
                status="failed",
                error_code=ErrorCategory.RETRYABLE.value,
                error_message=str(e),
            )
            raise ActivityError(
                message=f"Unexpected error in {self.step_id}: {e}",
                category=ErrorCategory.RETRYABLE,
                details={"original_error": str(e)},
            ) from e

        finally:
            # Cancel heartbeat task if running
            if heartbeat_task is not None and not heartbeat_task.done():
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass  # Expected when cancelling
                logger.info(f"[BaseActivity.run] Cancelled heartbeat loop for {self.step_id}")

    async def _get_dependency_digests(
        self,
        tenant_id: str,
        run_id: str,
    ) -> dict[str, str | None]:
        """Get digests of all dependent step outputs.

        Args:
            tenant_id: Tenant identifier
            run_id: Run identifier

        Returns:
            dict mapping step_id to its output digest (or None if not found)
        """
        digests: dict[str, str | None] = {}
        for dep_step in self.depends_on_steps:
            meta_path = self.store.build_path(tenant_id, run_id, dep_step, "metadata.json")
            try:
                meta_content = await self._get_raw_content(meta_path)
            except Exception as e:
                raise ActivityError(
                    message=f"Failed to load dependency metadata for {dep_step}: {e}",
                    category=ErrorCategory.RETRYABLE,
                ) from e

            if not meta_content:
                digests[dep_step] = None
                continue

            try:
                metadata = json.loads(meta_content.decode("utf-8"))
            except json.JSONDecodeError as e:
                raise ActivityError(
                    message=f"Invalid metadata JSON for {dep_step}: {e}",
                    category=ErrorCategory.NON_RETRYABLE,
                ) from e

            digests[dep_step] = metadata.get("output_digest")
        return digests

    async def _compute_input_digest(
        self,
        tenant_id: str,
        run_id: str,
        config: dict[str, Any],
    ) -> str:
        """Compute SHA256 hash of inputs for idempotency check.

        Includes dependency artifact digests to invalidate cache when upstream changes.

        Raises:
            ActivityError: If required dependencies are missing
        """
        # Get dependency digests
        dependency_digests = await self._get_dependency_digests(tenant_id, run_id)

        # Validate required dependencies exist
        missing_deps = [dep for dep, digest in dependency_digests.items() if digest is None]
        if missing_deps:
            raise ActivityError(
                message=f"Step {self.step_id} cannot execute: missing required dependencies: {missing_deps}",
                category=ErrorCategory.NON_RETRYABLE,
                details={
                    "missing_dependencies": missing_deps,
                    "step": self.step_id,
                },
            )

        # Normalize config for consistent hashing
        input_data = {
            "tenant_id": tenant_id,
            "run_id": run_id,
            "step_id": self.step_id,
            "config": config,
            "dependency_digests": dependency_digests,
        }
        input_json = json.dumps(input_data, sort_keys=True)
        return hashlib.sha256(input_json.encode()).hexdigest()

    async def _check_existing_output(
        self,
        path: str,
        input_digest: str,
    ) -> ArtifactRef | None:
        """Check if valid output already exists.

        Verifies that:
        1. Output artifact exists at the expected path
        2. Metadata file exists with matching input_digest
        3. Output digest matches the one stored in metadata

        Args:
            path: Expected output path
            input_digest: Input hash for verification

        Returns:
            ArtifactRef if valid output exists with matching input, None otherwise
        """
        import logging

        logger = logging.getLogger(__name__)

        try:
            # Validate path format: {tenant_id}/{run_id}/{step}/output.json
            path_parts = path.split("/")
            if len(path_parts) < 4:
                return None

            step = path_parts[2]  # For logging

            # Try to get metadata file
            meta_path = path.replace("/output.json", "/metadata.json")
            meta_content = await self._get_raw_content(meta_path)

            if meta_content is None:
                logger.debug(f"No metadata found for {step}, will execute")
                return None

            # Parse metadata
            metadata = json.loads(meta_content.decode("utf-8"))
            stored_input_digest = metadata.get("input_digest")

            if stored_input_digest != input_digest:
                logger.info(f"Input digest mismatch for {step}: stored={stored_input_digest[:8]}... vs current={input_digest[:8]}...")
                return None

            # Get output artifact to verify it exists and get its digest
            output_content = await self._get_raw_content(path)
            if output_content is None:
                logger.warning(f"Metadata exists but output missing for {step}")
                return None

            # Calculate current digest
            output_digest = hashlib.sha256(output_content).hexdigest()

            logger.info(f"Cache hit for {step}: input_digest matches, returning cached output")

            return ArtifactRef(
                path=path,
                digest=output_digest,
                content_type="application/json",
                size_bytes=len(output_content),
            )

        except json.JSONDecodeError as e:
            activity.logger.warning(f"Failed to parse metadata: {e}")
            return None
        except Exception as e:
            activity.logger.debug(f"Cache check failed: {e}")
            return None

    async def _get_raw_content(self, path: str) -> bytes | None:
        """Get raw content from storage by path.

        Args:
            path: Full storage path

        Returns:
            Content bytes if exists, None otherwise
        """
        try:
            from minio.error import S3Error

            response = self.store.client.get_object(
                bucket_name=self.store.bucket,
                object_name=path,
            )
            content = response.read()
            response.close()
            response.release_conn()
            return content
        except S3Error as e:
            if e.code == "NoSuchKey":
                return None
            raise
        except Exception as e:
            activity.logger.warning(f"Storage read failed for {path}: {e}")
            raise

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
        meta_content = json.dumps(
            {
                "input_digest": input_digest,
                "step_id": self.step_id,
                "created_at": ctx.started_at.isoformat(),
                "attempt": ctx.attempt,
            }
        )
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
        tenant_id: str,
        step_name: str,
        status: str,
        error_code: str | None = None,
        error_message: str | None = None,
        retry_count: int = 0,
    ) -> None:
        """Update step status via internal API.

        Sends HTTP request to API to record step progress in DB.
        Failures are logged but not raised to avoid blocking workflow.

        Args:
            run_id: Run identifier
            tenant_id: Tenant identifier (required for multi-tenant isolation)
            step_name: Step identifier
            status: Step status (running, completed, failed)
            error_code: ErrorCategory enum value (RETRYABLE, NON_RETRYABLE, etc.)
            error_message: Error message (if failed)
            retry_count: Number of retry attempts
        """
        import logging

        logger = logging.getLogger(__name__)

        max_attempts = 3 if status in ("completed", "failed") else 1
        for attempt in range(1, max_attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        f"{API_BASE_URL}/api/internal/steps/update",
                        json={
                            "run_id": run_id,
                            "tenant_id": tenant_id,
                            "step_name": step_name,
                            "status": status,
                            "error_code": error_code,
                            "error_message": error_message,
                            "retry_count": retry_count,
                        },
                    )
                if response.status_code == 200:
                    logger.info(f"Step status updated: {step_name} -> {status}")
                    return
                logger.warning(f"Failed to update step status: {response.status_code} {response.text}")
            except Exception as e:
                logger.warning(f"Failed to update step status via API: {e}")

            if attempt < max_attempts:
                await asyncio.sleep(2 ** (attempt - 1))

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
        source: str = "activity",
        context: dict[str, Any] | None = None,
    ) -> None:
        """Collect error for LLM-based diagnostics.

        Stores error details in the error_logs table for later analysis
        by the diagnostics service.

        Args:
            ctx: Execution context
            error: The exception that occurred
            category: Error classification
            source: Error source (activity, llm, tool, validation, storage, api)
            context: Additional context (LLM model, tool, params, etc.)
        """
        import traceback

        try:
            from sqlalchemy import text

            from apps.api.db.tenant import get_tenant_engine

            # Get tenant database engine
            engine = await get_tenant_engine(ctx.tenant_id)

            # Build error context
            error_context = context or {}
            error_context.update(
                {
                    "step_id": ctx.step_id,
                    "timeout_seconds": ctx.timeout_seconds,
                    "config_keys": list(ctx.config.keys()) if ctx.config else [],
                }
            )

            # Get stack trace
            stack_trace = "".join(traceback.format_exception(type(error), error, error.__traceback__))

            async with engine.connect() as conn:
                await conn.execute(
                    text(
                        """
                        INSERT INTO error_logs
                        (run_id, source, error_category, error_type,
                         error_message, stack_trace, context, attempt)
                        VALUES
                        (:run_id, :source, :error_category, :error_type,
                         :error_message, :stack_trace, :context::jsonb, :attempt)
                        """
                    ),
                    {
                        "run_id": ctx.run_id,
                        "source": source,
                        "error_category": category.value,
                        "error_type": type(error).__name__,
                        "error_message": str(error),
                        "stack_trace": stack_trace,
                        "context": json.dumps(error_context),
                        "attempt": ctx.attempt,
                    },
                )
                await conn.commit()

            activity.logger.debug(f"Error logged for diagnostics: {type(error).__name__} in {ctx.step_id}")

        except Exception as log_error:
            # Don't fail the activity if error logging fails
            activity.logger.warning(f"Failed to log error for diagnostics: {log_error}")
