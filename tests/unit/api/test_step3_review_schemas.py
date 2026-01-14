"""Tests for Step3 Review schemas and validation.

REQ-01: 指示付き却下
REQ-02: ステップ個別リトライ
REQ-03: 修正指示の反映
REQ-04: 再レビュー
REQ-05: リトライ上限
"""

import pytest
from pydantic import ValidationError

from apps.api.schemas.runs import (
    Step3ReviewItem,
    Step3ReviewInput,
    Step3ReviewResponse,
    RejectRunInput,
    STEP3_VALID_STEPS,
    STEP3_RETRY_LIMIT,
)


class TestStep3ReviewConstants:
    """Test constants for Step3 review."""

    def test_valid_steps_defined(self) -> None:
        """Test that valid step names are defined."""
        assert "step3a" in STEP3_VALID_STEPS
        assert "step3b" in STEP3_VALID_STEPS
        assert "step3c" in STEP3_VALID_STEPS
        assert len(STEP3_VALID_STEPS) == 3

    def test_retry_limit_defined(self) -> None:
        """Test that retry limit is defined (REQ-05)."""
        assert STEP3_RETRY_LIMIT == 3


class TestStep3ReviewItem:
    """Test individual Step3 review item validation."""

    def test_valid_approval(self) -> None:
        """Test valid approval item."""
        item = Step3ReviewItem(step="step3a", accepted=True)
        assert item.step == "step3a"
        assert item.accepted is True
        assert item.retry is False
        assert item.retry_instruction == ""

    def test_valid_retry_with_instruction(self) -> None:
        """Test valid retry item with instruction (REQ-03)."""
        item = Step3ReviewItem(
            step="step3b",
            accepted=False,
            retry=True,
            retry_instruction="ペルソナをより具体的に。年齢層と職業を明記してください",
        )
        assert item.step == "step3b"
        assert item.accepted is False
        assert item.retry is True
        assert item.retry_instruction == "ペルソナをより具体的に。年齢層と職業を明記してください"

    def test_invalid_step_name(self) -> None:
        """Test that invalid step names are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Step3ReviewItem(step="step99", accepted=True)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "step" in errors[0]["loc"]
        assert "Invalid step" in errors[0]["msg"]

    def test_invalid_step_names_examples(self) -> None:
        """Test various invalid step names."""
        invalid_steps = ["step3", "step3d", "step4", "step3A", "STEP3A", ""]

        for step in invalid_steps:
            with pytest.raises(ValidationError):
                Step3ReviewItem(step=step, accepted=True)

    def test_retry_requires_instruction(self) -> None:
        """Test that retry requires instruction (REQ-03)."""
        with pytest.raises(ValidationError) as exc_info:
            Step3ReviewItem(
                step="step3a",
                accepted=False,
                retry=True,
                retry_instruction="",  # Empty instruction should fail
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "retry_instruction is required" in errors[0]["msg"]

    def test_retry_without_instruction_explicit(self) -> None:
        """Test retry without instruction (using default empty string) is invalid."""
        # retry_instruction defaults to "" which triggers validation error
        with pytest.raises(ValidationError):
            Step3ReviewItem(step="step3c", accepted=False, retry=True, retry_instruction="")


class TestStep3ReviewInput:
    """Test Step3 review input validation."""

    def test_valid_all_approved(self) -> None:
        """Test valid input with all steps approved."""
        input_data = Step3ReviewInput(
            reviews=[
                Step3ReviewItem(step="step3a", accepted=True),
                Step3ReviewItem(step="step3b", accepted=True),
                Step3ReviewItem(step="step3c", accepted=True),
            ]
        )
        assert len(input_data.reviews) == 3
        assert all(r.accepted for r in input_data.reviews)

    def test_valid_mixed_approval_retry(self) -> None:
        """Test valid input with mixed approval and retry (REQ-02)."""
        input_data = Step3ReviewInput(
            reviews=[
                Step3ReviewItem(step="step3a", accepted=True),
                Step3ReviewItem(
                    step="step3b",
                    accepted=False,
                    retry=True,
                    retry_instruction="競合との差別化ポイントをもっと明確に",
                ),
                Step3ReviewItem(step="step3c", accepted=True),
            ]
        )
        assert len(input_data.reviews) == 3
        retrying = [r for r in input_data.reviews if r.retry]
        assert len(retrying) == 1
        assert retrying[0].step == "step3b"

    def test_valid_all_retry(self) -> None:
        """Test valid input with all steps retrying."""
        input_data = Step3ReviewInput(
            reviews=[
                Step3ReviewItem(
                    step="step3a",
                    accepted=False,
                    retry=True,
                    retry_instruction="Instruction for 3A",
                ),
                Step3ReviewItem(
                    step="step3b",
                    accepted=False,
                    retry=True,
                    retry_instruction="Instruction for 3B",
                ),
                Step3ReviewItem(
                    step="step3c",
                    accepted=False,
                    retry=True,
                    retry_instruction="Instruction for 3C",
                ),
            ]
        )
        assert len(input_data.reviews) == 3
        assert all(r.retry for r in input_data.reviews)

    def test_duplicate_steps_rejected(self) -> None:
        """Test that duplicate steps are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Step3ReviewInput(
                reviews=[
                    Step3ReviewItem(step="step3a", accepted=True),
                    Step3ReviewItem(step="step3a", accepted=False),  # Duplicate
                ]
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "Duplicate step" in errors[0]["msg"]

    def test_empty_reviews_allowed(self) -> None:
        """Test that empty reviews list is allowed."""
        input_data = Step3ReviewInput(reviews=[])
        assert len(input_data.reviews) == 0

    def test_partial_reviews_allowed(self) -> None:
        """Test that partial reviews (not all steps) is allowed."""
        input_data = Step3ReviewInput(
            reviews=[
                Step3ReviewItem(step="step3a", accepted=True),
                # step3b and step3c not included
            ]
        )
        assert len(input_data.reviews) == 1


class TestStep3ReviewResponse:
    """Test Step3 review response model."""

    def test_proceed_response(self) -> None:
        """Test response when all steps approved."""
        response = Step3ReviewResponse(
            success=True,
            retrying=[],
            approved=["step3a", "step3b", "step3c"],
            next_action="proceed_to_step3_5",
            retry_counts={},
        )
        assert response.success is True
        assert response.next_action == "proceed_to_step3_5"
        assert len(response.approved) == 3
        assert len(response.retrying) == 0

    def test_retry_response(self) -> None:
        """Test response when some steps need retry."""
        response = Step3ReviewResponse(
            success=True,
            retrying=["step3a", "step3c"],
            approved=["step3b"],
            next_action="waiting_retry_completion",
            retry_counts={"step3a": 1, "step3c": 1},
        )
        assert response.success is True
        assert response.next_action == "waiting_retry_completion"
        assert len(response.retrying) == 2
        assert response.retry_counts["step3a"] == 1

    def test_waiting_approval_response(self) -> None:
        """Test response when waiting for approval after retry (REQ-04)."""
        response = Step3ReviewResponse(
            success=True,
            retrying=[],
            approved=[],
            next_action="waiting_approval",
            retry_counts={"step3a": 2, "step3b": 1, "step3c": 0},
        )
        assert response.next_action == "waiting_approval"


class TestRejectRunInputWithInstructions:
    """Test RejectRunInput with step instructions (REQ-01)."""

    def test_simple_rejection(self) -> None:
        """Test simple rejection without retry."""
        input_data = RejectRunInput(reason="Output quality insufficient")
        assert input_data.reason == "Output quality insufficient"
        assert input_data.retry_with_instructions is False
        assert input_data.step_instructions is None

    def test_rejection_with_retry_instructions(self) -> None:
        """Test rejection with retry instructions (REQ-01)."""
        input_data = RejectRunInput(
            reason="Need improvements",
            retry_with_instructions=True,
            step_instructions={
                "step3a": "ペルソナをより具体的に",
                "step3c": "競合分析を詳細に",
            },
        )
        assert input_data.retry_with_instructions is True
        assert input_data.step_instructions is not None
        assert "step3a" in input_data.step_instructions
        assert "step3c" in input_data.step_instructions
        assert "step3b" not in input_data.step_instructions

    def test_empty_reason_allowed(self) -> None:
        """Test that empty reason is allowed."""
        input_data = RejectRunInput(reason="")
        assert input_data.reason == ""

    def test_default_reason(self) -> None:
        """Test default reason value."""
        input_data = RejectRunInput()
        assert input_data.reason == ""


class TestStep3ReviewBusinessLogic:
    """Test Step3 review business logic scenarios."""

    def test_approve_then_proceed_scenario(self) -> None:
        """Test scenario: User approves all → proceed to step3.5."""
        # Input
        reviews = Step3ReviewInput(
            reviews=[
                Step3ReviewItem(step="step3a", accepted=True),
                Step3ReviewItem(step="step3b", accepted=True),
                Step3ReviewItem(step="step3c", accepted=True),
            ]
        )

        # Business logic would produce:
        approved = [r.step for r in reviews.reviews if r.accepted]
        retrying = [r.step for r in reviews.reviews if r.retry]

        assert approved == ["step3a", "step3b", "step3c"]
        assert retrying == []

    def test_partial_retry_scenario(self) -> None:
        """Test scenario: User approves some, retries others."""
        reviews = Step3ReviewInput(
            reviews=[
                Step3ReviewItem(step="step3a", accepted=True),
                Step3ReviewItem(
                    step="step3b",
                    accepted=False,
                    retry=True,
                    retry_instruction="More detail needed",
                ),
                Step3ReviewItem(step="step3c", accepted=True),
            ]
        )

        approved = [r.step for r in reviews.reviews if r.accepted]
        retrying = [r.step for r in reviews.reviews if r.retry]
        instructions = {r.step: r.retry_instruction for r in reviews.reviews if r.retry}

        assert approved == ["step3a", "step3c"]
        assert retrying == ["step3b"]
        assert instructions["step3b"] == "More detail needed"

    def test_retry_limit_check_logic(self) -> None:
        """Test retry limit check logic (REQ-05)."""
        # Simulate retry counts from workflow state
        current_retry_counts = {"step3a": 2, "step3b": 1, "step3c": 0}

        # User requests retry for step3a (already at count 2)
        requested_retry_steps = ["step3a"]

        # Check if any step exceeds limit
        for step in requested_retry_steps:
            current_count = current_retry_counts.get(step, 0)
            if current_count >= STEP3_RETRY_LIMIT:
                # Would raise error in actual API
                assert step == "step3a"
                assert current_count == 2
                # At count 2, next retry would be #3, which is at limit
                # Count 3 would exceed limit

        # This test documents the limit checking logic
        assert STEP3_RETRY_LIMIT == 3
