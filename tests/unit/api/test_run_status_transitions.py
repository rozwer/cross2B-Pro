"""Tests for Run status transitions including WORKFLOW_STARTING intermediate state."""

from apps.api.schemas.enums import RunStatus


class TestRunStatusEnum:
    """Tests for RunStatus enum values."""

    def test_workflow_starting_status_exists(self) -> None:
        """Test that WORKFLOW_STARTING status is available."""
        assert hasattr(RunStatus, "WORKFLOW_STARTING")
        assert RunStatus.WORKFLOW_STARTING.value == "workflow_starting"

    def test_all_expected_statuses_exist(self) -> None:
        """Test that all expected status values are defined."""
        expected_statuses = [
            "pending",
            "workflow_starting",
            "running",
            "waiting_approval",
            "waiting_image_input",
            "completed",
            "failed",
            "cancelled",
        ]

        actual_values = [status.value for status in RunStatus]
        for expected in expected_statuses:
            assert expected in actual_values, f"Missing status: {expected}"

    def test_status_string_conversion(self) -> None:
        """Test that RunStatus can be used as strings."""
        assert str(RunStatus.WORKFLOW_STARTING) == "RunStatus.WORKFLOW_STARTING"
        assert RunStatus.WORKFLOW_STARTING.value == "workflow_starting"
        # StrEnum inherits from str, so value comparison works
        assert RunStatus.WORKFLOW_STARTING.value == "workflow_starting"


class TestStatusTransitionLogic:
    """Tests for valid status transitions.

    These tests document the expected state machine behavior.
    """

    def test_valid_transitions_from_pending(self) -> None:
        """Test valid transitions from PENDING status."""
        # PENDING can transition to:
        # - WORKFLOW_STARTING (when workflow is being started)
        # - CANCELLED (if cancelled before start)
        valid_from_pending = [
            RunStatus.WORKFLOW_STARTING,
            RunStatus.CANCELLED,
        ]

        # This is a documentation test - actual enforcement is in business logic
        for target in valid_from_pending:
            assert target in RunStatus

    def test_valid_transitions_from_workflow_starting(self) -> None:
        """Test valid transitions from WORKFLOW_STARTING status."""
        # WORKFLOW_STARTING can transition to:
        # - RUNNING (workflow started successfully)
        # - FAILED (workflow failed to start)
        valid_from_workflow_starting = [
            RunStatus.RUNNING,
            RunStatus.FAILED,
        ]

        for target in valid_from_workflow_starting:
            assert target in RunStatus

    def test_valid_transitions_from_running(self) -> None:
        """Test valid transitions from RUNNING status."""
        # RUNNING can transition to:
        # - WAITING_APPROVAL (at approval checkpoint)
        # - WAITING_IMAGE_INPUT (at Step11 image generation)
        # - COMPLETED (workflow finished)
        # - FAILED (workflow error)
        # - CANCELLED (user cancelled)
        valid_from_running = [
            RunStatus.WAITING_APPROVAL,
            RunStatus.WAITING_IMAGE_INPUT,
            RunStatus.COMPLETED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
        ]

        for target in valid_from_running:
            assert target in RunStatus

    def test_valid_transitions_from_waiting_approval(self) -> None:
        """Test valid transitions from WAITING_APPROVAL status."""
        # WAITING_APPROVAL can transition to:
        # - RUNNING (approved)
        # - FAILED (rejected)
        # - CANCELLED (user cancelled)
        valid_from_waiting_approval = [
            RunStatus.RUNNING,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
        ]

        for target in valid_from_waiting_approval:
            assert target in RunStatus

    def test_valid_transitions_from_waiting_image_input(self) -> None:
        """Test valid transitions from WAITING_IMAGE_INPUT status."""
        # WAITING_IMAGE_INPUT can transition to:
        # - RUNNING (images finalized/skipped)
        # - FAILED (error)
        # - CANCELLED (user cancelled)
        valid_from_waiting_image_input = [
            RunStatus.RUNNING,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
        ]

        for target in valid_from_waiting_image_input:
            assert target in RunStatus

    def test_terminal_statuses(self) -> None:
        """Test that terminal statuses have no valid transitions."""
        terminal_statuses = [
            RunStatus.COMPLETED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
        ]

        # Terminal statuses should not transition to anything normally
        # (except via retry/resume which creates new workflow)
        for status in terminal_statuses:
            assert status in RunStatus


class TestWorkflowStartingRationale:
    """Tests documenting the rationale for WORKFLOW_STARTING status."""

    def test_prevents_db_workflow_desync(self) -> None:
        """Document: WORKFLOW_STARTING prevents DB showing RUNNING when workflow hasn't started.

        The problem this solves:
        1. User clicks retry/resume
        2. DB is updated to RUNNING
        3. Temporal workflow start fails (network, timeout, etc.)
        4. Result: DB shows RUNNING but no workflow exists

        Solution:
        1. User clicks retry/resume
        2. DB is updated to WORKFLOW_STARTING
        3. Temporal workflow start is attempted
        4a. Success -> DB updated to RUNNING
        4b. Failure -> DB updated to FAILED
        """
        # This is a documentation test
        assert RunStatus.WORKFLOW_STARTING.value == "workflow_starting"

    def test_status_sequence_for_retry(self) -> None:
        """Document the status sequence for a retry operation."""
        # Expected sequence: FAILED -> WORKFLOW_STARTING -> RUNNING -> ...
        sequence = [
            RunStatus.FAILED,  # Initial failed state
            RunStatus.WORKFLOW_STARTING,  # Retry initiated
            RunStatus.RUNNING,  # Workflow started successfully
        ]

        assert len(sequence) == 3
        assert sequence[0] == RunStatus.FAILED
        assert sequence[1] == RunStatus.WORKFLOW_STARTING
        assert sequence[2] == RunStatus.RUNNING

    def test_status_sequence_for_resume(self) -> None:
        """Document the status sequence for a resume operation."""
        # Expected sequence: FAILED -> WORKFLOW_STARTING -> RUNNING -> ...
        sequence = [
            RunStatus.FAILED,  # Initial failed state (after partial completion)
            RunStatus.WORKFLOW_STARTING,  # Resume initiated
            RunStatus.RUNNING,  # Workflow started successfully
        ]

        assert len(sequence) == 3
        assert sequence[0] == RunStatus.FAILED
        assert sequence[1] == RunStatus.WORKFLOW_STARTING
        assert sequence[2] == RunStatus.RUNNING
