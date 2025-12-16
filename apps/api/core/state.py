"""GraphState schema for LangGraph workflows.

GraphState is the central contract that all workflow steps share.
All step outputs are stored as ArtifactRef (path/digest) - never raw content.
"""

from typing import Any, TypedDict

from ..storage.schemas import ArtifactRef
from ..validation.schemas import ValidationReport
from .errors import StepError


class GraphState(TypedDict, total=False):
    """Central state schema for LangGraph workflows.

    All fields except run_id and tenant_id are optional (total=False).
    Step outputs are stored as ArtifactRef to keep state small.

    IMPORTANT: Never store large JSON or content directly in state.
    Always use ArtifactRef with path/digest.
    """

    # Required identifiers
    run_id: str
    tenant_id: str

    # Current execution state
    current_step: str
    status: str  # pending, running, paused, completed, failed

    # Step outputs - key is step name, value is reference to stored artifact
    step_outputs: dict[str, ArtifactRef]

    # Validation results from each step
    validation_reports: list[ValidationReport]

    # Errors encountered during execution
    errors: list[StepError]

    # Runtime configuration (LLM settings, timeouts, etc.)
    config: dict[str, Any]

    # Additional metadata (timestamps, user info, etc.)
    metadata: dict[str, Any]


def create_initial_state(
    run_id: str,
    tenant_id: str,
    config: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> GraphState:
    """Create initial state for a new workflow run."""
    return GraphState(
        run_id=run_id,
        tenant_id=tenant_id,
        current_step="init",
        status="pending",
        step_outputs={},
        validation_reports=[],
        errors=[],
        config=config or {},
        metadata=metadata or {},
    )


def add_step_output(
    state: GraphState,
    step: str,
    artifact_ref: ArtifactRef,
) -> GraphState:
    """Add a step output to state (immutable update)."""
    outputs = dict(state.get("step_outputs", {}))
    outputs[step] = artifact_ref
    return GraphState(**{**state, "step_outputs": outputs})


def add_error(
    state: GraphState,
    error: StepError,
) -> GraphState:
    """Add an error to state (immutable update)."""
    errors = list(state.get("errors", []))
    errors.append(error)
    return GraphState(**{**state, "errors": errors})


def add_validation_report(
    state: GraphState,
    report: ValidationReport,
) -> GraphState:
    """Add a validation report to state (immutable update)."""
    reports = list(state.get("validation_reports", []))
    reports.append(report)
    return GraphState(**{**state, "validation_reports": reports})
