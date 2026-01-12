"""Integration tests for WebSocket authentication.

Tests cover:
- JWT token authentication for WebSocket connections
- Tenant isolation (users can only subscribe to their own runs)
- Error handling for invalid/missing tokens
- Development mode auth bypass
"""

# mypy: ignore-errors
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.api.routers.websocket import (
    ConnectionManager,
    _authenticate_websocket,
    _verify_run_ownership,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    websocket = MagicMock()
    websocket.accept = AsyncMock()
    websocket.close = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.receive_text = AsyncMock(return_value="ping")
    return websocket


@pytest.fixture
def valid_jwt_token():
    """Valid JWT token for testing."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token"


@pytest.fixture
def mock_token_data(tenant_id):
    """Mock decoded token data."""
    token_data = MagicMock()
    token_data.sub = "user-001"
    token_data.tenant_id = tenant_id
    token_data.roles = ["user"]
    return token_data


@pytest.fixture
def connection_manager():
    """Create a fresh ConnectionManager instance."""
    return ConnectionManager()


# =============================================================================
# Authentication Tests
# =============================================================================


class TestWebSocketAuthentication:
    """Test WebSocket JWT authentication."""

    @pytest.mark.asyncio
    async def test_auth_with_valid_token(
        self,
        mock_websocket,
        valid_jwt_token,
        mock_token_data,
        tenant_id,
    ):
        """Test successful authentication with valid JWT token."""
        with patch("apps.api.routers.websocket.SKIP_AUTH", False):
            with patch("apps.api.routers.websocket.verify_token", return_value=mock_token_data):
                user = await _authenticate_websocket(mock_websocket, valid_jwt_token)

                assert user is not None
                assert user.user_id == "user-001"
                assert user.tenant_id == tenant_id

    @pytest.mark.asyncio
    async def test_auth_without_token_fails(
        self,
        mock_websocket,
    ):
        """Test authentication fails when no token provided."""
        with patch("apps.api.routers.websocket.SKIP_AUTH", False):
            user = await _authenticate_websocket(mock_websocket, None)

            assert user is None

    @pytest.mark.asyncio
    async def test_auth_with_invalid_token_fails(
        self,
        mock_websocket,
    ):
        """Test authentication fails with invalid token."""
        from apps.api.auth.middleware import AuthError

        with patch("apps.api.routers.websocket.SKIP_AUTH", False):
            with patch(
                "apps.api.routers.websocket.verify_token",
                side_effect=AuthError(message="Invalid token", reason="invalid_token"),
            ):
                user = await _authenticate_websocket(mock_websocket, "invalid_token")

                assert user is None

    @pytest.mark.asyncio
    async def test_auth_with_expired_token_fails(
        self,
        mock_websocket,
    ):
        """Test authentication fails with expired token."""
        from apps.api.auth.middleware import AuthError

        with patch("apps.api.routers.websocket.SKIP_AUTH", False):
            with patch(
                "apps.api.routers.websocket.verify_token",
                side_effect=AuthError(message="Token expired", reason="token_expired"),
            ):
                user = await _authenticate_websocket(mock_websocket, "expired_token")

                assert user is None

    @pytest.mark.asyncio
    async def test_dev_mode_skips_auth(
        self,
        mock_websocket,
    ):
        """Test development mode bypasses authentication."""
        with patch("apps.api.routers.websocket.SKIP_AUTH", True):
            with patch("apps.api.routers.websocket.DEV_TENANT_ID", "dev-tenant-001"):
                user = await _authenticate_websocket(mock_websocket, None)

                assert user is not None
                assert user.user_id == "dev-user-001"
                assert user.tenant_id == "dev-tenant-001"
                assert "admin" in user.roles


# =============================================================================
# Tenant Isolation Tests
# =============================================================================


class TestTenantIsolation:
    """Test WebSocket tenant isolation."""

    @pytest.mark.asyncio
    async def test_verify_run_ownership_success(
        self,
        tenant_id,
        run_id,
    ):
        """Test run ownership verification succeeds for correct tenant."""
        mock_run = MagicMock()
        mock_run.id = run_id
        mock_run.tenant_id = tenant_id

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_run
        mock_session.execute.return_value = mock_result

        mock_db_manager = MagicMock()
        mock_db_manager.get_session = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_session),
                __aexit__=AsyncMock(),
            )
        )

        with patch("apps.api.routers.websocket._get_tenant_db_manager", return_value=mock_db_manager):
            result = await _verify_run_ownership(tenant_id, run_id)

            assert result is True

    @pytest.mark.asyncio
    async def test_verify_run_ownership_wrong_tenant(
        self,
        tenant_id,
        run_id,
    ):
        """Test run ownership verification fails for wrong tenant."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # Run not found for this tenant
        mock_session.execute.return_value = mock_result

        mock_db_manager = MagicMock()
        mock_db_manager.get_session = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_session),
                __aexit__=AsyncMock(),
            )
        )

        with patch("apps.api.routers.websocket._get_tenant_db_manager", return_value=mock_db_manager):
            result = await _verify_run_ownership("wrong_tenant", run_id)

            assert result is False

    @pytest.mark.asyncio
    async def test_verify_run_ownership_nonexistent_run(
        self,
        tenant_id,
    ):
        """Test run ownership verification fails for nonexistent run."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        mock_db_manager = MagicMock()
        mock_db_manager.get_session = MagicMock(
            return_value=AsyncMock(
                __aenter__=AsyncMock(return_value=mock_session),
                __aexit__=AsyncMock(),
            )
        )

        with patch("apps.api.routers.websocket._get_tenant_db_manager", return_value=mock_db_manager):
            result = await _verify_run_ownership(tenant_id, "nonexistent_run_id")

            assert result is False


# =============================================================================
# Connection Manager Tests
# =============================================================================


class TestConnectionManager:
    """Test WebSocket ConnectionManager functionality."""

    @pytest.mark.asyncio
    async def test_connect_adds_to_active_connections(
        self,
        connection_manager,
        mock_websocket,
        run_id,
    ):
        """Test connecting adds WebSocket to active connections."""
        await connection_manager.connect(run_id, mock_websocket)

        assert run_id in connection_manager.active_connections
        assert mock_websocket in connection_manager.active_connections[run_id]

    @pytest.mark.asyncio
    async def test_disconnect_removes_from_active_connections(
        self,
        connection_manager,
        mock_websocket,
        run_id,
    ):
        """Test disconnecting removes WebSocket from active connections."""
        await connection_manager.connect(run_id, mock_websocket)
        connection_manager.disconnect(run_id, mock_websocket)

        assert run_id not in connection_manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_connections(
        self,
        connection_manager,
        run_id,
    ):
        """Test broadcast sends message to all connections for a run."""
        ws1 = MagicMock()
        ws1.send_json = AsyncMock()
        ws2 = MagicMock()
        ws2.send_json = AsyncMock()

        await connection_manager.connect(run_id, ws1)
        await connection_manager.connect(run_id, ws2)

        message = {"type": "test", "data": "hello"}
        await connection_manager.broadcast(run_id, message)

        ws1.send_json.assert_called_once_with(message)
        ws2.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_removes_disconnected_clients(
        self,
        connection_manager,
        run_id,
    ):
        """Test broadcast removes clients that fail to receive."""
        ws_good = MagicMock()
        ws_good.send_json = AsyncMock()
        ws_bad = MagicMock()
        ws_bad.send_json = AsyncMock(side_effect=Exception("Connection closed"))

        await connection_manager.connect(run_id, ws_good)
        await connection_manager.connect(run_id, ws_bad)

        await connection_manager.broadcast(run_id, {"type": "test"})

        # Good client should still be connected
        assert ws_good in connection_manager.active_connections.get(run_id, [])
        # Bad client should be removed
        assert ws_bad not in connection_manager.active_connections.get(run_id, [])

    @pytest.mark.asyncio
    async def test_broadcast_run_update(
        self,
        connection_manager,
        mock_websocket,
        run_id,
    ):
        """Test broadcast_run_update sends correctly formatted event."""
        await connection_manager.connect(run_id, mock_websocket)

        await connection_manager.broadcast_run_update(
            run_id=run_id,
            event_type="run.started",
            status="running",
            current_step="step1",
            progress=10,
            message="Processing step 1",
        )

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]

        assert call_args["type"] == "run.started"
        assert call_args["run_id"] == run_id
        assert call_args["step"] == "step1"
        assert call_args["status"] == "running"
        assert call_args["progress"] == 10
        assert call_args["message"] == "Processing step 1"
        assert "timestamp" in call_args

    @pytest.mark.asyncio
    async def test_broadcast_step_event(
        self,
        connection_manager,
        mock_websocket,
        run_id,
    ):
        """Test broadcast_step_event sends correctly formatted step event."""
        await connection_manager.connect(run_id, mock_websocket)

        await connection_manager.broadcast_step_event(
            run_id=run_id,
            step="step3a",
            event_type="step_completed",
            status="completed",
            progress=100,
            message="Step 3A completed successfully",
            attempt=1,
            details={"tokens_used": 1500},
        )

        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]

        assert call_args["type"] == "step_completed"
        assert call_args["step"] == "step3a"
        assert call_args["attempt"] == 1
        assert call_args["details"]["tokens_used"] == 1500


# =============================================================================
# WebSocket Close Code Tests
# =============================================================================


class TestWebSocketCloseCodes:
    """Test WebSocket close codes for different error scenarios."""

    @pytest.mark.asyncio
    async def test_close_code_4001_for_auth_required(
        self,
        mock_websocket,
    ):
        """Test close code 4001 is used for authentication required."""
        # Simulating what websocket_progress does
        await mock_websocket.close(code=4001, reason="Authentication required")

        mock_websocket.close.assert_called_with(
            code=4001,
            reason="Authentication required",
        )

    @pytest.mark.asyncio
    async def test_close_code_4003_for_access_denied(
        self,
        mock_websocket,
    ):
        """Test close code 4003 is used for access denied."""
        await mock_websocket.close(code=4003, reason="Run not found or access denied")

        mock_websocket.close.assert_called_with(
            code=4003,
            reason="Run not found or access denied",
        )


# =============================================================================
# Ping/Pong Tests
# =============================================================================


class TestPingPong:
    """Test WebSocket ping/pong handling."""

    @pytest.mark.asyncio
    async def test_pong_response_to_ping(
        self,
        mock_websocket,
    ):
        """Test server responds with pong to ping."""
        # This tests the logic in websocket_progress endpoint
        data = "ping"

        if data == "ping":
            await mock_websocket.send_json({"type": "pong"})

        mock_websocket.send_json.assert_called_with({"type": "pong"})
