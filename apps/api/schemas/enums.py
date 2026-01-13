"""Shared enums for API."""

from enum import Enum


class RunStatus(str, Enum):
    """Run status values matching UI expectations."""

    PENDING = "pending"
    WORKFLOW_STARTING = "workflow_starting"  # Temporal Workflow開始処理中（競合状態対策）
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    WAITING_IMAGE_INPUT = "waiting_image_input"  # Step11画像生成のユーザー入力待ち
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Step status values matching UI expectations."""

    PENDING = "pending"
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ErrorType(str, Enum):
    """Error type classification."""

    RETRYABLE = "RETRYABLE"
    NON_RETRYABLE = "NON_RETRYABLE"
    VALIDATION_FAIL = "VALIDATION_FAIL"


class StepAttemptStatus(str, Enum):
    """Step attempt status values."""

    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
