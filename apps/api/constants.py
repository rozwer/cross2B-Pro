"""API Constants

Centralized constants for the API module to avoid duplication and ensure consistency.
"""

# Workflow step order for retry operations
# These are the steps that can be retried individually
RETRY_STEP_ORDER: tuple[str, ...] = (
    "step0",
    "step1",
    "step1_5",
    "step2",
    "step3a",
    "step3b",
    "step3c",
    "step3_5",
    "step4",
    "step5",
    "step6",
    "step6_5",
    "step7a",
    "step7b",
    "step8",
    "step9",
    "step10",
    "step11",
    "step12",
)

# Workflow step order for resume operations
# step3 is accepted and normalized to step3a
# step3b/3c are not allowed as resume points (must resume from step3 or step3a)
RESUME_STEP_ORDER: tuple[str, ...] = (
    "step0",
    "step1",
    "step1_5",
    "step2",
    "step3",  # Accepted and normalized to step3a
    "step3a",  # step3 group entry point
    "step3_5",
    "step4",
    "step5",
    "step6",
    "step6_5",
    "step7a",
    "step7b",
    "step8",
    "step9",
    "step10",
    "step11",
    "step12",
)

# Steps that cannot be used as resume points
INVALID_RESUME_STEPS: frozenset[str] = frozenset({"step3b", "step3c"})

# Run statuses that can be paused (一時停止可能なステータス)
PAUSABLE_STATUSES: frozenset[str] = frozenset(
    {
        "running",
        "waiting_approval",
        "waiting_image_input",
    }
)

# Run statuses that indicate workflow is in progress (進行中ステータス)
IN_PROGRESS_STATUSES: frozenset[str] = frozenset(
    {
        "pending",
        "workflow_starting",
        "running",
        "paused",
        "waiting_approval",
        "waiting_image_input",
    }
)
