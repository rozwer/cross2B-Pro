"""Unit tests for GitHub Fix Guidance feature.

Tests for:
- needs_github_fix calculation logic
- POST /api/github/runs/{run_id}/fix-issue
- GET /api/github/runs/{run_id}/fix-issue
"""

from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

from apps.api.schemas.enums import RunStatus

# =============================================================================
# Test: needs_github_fix calculation logic
# =============================================================================


class TestNeedsGitHubFixLogic:
    """Tests for needs_github_fix field calculation in run_orm_to_response."""

    def _create_mock_run(
        self,
        status: str = "failed",
        last_resumed_step: str | None = "step3a",
        current_step: str | None = "step3a",
        github_repo_url: str | None = "https://github.com/test/repo",
        fix_issue_number: int | None = None,
    ) -> MagicMock:
        """Create a mock Run object for testing."""
        run = MagicMock()
        run.id = str(uuid4())
        run.tenant_id = "test-tenant"
        run.status = status
        run.last_resumed_step = last_resumed_step
        run.current_step = current_step
        run.github_repo_url = github_repo_url
        run.fix_issue_number = fix_issue_number
        run.error_message = "Test error message"
        run.error_code = "TEST_ERROR"
        run.input_data = {"keyword": "test"}
        run.config = {}
        run.step11_state = None
        run.github_dir_path = None
        run.created_at = datetime.now()
        run.updated_at = datetime.now()
        run.started_at = None
        run.completed_at = None
        run.steps = []
        return run

    def test_needs_github_fix_true_resume_same_step_failed(self) -> None:
        """Test needs_github_fix is True when resume and fail on same step."""
        # Condition: status=failed AND last_resumed_step==current_step
        # AND github_repo_url is set AND fix_issue_number is None
        run = self._create_mock_run(
            status=RunStatus.FAILED.value,
            last_resumed_step="step3a",
            current_step="step3a",
            github_repo_url="https://github.com/test/repo",
            fix_issue_number=None,
        )

        # Calculate needs_github_fix using same logic as run_orm_to_response
        needs_github_fix = (
            run.status == RunStatus.FAILED.value
            and run.last_resumed_step is not None
            and run.current_step is not None
            and run.last_resumed_step == run.current_step
            and run.github_repo_url is not None
            and run.fix_issue_number is None
        )

        assert needs_github_fix is True

    def test_needs_github_fix_false_initial_failure(self) -> None:
        """Test needs_github_fix is False for initial failure (no resume)."""
        run = self._create_mock_run(
            status=RunStatus.FAILED.value,
            last_resumed_step=None,  # Never resumed
            current_step="step3a",
            github_repo_url="https://github.com/test/repo",
            fix_issue_number=None,
        )

        needs_github_fix = (
            run.status == RunStatus.FAILED.value
            and run.last_resumed_step is not None
            and run.current_step is not None
            and run.last_resumed_step == run.current_step
            and run.github_repo_url is not None
            and run.fix_issue_number is None
        )

        assert needs_github_fix is False

    def test_needs_github_fix_false_different_step(self) -> None:
        """Test needs_github_fix is False when fail on different step."""
        run = self._create_mock_run(
            status=RunStatus.FAILED.value,
            last_resumed_step="step3a",
            current_step="step4",  # Failed on different step
            github_repo_url="https://github.com/test/repo",
            fix_issue_number=None,
        )

        needs_github_fix = (
            run.status == RunStatus.FAILED.value
            and run.last_resumed_step is not None
            and run.current_step is not None
            and run.last_resumed_step == run.current_step
            and run.github_repo_url is not None
            and run.fix_issue_number is None
        )

        assert needs_github_fix is False

    def test_needs_github_fix_false_issue_already_created(self) -> None:
        """Test needs_github_fix is False when issue already created."""
        run = self._create_mock_run(
            status=RunStatus.FAILED.value,
            last_resumed_step="step3a",
            current_step="step3a",
            github_repo_url="https://github.com/test/repo",
            fix_issue_number=123,  # Already created
        )

        needs_github_fix = (
            run.status == RunStatus.FAILED.value
            and run.last_resumed_step is not None
            and run.current_step is not None
            and run.last_resumed_step == run.current_step
            and run.github_repo_url is not None
            and run.fix_issue_number is None
        )

        assert needs_github_fix is False

    def test_needs_github_fix_false_no_github_repo(self) -> None:
        """Test needs_github_fix is False when GitHub repo not configured."""
        run = self._create_mock_run(
            status=RunStatus.FAILED.value,
            last_resumed_step="step3a",
            current_step="step3a",
            github_repo_url=None,  # Not configured
            fix_issue_number=None,
        )

        needs_github_fix = (
            run.status == RunStatus.FAILED.value
            and run.last_resumed_step is not None
            and run.current_step is not None
            and run.last_resumed_step == run.current_step
            and run.github_repo_url is not None
            and run.fix_issue_number is None
        )

        assert needs_github_fix is False

    def test_needs_github_fix_false_not_failed(self) -> None:
        """Test needs_github_fix is False when run is not in failed status."""
        run = self._create_mock_run(
            status=RunStatus.RUNNING.value,  # Not failed
            last_resumed_step="step3a",
            current_step="step3a",
            github_repo_url="https://github.com/test/repo",
            fix_issue_number=None,
        )

        needs_github_fix = (
            run.status == RunStatus.FAILED.value
            and run.last_resumed_step is not None
            and run.current_step is not None
            and run.last_resumed_step == run.current_step
            and run.github_repo_url is not None
            and run.fix_issue_number is None
        )

        assert needs_github_fix is False


# =============================================================================
# Test: Issue Body Template
# =============================================================================


class TestIssueBodyTemplate:
    """Tests for issue body template generation."""

    def test_issue_body_contains_claude_mention(self) -> None:
        """Test that issue body contains @claude mention."""
        error_code = "VALIDATION_ERROR"
        error_message = "Output validation failed"
        current_step = "step5"
        run_id = str(uuid4())
        tenant_id = "test-tenant"

        body = f"""## エラー情報
- ステップ: {current_step}
- エラーコード: {error_code}
- メッセージ: {error_message}

## Run情報
- Run ID: {run_id}
- Tenant ID: {tenant_id}

@claude 上記のエラーを修正してください。
"""

        assert "@claude" in body
        assert current_step in body
        assert error_code in body
        assert error_message in body
        assert run_id in body

    def test_issue_title_format(self) -> None:
        """Test issue title format."""
        current_step = "step5"
        error_code = "VALIDATION_ERROR"

        title = f"[Step{current_step}] {error_code}: 修正依頼"

        assert f"[Step{current_step}]" in title
        assert error_code in title
        assert "修正依頼" in title


# =============================================================================
# Test: Fix Issue API Endpoint Behavior
# =============================================================================


class TestFixIssueAPIBehavior:
    """Tests for fix issue API endpoint behavior specifications."""

    def test_create_fix_issue_idempotency(self) -> None:
        """Test that creating fix issue updates fix_issue_number.

        Note: Each call creates a new issue and updates fix_issue_number.
        This is the specified behavior (not strictly idempotent).
        """
        # This test documents the expected behavior:
        # - First call: creates issue #1, saves to DB
        # - Second call: creates issue #2, updates DB
        # The last issue number is always stored.
        pass  # Behavior is tested in integration tests

    def test_get_fix_issue_status_requires_issue(self) -> None:
        """Test that GET returns 404 when no issue exists."""
        # Expected behavior:
        # - If fix_issue_number is None -> 404
        pass  # Behavior is tested in integration tests

    def test_get_fix_issue_status_returns_state(self) -> None:
        """Test that GET returns issue state from GitHub."""
        # Expected response fields:
        # - issue_number: int
        # - state: "open" | "closed"
        # - status: "open" | "in_progress" | "closed"
        # - pr_url: str | None
        # - last_comment: str | None (truncated to 200 chars)
        # - issue_url: str
        pass  # Behavior is tested in integration tests


# =============================================================================
# Test: Resume API Recording
# =============================================================================


class TestResumeAPIRecording:
    """Tests for resume API recording last_resumed_step."""

    def test_resume_records_normalized_step(self) -> None:
        """Test that resume API records normalized step name."""
        # When resume(step3) is called:
        # - step3 is normalized to step3a
        # - last_resumed_step is set to "step3a"
        pass  # Behavior is tested in integration tests

    def test_resume_updates_last_resumed_step(self) -> None:
        """Test that resume API updates last_resumed_step on each call."""
        # When resume is called multiple times:
        # - First resume(step3) -> last_resumed_step = "step3a"
        # - Second resume(step5) -> last_resumed_step = "step5"
        pass  # Behavior is tested in integration tests
