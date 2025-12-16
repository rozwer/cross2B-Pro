"""Tests for error classification."""

from datetime import datetime

import pytest

from apps.api.core.errors import ErrorCategory, StepError


class TestErrorCategory:
    """Tests for ErrorCategory enum."""

    def test_retryable_value(self) -> None:
        """Test RETRYABLE has correct string value."""
        assert ErrorCategory.RETRYABLE.value == "retryable"

    def test_non_retryable_value(self) -> None:
        """Test NON_RETRYABLE has correct string value."""
        assert ErrorCategory.NON_RETRYABLE.value == "non_retryable"

    def test_validation_fail_value(self) -> None:
        """Test VALIDATION_FAIL has correct string value."""
        assert ErrorCategory.VALIDATION_FAIL.value == "validation_fail"


class TestStepError:
    """Tests for StepError model."""

    def test_create_retryable_error(self) -> None:
        """Test creating a retryable error."""
        error = StepError(
            step_id="step_1",
            category=ErrorCategory.RETRYABLE,
            message="Temporary API error",
            occurred_at=datetime.now(),
            attempt=1,
        )
        assert error.is_retryable() is True
        assert error.is_validation_failure() is False

    def test_create_non_retryable_error(self) -> None:
        """Test creating a non-retryable error."""
        error = StepError(
            step_id="step_1",
            category=ErrorCategory.NON_RETRYABLE,
            message="Invalid configuration",
            occurred_at=datetime.now(),
            attempt=1,
        )
        assert error.is_retryable() is False
        assert error.is_validation_failure() is False

    def test_create_validation_error(self) -> None:
        """Test creating a validation error."""
        error = StepError(
            step_id="step_1",
            category=ErrorCategory.VALIDATION_FAIL,
            message="Output validation failed",
            details={"field": "content", "reason": "too short"},
            occurred_at=datetime.now(),
            attempt=2,
        )
        assert error.is_retryable() is False
        assert error.is_validation_failure() is True
        assert error.details is not None
        assert error.attempt == 2

    def test_attempt_must_be_positive(self) -> None:
        """Test that attempt must be >= 1."""
        with pytest.raises(ValueError):
            StepError(
                step_id="step_1",
                category=ErrorCategory.RETRYABLE,
                message="Error",
                occurred_at=datetime.now(),
                attempt=0,
            )
