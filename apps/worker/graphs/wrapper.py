"""Common node wrapper for LangGraph steps.

Provides consistent handling for all graph nodes:
- Prompt loading and rendering
- LLM/Tool execution
- Output validation
- Artifact storage
- Event emission
- State updates
"""

import json
import time
from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import Any

from apps.api.core.context import ExecutionContext
from apps.api.core.errors import ErrorCategory, StepError
from apps.api.core.state import GraphState, add_error, add_step_output, add_validation_report
from apps.api.observability.events import Event, EventEmitter, EventType
from apps.api.prompts.loader import PromptPackLoader
from apps.api.storage.artifact_store import ArtifactStore
from apps.api.storage.schemas import ArtifactRef
from apps.api.validation.base import ValidatorInterface
from apps.api.validation.json_validator import JsonValidator


class StepWrapperError(Exception):
    """Error during step wrapper execution."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.RETRYABLE,
        details: dict[str, Any] | None = None,
    ):
        self.category = category
        self.details = details or {}
        super().__init__(message)


async def step_wrapper(
    step_fn: Callable[[str, GraphState, ExecutionContext], Coroutine[Any, Any, dict[str, Any]]],
    ctx: ExecutionContext,
    state: GraphState,
    config: dict[str, Any],
    validator: ValidatorInterface | None = None,
    store: ArtifactStore | None = None,
    emitter: EventEmitter | None = None,
) -> GraphState:
    """Common wrapper for all LangGraph nodes.

    This wrapper handles:
    1. Prompt loading from pack
    2. Step function execution
    3. Output validation
    4. Artifact storage
    5. Event emission
    6. State updates

    Args:
        step_fn: The step function to execute (receives prompt, state, ctx)
        ctx: Execution context
        state: Current graph state
        config: Configuration including pack_id
        validator: Optional validator (default: JSONValidator)
        store: Artifact store (default: new ArtifactStore)
        emitter: Event emitter (default: new EventEmitter)

    Returns:
        Updated GraphState with step output

    Raises:
        StepWrapperError: On execution failure
    """
    store = store or ArtifactStore()
    emitter = emitter or EventEmitter()
    validator = validator or JsonValidator()

    start_time = time.time()

    # Step 1: Load and render prompt
    pack_id = config.get("pack_id")
    if not pack_id:
        raise StepWrapperError(
            "pack_id is required. Auto-execution without explicit pack_id is forbidden.",
            category=ErrorCategory.NON_RETRYABLE,
        )

    loader = PromptPackLoader()
    prompt_pack = loader.load(pack_id)

    try:
        prompt_template = prompt_pack.get_prompt(ctx.step_id)
        # Render with state data
        render_vars = _extract_render_vars(state, config)
        prompt = prompt_template.render(**render_vars)
    except Exception as e:
        raise StepWrapperError(
            f"Failed to load/render prompt for {ctx.step_id}: {e}",
            category=ErrorCategory.NON_RETRYABLE,
        ) from e

    # Step 2: Emit step started event
    await emitter.emit(Event(
        event_type=EventType.STEP_STARTED,
        run_id=ctx.run_id,
        step_id=ctx.step_id,
        tenant_id=ctx.tenant_id,
        payload={"attempt": ctx.attempt},
    ))

    try:
        # Step 3: Execute step function
        result = await step_fn(prompt, state, ctx)

        # Step 4: Validate output
        if result:
            result_json = json.dumps(result, ensure_ascii=False)
            validation_report = validator.validate(result_json.encode())

            if not validation_report.valid:
                # Check if errors are critical
                if validation_report.has_errors():
                    err_count = validation_report.error_count()
                    raise StepWrapperError(
                        f"Validation failed for {ctx.step_id}: {err_count} errors",
                        category=ErrorCategory.VALIDATION_FAIL,
                        details={"issues": [i.model_dump() for i in validation_report.issues]},
                    )

            # Add validation report to state
            state = add_validation_report(state, validation_report)

        # Step 5: Store artifact
        artifact_ref = await _store_artifact(
            store=store,
            ctx=ctx,
            result=result,
        )

        # Step 6: Calculate metrics
        duration_ms = int((time.time() - start_time) * 1000)

        # Step 7: Emit success event
        await emitter.emit(Event(
            event_type=EventType.STEP_SUCCEEDED,
            run_id=ctx.run_id,
            step_id=ctx.step_id,
            tenant_id=ctx.tenant_id,
            payload={
                "duration_ms": duration_ms,
                "artifact_path": artifact_ref.path,
                "artifact_digest": artifact_ref.digest,
            },
        ))

        # Step 8: Update state
        state = add_step_output(state, ctx.step_id, artifact_ref)
        state = GraphState(**{
            **state,
            "current_step": ctx.step_id,
            "status": "running",
        })

        return state

    except StepWrapperError:
        raise

    except Exception as e:
        # Emit failure event
        await emitter.emit(Event(
            event_type=EventType.STEP_FAILED,
            run_id=ctx.run_id,
            step_id=ctx.step_id,
            tenant_id=ctx.tenant_id,
            payload={
                "error": str(e),
                "category": ErrorCategory.RETRYABLE.value,
            },
        ))

        # Add error to state
        error = StepError(
            step_id=ctx.step_id,
            category=ErrorCategory.RETRYABLE,
            message=str(e),
            occurred_at=datetime.now(),
            attempt=ctx.attempt,
        )
        state = add_error(state, error)

        raise StepWrapperError(
            f"Step {ctx.step_id} failed: {e}",
            category=ErrorCategory.RETRYABLE,
        ) from e


def _extract_render_vars(state: GraphState, config: dict[str, Any]) -> dict[str, Any]:
    """Extract variables for prompt rendering from state and config."""
    vars_dict: dict[str, Any] = {}

    # Add config values
    vars_dict["keyword"] = config.get("keyword", "")

    # Add previous step outputs (summaries, not full content)
    step_outputs = state.get("step_outputs", {})
    for step_id, artifact_ref in step_outputs.items():
        # Add reference info (not actual content - that's in storage)
        vars_dict[f"{step_id}_ref"] = artifact_ref.path if artifact_ref else None

    return vars_dict


async def _store_artifact(
    store: ArtifactStore,
    ctx: ExecutionContext,
    result: dict[str, Any],
) -> ArtifactRef:
    """Store step result as artifact."""
    content = json.dumps(result, ensure_ascii=False, indent=2)
    content_bytes = content.encode("utf-8")

    path = store.build_path(
        tenant_id=ctx.tenant_id,
        run_id=ctx.run_id,
        step=ctx.step_id,
    )

    return await store.put(
        content=content_bytes,
        path=path,
        content_type="application/json",
    )


def create_node_function(
    step_id: str,
    execute_fn: Callable[[str, GraphState, ExecutionContext], Coroutine[Any, Any, dict[str, Any]]],
) -> Callable[[GraphState], Coroutine[Any, Any, GraphState]]:
    """Create a LangGraph node function with consistent wrapper behavior.

    Args:
        step_id: Step identifier
        execute_fn: Function that executes the step logic

    Returns:
        Async function suitable for use as a LangGraph node
    """

    async def node_fn(state: GraphState) -> GraphState:
        """LangGraph node function."""
        ctx = ExecutionContext(
            run_id=state["run_id"],
            step_id=step_id,
            attempt=1,  # LangGraph nodes don't have built-in retry tracking
            tenant_id=state["tenant_id"],
            started_at=datetime.now(),
            timeout_seconds=state.get("config", {}).get("timeout", 120),
            config=state.get("config", {}),
        )

        return await step_wrapper(
            step_fn=execute_fn,
            ctx=ctx,
            state=state,
            config=state.get("config", {}),
        )

    return node_fn
