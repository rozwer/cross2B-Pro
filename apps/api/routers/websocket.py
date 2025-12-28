"""WebSocket router.

Handles WebSocket connections for real-time progress streaming.
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


# =============================================================================
# Connection Manager
# =============================================================================


class ConnectionManager:
    """WebSocket connection manager for real-time updates."""

    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, run_id: str, websocket: WebSocket) -> None:
        """Track a WebSocket connection (acceptは呼び出し側で実施済み)."""
        if run_id not in self.active_connections:
            self.active_connections[run_id] = []
        self.active_connections[run_id].append(websocket)
        logger.info("WebSocket connected", extra={"run_id": run_id})

    def disconnect(self, run_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if run_id in self.active_connections:
            if websocket in self.active_connections[run_id]:
                self.active_connections[run_id].remove(websocket)
            if not self.active_connections[run_id]:
                del self.active_connections[run_id]
        logger.info("WebSocket disconnected", extra={"run_id": run_id})

    async def broadcast(self, run_id: str, message: dict[str, Any]) -> None:
        """Broadcast message to all connections for a run."""
        if run_id in self.active_connections:
            disconnected = []
            for websocket in self.active_connections[run_id]:
                try:
                    await websocket.send_json(message)
                except Exception:
                    disconnected.append(websocket)
            for ws in disconnected:
                self.disconnect(run_id, ws)

    async def broadcast_run_update(
        self,
        run_id: str,
        event_type: str,
        status: str,
        current_step: str | None = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        """Broadcast a run status update event.

        Args:
            run_id: The run ID to broadcast to
            event_type: Event type (e.g., 'run.status_changed', 'step.started')
            status: Current run status
            current_step: Current step name if applicable
            error: Error details if applicable
        """
        message: dict[str, Any] = {
            "type": event_type,
            "run_id": run_id,
            "status": status,
            "current_step": current_step,
            "timestamp": datetime.now().isoformat(),
        }
        if error:
            message["error"] = error
        await self.broadcast(run_id, message)

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
# Endpoints
# =============================================================================


@router.websocket("/ws/runs/{run_id}")
async def websocket_progress(websocket: WebSocket, run_id: str) -> None:
    """WebSocket endpoint for real-time progress updates.

    NOTE: 開発段階では認証を無効化
    """
    await websocket.accept()
    await ws_manager.connect(run_id, websocket)
    logger.info("WebSocket connected", extra={"run_id": run_id})

    try:
        while True:
            data = await websocket.receive_text()
            logger.debug("WebSocket received", extra={"run_id": run_id, "payload": data})

            if data == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        ws_manager.disconnect(run_id, websocket)
