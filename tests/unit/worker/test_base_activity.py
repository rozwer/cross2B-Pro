"""Unit tests for BaseActivity."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from apps.api.core.errors import ErrorCategory
from apps.api.validation.schemas import ValidationReport
from apps.worker.activities.base import (
    ActivityError,
    BaseActivity,
    ValidationError,
)


class TestActivityError:
    """Tests for ActivityError exception."""

    def test_default_category_is_retryable(self):
        """Test default error category is RETRYABLE."""
        error = ActivityError("Test error")
        assert error.category == ErrorCategory.RETRYABLE

    def test_custom_category(self):
        """Test custom error category."""
        error = ActivityError(
            "Auth error",
            category=ErrorCategory.NON_RETRYABLE,
        )
        assert error.category == ErrorCategory.NON_RETRYABLE

    def test_error_details(self):
        """Test error details are stored."""
        details = {"key": "value", "count": 42}
        error = ActivityError("Error", details=details)
        assert error.details == details


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_validation_error_from_report(self):
        """Test ValidationError created from ValidationReport."""
        report = ValidationReport(
            valid=False,
            format="json",
            issues=[],
            validated_at=datetime.now(),
            original_hash="abc123",
        )

        error = ValidationError(report)

        assert error.category == ErrorCategory.VALIDATION_FAIL
        assert error.report == report

    def test_validation_error_custom_message(self):
        """Test ValidationError with custom message."""
        report = ValidationReport(
            valid=False,
            format="json",
            issues=[],
            validated_at=datetime.now(),
            original_hash="abc123",
        )

        error = ValidationError(report, message="Custom validation message")

        assert "Custom validation message" in str(error)


class TestBaseActivityInputDigest:
    """Tests for input digest computation."""

    @pytest.mark.asyncio
    async def test_compute_input_digest_deterministic(self):
        """Test input digest is deterministic for same inputs."""

        class TestActivity(BaseActivity):
            @property
            def step_id(self) -> str:
                return "test_step"

            async def execute(self, ctx, state):
                return {}

        activity = TestActivity()

        digest1 = await activity._compute_input_digest(
            tenant_id="tenant1",
            run_id="run1",
            config={"key": "value"},
        )
        digest2 = await activity._compute_input_digest(
            tenant_id="tenant1",
            run_id="run1",
            config={"key": "value"},
        )

        assert digest1 == digest2

    @pytest.mark.asyncio
    async def test_compute_input_digest_different_for_different_inputs(self):
        """Test input digest differs for different inputs."""

        class TestActivity(BaseActivity):
            @property
            def step_id(self) -> str:
                return "test_step"

            async def execute(self, ctx, state):
                return {}

        activity = TestActivity()

        digest1 = await activity._compute_input_digest(
            tenant_id="tenant1",
            run_id="run1",
            config={"key": "value1"},
        )
        digest2 = await activity._compute_input_digest(
            tenant_id="tenant1",
            run_id="run1",
            config={"key": "value2"},
        )

        assert digest1 != digest2

    @pytest.mark.asyncio
    async def test_compute_input_digest_is_sha256(self):
        """Test digest is valid SHA256 hex string."""

        class TestActivity(BaseActivity):
            @property
            def step_id(self) -> str:
                return "test_step"

            async def execute(self, ctx, state):
                return {}

        activity = TestActivity()

        digest = await activity._compute_input_digest(
            tenant_id="tenant1",
            run_id="run1",
            config={},
        )

        # SHA256 produces 64 hex characters
        assert len(digest) == 64
        assert all(c in "0123456789abcdef" for c in digest)


class TestBaseActivityStepError:
    """Tests for StepError creation."""

    def test_create_step_error(self):
        """Test StepError creation from activity."""

        class TestActivity(BaseActivity):
            @property
            def step_id(self) -> str:
                return "test_step"

            async def execute(self, ctx, state):
                return {}

        activity = TestActivity()

        # Mock activity.info() for attempt number
        with patch("temporalio.activity.info") as mock_info:
            mock_info.return_value = MagicMock(attempt=2)

            error = activity.create_step_error(
                message="Test error message",
                category=ErrorCategory.RETRYABLE,
                details={"test": "data"},
            )

        assert error.step_id == "test_step"
        assert error.message == "Test error message"
        assert error.category == ErrorCategory.RETRYABLE
        assert error.details == {"test": "data"}
        assert error.attempt == 2
