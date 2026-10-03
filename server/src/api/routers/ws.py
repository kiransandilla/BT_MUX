"""WebSocket router for live event stream to React dashboard."""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..websocket import ws_manager

logger = logging.getLogger("btmux.ws.router")
router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
@router.websocket("/api/ws")
async def websocket_stream_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint streaming live TDM rotation, node states, and telemetry."""
    await ws_manager.connect(websocket)
    # Send initial welcome / handshake payload
    try:
        await websocket.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "data": {"message": "Connected to BT-Mux diagnostic event stream"},
        })
        while True:
            # Keep connection alive; accept optional client ping/command messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as exc:
        logger.debug("WebSocket client connection ended: %s", exc)
        await ws_manager.disconnect(websocket)
