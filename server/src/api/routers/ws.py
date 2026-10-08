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
    from ...core.engine import engine

    await ws_manager.connect(websocket)
    # Send initial welcome and current snapshot in single handshake frame
    try:
        await websocket.send_json({
            "type": "CONNECTION_ESTABLISHED",
            "data": {
                "message": "Connected to BT-Mux diagnostic event stream",
                "initial_state": engine.get_telemetry_snapshot(),
            },
        })
        while True:
            # Keep connection alive; accept optional client ping/command messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            elif data.startswith("{"):
                import json
                try:
                    msg = json.loads(data)
                    cmd = msg.get("command")
                    if cmd == "START":
                        await engine.start()
                    elif cmd == "STOP":
                        await engine.stop()
                    elif cmd == "SET_T_SLICE":
                        val = int(msg.get("value", 500))
                        engine.set_t_slice_ms(val)
                    elif cmd == "RESET":
                        await engine.reset()
                except Exception as parse_err:
                    logger.debug("WS command error: %s", parse_err)
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception as exc:
        logger.debug("WebSocket client connection ended: %s", exc)
        await ws_manager.disconnect(websocket)

