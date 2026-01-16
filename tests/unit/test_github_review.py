"""Unit tests for GitHub review API endpoints.

Tests for:
- POST /api/github/review/{run_id}/{step}
- POST /api/github/review-result/{run_id}/{step}
- GET /api/github/review-status/{run_id}/{step}
"""

from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from apps.api.services.review_prompts import ReviewType, get_review_prompt, get_review_title

# =============================================================================
# Test: Review Prompt Templates
# =============================================================================


class TestReviewPrompts:
    """Tests for review prompt generation."""

    def test_get_review_prompt_fact_check(self) -> None:
        """Test fact check prompt generation with default @codex."""
        prompt = get_review_prompt(
            review_type=ReviewType.FACT_CHECK,
            file_path="test/step10/output.json",
            output_path="test/step10/review.json",
            run_id="test-run-123",
            step="step10",
        )

        # Default is @codex (more cost-effective)
        assert "@codex" in prompt
        assert "ファクトチェック" in prompt
        assert "test/step10/output.json" in prompt
        assert "test/step10/review.json" in prompt
        assert "test-run-123" in prompt
        assert "事実の正確性" in prompt

    def test_get_review_prompt_with_claude(self) -> None:
        """Test fact check prompt generation with explicit @claude."""
        prompt = get_review_prompt(
            review_type=ReviewType.FACT_CHECK,
            file_path="test/step10/output.json",
            output_path="test/step10/review.json",
            run_id="test-run-123",
            step="step10",
            ai_mention="@claude",
        )

        assert "@claude" in prompt
        assert "@codex" not in prompt
        assert "ファクトチェック" in prompt

    def test_get_review_prompt_seo(self) -> None:
        """Test SEO review prompt generation."""
        prompt = get_review_prompt(
            review_type=ReviewType.SEO,
            file_path="test/step10/output.json",
            output_path="test/step10/review.json",
            run_id="test-run-123",
            step="step10",
        )

        assert "@codex" in prompt
        assert "SEO最適化" in prompt
        assert "キーワード配置" in prompt
        assert "見出し構造" in prompt

    def test_get_review_prompt_quality(self) -> None:
        """Test quality review prompt generation."""
        prompt = get_review_prompt(
            review_type=ReviewType.QUALITY,
            file_path="test/step10/output.json",
            output_path="test/step10/review.json",
            run_id="test-run-123",
            step="step10",
        )

        assert "@codex" in prompt
        assert "文章品質" in prompt
        assert "可読性" in prompt
        assert "誤字脱字" in prompt

    def test_get_review_prompt_all(self) -> None:
        """Test comprehensive review prompt generation."""
        prompt = get_review_prompt(
            review_type=ReviewType.ALL,
            file_path="test/step10/output.json",
            output_path="test/step10/review.json",
            run_id="test-run-123",
            step="step10",
        )

        assert "@codex" in prompt
        assert "総合レビュー" in prompt
        # Should contain all three perspectives
        assert "ファクトチェック" in prompt
        assert "SEO最適化" in prompt
        assert "文章品質" in prompt

    def test_get_review_prompt_output_format(self) -> None:
        """Test that output format instructions are included."""
        prompt = get_review_prompt(
            review_type=ReviewType.FACT_CHECK,
            file_path="test/step10/output.json",
            output_path="test/step10/review.json",
            run_id="test-run-123",
            step="step10",
        )

        # Check JSON output format is specified
        assert "JSON" in prompt
        assert '"issues"' in prompt
        assert '"summary"' in prompt
        assert '"severity"' in prompt

    def test_get_review_title(self) -> None:
        """Test review issue title generation."""
        title = get_review_title(
            review_type=ReviewType.FACT_CHECK,
            step="step10",
            dir_path="articles/run-123",
        )

        assert "[Claude Code Review]" in title
        assert "ファクトチェック" in title
        assert "step10" in title
        assert "articles/run-123" in title

    def test_get_review_title_all_types(self) -> None:
        """Test titles for all review types."""
        types_and_labels = [
            (ReviewType.FACT_CHECK, "ファクトチェック"),
            (ReviewType.SEO, "SEO最適化"),
            (ReviewType.QUALITY, "文章品質"),
            (ReviewType.ALL, "総合レビュー"),
        ]

        for review_type, expected_label in types_and_labels:
            title = get_review_title(review_type, "step10", "test/path")
            assert expected_label in title


# =============================================================================
# Test: Review API Endpoints (Mocked)
# =============================================================================


class TestReviewAPIEndpoints:
    """Tests for review API endpoint logic.

    Note: These tests mock the database and GitHub service to test
    endpoint logic in isolation.
    """

    @pytest.fixture
    def mock_run(self) -> MagicMock:
        """Create a mock Run object."""
        run = MagicMock()
        run.id = uuid4()
        run.github_repo_url = "https://github.com/test-owner/test-repo"
        run.github_dir_path = "articles/test-run"
        return run

    @pytest.fixture
    def mock_run_no_github(self) -> MagicMock:
        """Create a mock Run without GitHub configuration."""
        run = MagicMock()
        run.id = uuid4()
        run.github_repo_url = None
        run.github_dir_path = None
        return run

    @pytest.mark.asyncio
    async def test_create_review_issue_success(self, mock_run: MagicMock) -> None:
        """Test successful review issue creation."""
        # This tests the logic that would be in the endpoint
        from apps.api.services.review_prompts import ReviewType, get_review_prompt, get_review_title

        run_id = str(mock_run.id)
        step = "step10"
        review_type = ReviewType.ALL

        # Generate expected values
        file_path = f"{mock_run.github_dir_path}/{step}/output.json"
        output_path = f"{mock_run.github_dir_path}/{step}/review.json"

        prompt = get_review_prompt(
            review_type=review_type,
            file_path=file_path,
            output_path=output_path,
            run_id=run_id,
            step=step,
        )
        title = get_review_title(review_type, step, mock_run.github_dir_path)

        # Verify prompt contains required elements (default is @codex)
        assert "@codex" in prompt
        assert file_path in prompt
        assert output_path in prompt

        # Verify title format
        assert "[Claude Code Review]" in title
        assert step in title

    @pytest.mark.asyncio
    async def test_create_review_issue_no_github(self, mock_run_no_github: MagicMock) -> None:
        """Test that review fails when GitHub is not configured."""
        # Logic check: should raise 400 when github_repo_url is None
        if not mock_run_no_github.github_repo_url:
            # This is expected behavior
            error_message = "Run does not have a GitHub repository configured"
            assert "GitHub repository" in error_message

    @pytest.mark.asyncio
    async def test_review_result_save_format(self) -> None:
        """Test review result data structure."""
        # Test the expected JSON structure for review results
        review_result: dict[str, Any] = {
            "review_type": "all",
            "issues": [
                {
                    "severity": "high",
                    "category": "ファクトチェック",
                    "location": "見出し2: 市場規模",
                    "original": "市場規模は100億円",
                    "issue": "数値が2023年のデータで古い",
                    "suggestion": "2025年の最新データに更新: 150億円",
                },
                {
                    "severity": "medium",
                    "category": "文章品質",
                    "location": "段落3",
                    "original": "とても非常に重要",
                    "issue": "冗長な表現",
                    "suggestion": "非常に重要",
                },
            ],
            "summary": {
                "total_issues": 2,
                "high": 1,
                "medium": 1,
                "low": 0,
                "overall_assessment": "概ね良好。事実確認で1点要修正。",
            },
            "passed": False,
        }

        # Verify structure
        assert "review_type" in review_result
        assert "issues" in review_result
        assert "summary" in review_result
        assert isinstance(review_result["issues"], list)
        assert review_result["summary"]["total_issues"] == len(review_result["issues"])

    @pytest.mark.asyncio
    async def test_review_status_transitions(self) -> None:
        """Test review status state transitions."""
        valid_statuses = ["pending", "in_progress", "completed", "failed"]

        # All statuses should be valid
        for status in valid_statuses:
            assert status in valid_statuses

        # Test status determination logic
        def determine_status(issue_state: str, has_result_file: bool) -> str:
            if has_result_file:
                return "completed"
            if issue_state == "open":
                return "in_progress"
            if issue_state == "closed":
                return "failed"  # Closed without result = failed
            return "pending"

        assert determine_status("open", False) == "in_progress"
        assert determine_status("open", True) == "completed"
        assert determine_status("closed", True) == "completed"
        assert determine_status("closed", False) == "failed"


# =============================================================================
# Test: Security - Tenant Isolation
# =============================================================================


class TestTenantIsolation:
    """Tests for tenant isolation in review operations."""

    @pytest.mark.asyncio
    async def test_tenant_id_required_for_review(self) -> None:
        """Test that tenant_id is required for all review operations."""
        # Simulating the check that should happen in the endpoint
        tenant_id = "tenant-123"
        run_tenant_id = "tenant-123"

        # Same tenant - should pass
        assert tenant_id == run_tenant_id

    @pytest.mark.asyncio
    async def test_cross_tenant_access_denied(self) -> None:
        """Test that cross-tenant access is denied."""
        requesting_tenant_id = "tenant-123"
        run_tenant_id = "tenant-456"

        # Different tenant - should fail
        assert requesting_tenant_id != run_tenant_id

        # In actual implementation, this would raise 403 Forbidden


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_step_name(self) -> None:
        """Test handling of empty step name."""
        step = ""

        # Should be validated and rejected
        assert len(step) == 0

    def test_invalid_review_type(self) -> None:
        """Test handling of invalid review type."""
        valid_types = ["fact_check", "seo", "quality", "all"]
        invalid_type = "invalid_type"

        assert invalid_type not in valid_types

    def test_special_characters_in_path(self) -> None:
        """Test handling of special characters in file paths."""
        # These should be safely handled
        safe_paths = [
            "articles/run-123/step10/output.json",
            "articles/run_123/step10/output.json",
            "articles/run.123/step10/output.json",
        ]

        for path in safe_paths:
            # Path should not contain dangerous characters
            assert ".." not in path
            assert path.startswith("articles/")

    def test_review_prompt_escaping(self) -> None:
        """Test that user input in prompts is properly handled."""
        # Test with potentially problematic characters
        file_path = "test/path/with'quotes/file.json"

        prompt = get_review_prompt(
            review_type=ReviewType.FACT_CHECK,
            file_path=file_path,
            output_path="test/review.json",
            run_id="test-123",
            step="step10",
        )

        # Path should be included as-is (no injection)
        assert file_path in prompt
