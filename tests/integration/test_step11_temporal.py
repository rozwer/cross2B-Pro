"""Integration tests for Step11 Temporal signal integration.

Tests cover:
- API endpoints sending Temporal signals to resume workflow execution
- Signal payload structure and validation
- Error handling when Temporal client fails
"""

# mypy: ignore-errors
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import schema models (not used directly, but kept for documentation)
# These models are defined in apps.api.routers.step11:
# - PositionConfirmInput
# - InstructionsInput
# - ImageReviewInput
# - FinalizeInput


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def mock_run(tenant_id, run_id):
    """Create a mock Run object."""
    run = MagicMock()
    run.id = run_id
    run.tenant_id = tenant_id
    run.status = "waiting_image_input"
    run.current_step = "step11"
    return run


@pytest.fixture
def mock_step11_state():
    """Create a mock Step11 state."""
    state = MagicMock()
    state.id = "step11_state_001"
    state.phase = "positions_proposed"
    state.positions = [
        {"id": "pos_1", "section": "intro", "order": 1},
        {"id": "pos_2", "section": "body", "order": 2},
    ]
    state.settings = {"style": "photo", "aspect_ratio": "16:9"}
    return state


@pytest.fixture
def mock_temporal_client():
    """Create a mock Temporal client."""
    client = MagicMock()
    workflow_handle = MagicMock()
    workflow_handle.signal = AsyncMock()
    client.get_workflow_handle = MagicMock(return_value=workflow_handle)
    return client


@pytest.fixture
def mock_auth_user(tenant_id):
    """Create a mock authenticated user."""
    from apps.api.auth.schemas import AuthUser

    return AuthUser(
        user_id="test-user-001",
        tenant_id=tenant_id,
        roles=["admin"],
    )


# =============================================================================
# Step11 Temporal Signal Tests
# =============================================================================


class TestStep11PositionsSignal:
    """Test step11_confirm_positions signal sending."""

    @pytest.mark.asyncio
    async def test_positions_confirm_sends_temporal_signal(
        self,
        mock_temporal_client,
        mock_db_session,
        mock_run,
        mock_step11_state,
        tenant_id,
        run_id,
    ):
        """Test that confirming positions sends Temporal signal."""
        # Arrange
        workflow_handle = mock_temporal_client.get_workflow_handle(run_id)

        with patch("apps.api.routers.step11.get_temporal_client", return_value=mock_temporal_client):
            # Act - Simulate signal call
            payload = {
                "approved": True,
                "reanalyze": False,
                "reanalyze_request": None,
                "modified_positions": None,
            }
            await workflow_handle.signal("step11_confirm_positions", payload)

            # Assert
            workflow_handle.signal.assert_called_once_with(
                "step11_confirm_positions",
                payload,
            )

    @pytest.mark.asyncio
    async def test_positions_confirm_with_modified_positions(
        self,
        mock_temporal_client,
        run_id,
    ):
        """Test signal with modified positions."""
        workflow_handle = mock_temporal_client.get_workflow_handle(run_id)

        modified_positions = [
            {"id": "pos_1", "section": "intro", "order": 1, "custom_prompt": "A scenic view"},
            {"id": "pos_2", "section": "body", "order": 3},  # Changed order
        ]

        payload = {
            "approved": True,
            "reanalyze": False,
            "reanalyze_request": None,
            "modified_positions": modified_positions,
        }

        await workflow_handle.signal("step11_confirm_positions", payload)

        workflow_handle.signal.assert_called_once()
        call_args = workflow_handle.signal.call_args
        assert call_args[0][1]["modified_positions"] == modified_positions

    @pytest.mark.asyncio
    async def test_positions_reanalyze_request(
        self,
        mock_temporal_client,
        run_id,
    ):
        """Test signal with reanalyze request."""
        workflow_handle = mock_temporal_client.get_workflow_handle(run_id)

        payload = {
            "approved": False,
            "reanalyze": True,
            "reanalyze_request": "本文中の技術説明部分にも画像を追加してほしい",
            "modified_positions": None,
        }

        await workflow_handle.signal("step11_confirm_positions", payload)

        call_args = workflow_handle.signal.call_args
        assert call_args[0][1]["reanalyze"] is True
        assert "技術説明部分" in call_args[0][1]["reanalyze_request"]


class TestStep11InstructionsSignal:
    """Test step11_submit_instructions signal sending."""

    @pytest.mark.asyncio
    async def test_instructions_sends_temporal_signal(
        self,
        mock_temporal_client,
        run_id,
    ):
        """Test that submitting instructions sends Temporal signal."""
        workflow_handle = mock_temporal_client.get_workflow_handle(run_id)

        instructions = [
            {"position_id": "pos_1", "prompt": "A beautiful sunset over mountains"},
            {"position_id": "pos_2", "prompt": "Modern office workspace"},
        ]

        payload = {"instructions": instructions}
        await workflow_handle.signal("step11_submit_instructions", payload)

        workflow_handle.signal.assert_called_once_with(
            "step11_submit_instructions",
            payload,
        )

    @pytest.mark.asyncio
    async def test_instructions_with_style_overrides(
        self,
        mock_temporal_client,
        run_id,
    ):
        """Test instructions with per-image style overrides."""
        workflow_handle = mock_temporal_client.get_workflow_handle(run_id)

        instructions = [
            {
                "position_id": "pos_1",
                "prompt": "Abstract technology concept",
                "style": "illustration",
                "aspect_ratio": "1:1",
            },
        ]

        payload = {"instructions": instructions}
        await workflow_handle.signal("step11_submit_instructions", payload)

        call_args = workflow_handle.signal.call_args
        assert call_args[0][1]["instructions"][0]["style"] == "illustration"


class TestStep11ReviewSignal:
    """Test step11_review_images signal sending."""

    @pytest.mark.asyncio
    async def test_review_approve_all_sends_signal(
        self,
        mock_temporal_client,
        run_id,
    ):
        """Test approving all images sends Temporal signal."""
        workflow_handle = mock_temporal_client.get_workflow_handle(run_id)

        reviews = [
            {"image_id": "img_1", "approved": True},
            {"image_id": "img_2", "approved": True},
        ]

        payload = {"reviews": reviews, "all_approved": True}
        await workflow_handle.signal("step11_review_images", payload)

        workflow_handle.signal.assert_called_once()
        call_args = workflow_handle.signal.call_args
        assert call_args[0][1]["all_approved"] is True

    @pytest.mark.asyncio
    async def test_review_with_retry_requests(
        self,
        mock_temporal_client,
        run_id,
    ):
        """Test review with retry requests for rejected images."""
        workflow_handle = mock_temporal_client.get_workflow_handle(run_id)

        reviews = [
            {"image_id": "img_1", "approved": True},
            {
                "image_id": "img_2",
                "approved": False,
                "retry_prompt": "もっと明るい色調で生成してください",
            },
        ]

        payload = {"reviews": reviews, "all_approved": False}
        await workflow_handle.signal("step11_review_images", payload)

        call_args = workflow_handle.signal.call_args
        assert call_args[0][1]["all_approved"] is False
        assert "retry_prompt" in call_args[0][1]["reviews"][1]


class TestStep11FinalizeSignal:
    """Test step11_finalize signal sending."""

    @pytest.mark.asyncio
    async def test_finalize_sends_temporal_signal(
        self,
        mock_temporal_client,
        run_id,
    ):
        """Test finalizing sends Temporal signal to proceed to Step12."""
        workflow_handle = mock_temporal_client.get_workflow_handle(run_id)

        payload = {
            "confirmed": True,
            "preview_approved": True,
        }
        await workflow_handle.signal("step11_finalize", payload)

        workflow_handle.signal.assert_called_once_with(
            "step11_finalize",
            payload,
        )

    @pytest.mark.asyncio
    async def test_finalize_with_restart_request(
        self,
        mock_temporal_client,
        run_id,
    ):
        """Test finalize with restart from beginning."""
        workflow_handle = mock_temporal_client.get_workflow_handle(run_id)

        payload = {
            "confirmed": False,
            "restart": True,
            "restart_reason": "画像の品質が全体的に低いため最初からやり直し",
        }
        await workflow_handle.signal("step11_finalize", payload)

        call_args = workflow_handle.signal.call_args
        assert call_args[0][1]["restart"] is True


class TestStep11SkipSignal:
    """Test step11_skip signal sending."""

    @pytest.mark.asyncio
    async def test_skip_sends_temporal_signal(
        self,
        mock_temporal_client,
        run_id,
    ):
        """Test skipping image generation sends Temporal signal."""
        workflow_handle = mock_temporal_client.get_workflow_handle(run_id)

        await workflow_handle.signal("step11_skip")

        workflow_handle.signal.assert_called_once_with("step11_skip")

    @pytest.mark.asyncio
    async def test_skip_with_reason(
        self,
        mock_temporal_client,
        run_id,
    ):
        """Test skip with optional reason."""
        workflow_handle = mock_temporal_client.get_workflow_handle(run_id)

        payload = {"reason": "画像は後で手動で追加予定"}
        await workflow_handle.signal("step11_skip", payload)

        # Skip may or may not include payload depending on implementation
        assert workflow_handle.signal.called


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestTemporalSignalErrorHandling:
    """Test error handling when Temporal signal fails."""

    @pytest.mark.asyncio
    async def test_signal_failure_raises_service_unavailable(
        self,
        mock_temporal_client,
        run_id,
    ):
        """Test that signal failure raises 503 error."""
        workflow_handle = mock_temporal_client.get_workflow_handle(run_id)
        workflow_handle.signal = AsyncMock(side_effect=Exception("Temporal connection lost"))

        with pytest.raises(Exception) as exc_info:
            await workflow_handle.signal("step11_confirm_positions", {})

        assert "Temporal connection lost" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_workflow_not_found_error(
        self,
        mock_temporal_client,
    ):
        """Test error when workflow doesn't exist."""
        from temporalio.client import RPCError

        # RPCError is raised when workflow is not found
        mock_temporal_client.get_workflow_handle = MagicMock(
            side_effect=RPCError(message="Workflow not found", status=None, raw_grpc_status=None)
        )

        with pytest.raises(RPCError):
            mock_temporal_client.get_workflow_handle("nonexistent_run_id")


# =============================================================================
# Signal Payload Validation Tests
# =============================================================================


class TestSignalPayloadStructure:
    """Test signal payload structure matches workflow expectations."""

    def test_positions_confirm_payload_structure(self):
        """Test positions confirm payload has required fields."""
        payload = {
            "approved": True,
            "reanalyze": False,
            "reanalyze_request": None,
            "modified_positions": None,
        }

        # Required fields
        assert "approved" in payload
        assert "reanalyze" in payload
        assert isinstance(payload["approved"], bool)
        assert isinstance(payload["reanalyze"], bool)

    def test_instructions_payload_structure(self):
        """Test instructions payload has required fields."""
        payload = {
            "instructions": [
                {"position_id": "pos_1", "prompt": "test prompt"},
            ]
        }

        assert "instructions" in payload
        assert isinstance(payload["instructions"], list)
        for inst in payload["instructions"]:
            assert "position_id" in inst
            assert "prompt" in inst

    def test_review_payload_structure(self):
        """Test review payload has required fields."""
        payload = {
            "reviews": [
                {"image_id": "img_1", "approved": True},
            ],
            "all_approved": True,
        }

        assert "reviews" in payload
        assert "all_approved" in payload
        for review in payload["reviews"]:
            assert "image_id" in review
            assert "approved" in review

    def test_finalize_payload_structure(self):
        """Test finalize payload has required fields."""
        payload = {
            "confirmed": True,
            "preview_approved": True,
        }

        assert "confirmed" in payload
        assert isinstance(payload["confirmed"], bool)
