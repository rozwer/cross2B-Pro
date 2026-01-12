"""WebSocket router.

Handles WebSocket connections for real-time progress streaming.
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from apps.api.auth.middleware import DEV_TENANT_ID, SKIP_AUTH, AuthError, verify_token
from apps.api.auth.schemas import AuthUser

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


# =============================================================================
# Connection Manager
# =============================================================================


class ConnectionManager:
    """WebSocket connection manager for real-time updates with tenant isolation."""

    def __init__(self) -> None:
        # Structure: {tenant_id: {run_id: [websockets]}}
        self.active_connections: dict[str, dict[str, list[WebSocket]]] = {}
        # Legacy structure for backward compatibility during transition
        self._legacy_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, run_id: str, websocket: WebSocket, tenant_id: str | None = None) -> None:
        """Track a WebSocket connection (acceptは呼び出し側で実施済み).

        Args:
            run_id: Run identifier
            websocket: WebSocket connection
            tenant_id: Tenant identifier for isolation (required for secure connections)
        """
        if tenant_id:
            # Tenant-isolated storage
            if tenant_id not in self.active_connections:
                self.active_connections[tenant_id] = {}
            if run_id not in self.active_connections[tenant_id]:
                self.active_connections[tenant_id][run_id] = []
            self.active_connections[tenant_id][run_id].append(websocket)
            logger.info("WebSocket connected", extra={"run_id": run_id, "tenant_id": tenant_id})
        else:
            # Legacy mode (backward compatibility)
            if run_id not in self._legacy_connections:
                self._legacy_connections[run_id] = []
            self._legacy_connections[run_id].append(websocket)
            logger.info("WebSocket connected (legacy)", extra={"run_id": run_id})

    def disconnect(self, run_id: str, websocket: WebSocket, tenant_id: str | None = None) -> None:
        """Remove a WebSocket connection."""
        if tenant_id and tenant_id in self.active_connections:
            if run_id in self.active_connections[tenant_id]:
                if websocket in self.active_connections[tenant_id][run_id]:
                    self.active_connections[tenant_id][run_id].remove(websocket)
                if not self.active_connections[tenant_id][run_id]:
                    del self.active_connections[tenant_id][run_id]
            if not self.active_connections[tenant_id]:
                del self.active_connections[tenant_id]
            logger.info("WebSocket disconnected", extra={"run_id": run_id, "tenant_id": tenant_id})
        elif run_id in self._legacy_connections:
            # Legacy mode
            if websocket in self._legacy_connections[run_id]:
                self._legacy_connections[run_id].remove(websocket)
            if not self._legacy_connections[run_id]:
                del self._legacy_connections[run_id]
            logger.info("WebSocket disconnected (legacy)", extra={"run_id": run_id})

    async def broadcast(self, run_id: str, message: dict[str, Any], tenant_id: str | None = None) -> None:
        """Broadcast message to all connections for a run.

        Args:
            run_id: Run identifier
            message: Message to broadcast
            tenant_id: Tenant identifier for isolation (when provided, only broadcasts to tenant-specific connections)
        """
        connections: list[WebSocket] = []

        if tenant_id and tenant_id in self.active_connections:
            # Tenant-isolated broadcast
            connections = self.active_connections[tenant_id].get(run_id, [])
        elif run_id in self._legacy_connections:
            # Legacy mode fallback
            connections = self._legacy_connections.get(run_id, [])

        if connections:
            disconnected = []
            for websocket in connections:
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.append(websocket)
            for ws in disconnected:
                self.disconnect(run_id, ws, tenant_id)

    async def broadcast_run_update(
        self,
        run_id: str,
        event_type: str,
        status: str,
        current_step: str | None = None,
        error: dict[str, Any] | None = None,
        progress: int = 0,
        message: str = "",
    ) -> None:
        """Broadcast a run status update event.

        Args:
            run_id: The run ID to broadcast to
            event_type: Event type (e.g., 'run.started', 'run.approved', 'step_completed')
            status: Current run status
            current_step: Current step name if applicable
            error: Error details if applicable
            progress: Progress percentage (0-100), default 0
            message: Human-readable status message, default empty
        """
        # Match frontend ProgressEvent type for consistency
        event_message: dict[str, Any] = {
            "type": event_type,
            "run_id": run_id,
            "step": current_step,  # FE expects 'step' field
            "status": status,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        if error:
            event_message["error"] = error
            event_message["details"] = error  # FE may also look for 'details'
        await self.broadcast(run_id, event_message)

    async def broadcast_step_event(
        self,
        run_id: str,
        step: str,
        event_type: str,
        status: str,
        progress: int = 0,
        message: str = "",
        attempt: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Broadcast a step-level event.

        Args:
            run_id: The run ID to broadcast to
            step: Step name (e.g., 'step0', 'step3a')
            event_type: Event type (e.g., 'step_started', 'step_completed')
            status: Step status
            progress: Progress percentage (0-100)
            message: Human-readable status message
            attempt: Attempt number if applicable
            details: Additional details
        """
        # Match frontend ProgressEvent type
        event_message: dict[str, Any] = {
            "type": event_type,
            "run_id": run_id,
            "step": step,  # Frontend expects 'step', not 'step_id'
            "status": status,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        if attempt is not None:
            event_message["attempt"] = attempt
        if details:
            event_message["details"] = details
        await self.broadcast(run_id, event_message)


# Global connection manager (will be imported by main.py)
ws_manager = ConnectionManager()


# =============================================================================
# Helper Functions
# =============================================================================


def _get_tenant_db_manager() -> Any:
    """Get tenant DB manager (lazy import to avoid circular dependency)."""
    from apps.api.db.tenant import get_tenant_manager

    return get_tenant_manager()


class RunVerificationResult:
    """Result of run ownership verification."""

    def __init__(self, success: bool, error_type: str | None = None, error_message: str | None = None):
        self.success = success
        self.error_type = error_type  # "not_found", "access_denied", "db_error"
        self.error_message = error_message


async def _verify_run_ownership(tenant_id: str, run_id: str) -> RunVerificationResult:
    """Verify that the run belongs to the specified tenant.

    Args:
        tenant_id: Tenant ID from the authenticated user
        run_id: Run ID to verify

    Returns:
        RunVerificationResult with success status and error details if applicable
    """
    from apps.api.db import Run

    db_manager = _get_tenant_db_manager()
    try:
        async with db_manager.get_session(tenant_id) as session:
            query = select(Run).where(Run.id == run_id, Run.tenant_id == tenant_id)
            result = await session.execute(query)
            run = result.scalar_one_or_none()
            if run is not None:
                return RunVerificationResult(success=True)
            else:
                # Run not found or belongs to different tenant
                return RunVerificationResult(
                    success=False,
                    error_type="not_found",
                    error_message="Run not found or access denied",
                )
    except Exception as e:
        logger.error(f"Database error during run verification: {e}", exc_info=True)
        return RunVerificationResult(
            success=False,
            error_type="db_error",
            error_message="Internal error during verification",
        )


async def _authenticate_websocket(
    websocket: WebSocket,
    token: str | None,
) -> AuthUser | None:
    """Authenticate WebSocket connection using JWT token.

    Args:
        websocket: WebSocket connection
        token: JWT token from query parameter

    Returns:
        AuthUser if authenticated, None if authentication fails
    """
    # Development mode: skip auth
    if SKIP_AUTH:
        return AuthUser(
            user_id="dev-user-001",
            tenant_id=DEV_TENANT_ID,
            roles=["admin"],
        )

    if not token:
        logger.warning("WebSocket connection rejected: missing token")
        return None

    try:
        token_data = verify_token(token)
        return AuthUser(
            user_id=token_data.sub,
            tenant_id=token_data.tenant_id,
            roles=token_data.roles,
        )
    except AuthError as e:
        logger.warning(f"WebSocket authentication failed: {e.reason}")
        return None


# =============================================================================
# Endpoints
# =============================================================================


@router.websocket("/ws/runs/{run_id}")
async def websocket_progress(
    websocket: WebSocket,
    run_id: str,
    token: str | None = Query(default=None, description="JWT authentication token"),
) -> None:
    """WebSocket endpoint for real-time progress updates.

    Authentication:
    - In production: JWT token required via query parameter (?token=xxx)
    - In development (SKIP_AUTH=true): Authentication skipped

    Security:
    - Verifies JWT token validity
    - Verifies that the run belongs to the authenticated user's tenant
    - Rejects connections with invalid/missing auth or unauthorized run access
    """
    # Step 1: Authenticate the connection
    user = await _authenticate_websocket(websocket, token)
    if user is None:
        await websocket.close(code=4001, reason="Authentication required")
        return

    # Step 2: Verify run ownership (tenant isolation)
    verification = await _verify_run_ownership(user.tenant_id, run_id)
    if not verification.success:
        if verification.error_type == "db_error":
            logger.error(f"WebSocket connection rejected due to DB error: {verification.error_message}")
            await websocket.close(code=4500, reason="Internal server error")
        else:
            logger.warning(f"WebSocket connection rejected: {verification.error_message} (run_id={run_id}, tenant={user.tenant_id})")
            await websocket.close(code=4003, reason=verification.error_message or "Run not found or access denied")
        return

    # Step 3: Accept connection and register
    await websocket.accept()
    await ws_manager.connect(run_id, websocket)
    logger.info(
        "WebSocket connected",
        extra={"run_id": run_id, "user_id": user.user_id, "tenant_id": user.tenant_id},
    )

    try:
        while True:
            data = await websocket.receive_text()
            logger.debug("WebSocket received", extra={"run_id": run_id, "payload": data})

            if data == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        ws_manager.disconnect(run_id, websocket)
