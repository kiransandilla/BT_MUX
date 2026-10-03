"""Unit and integration tests for WebSocket real-time telemetry streaming (SRS REQ-9, REQ-10)."""
import pytest
from starlette.testclient import TestClient

from src.api.websocket import ws_manager
from src.main import app


def test_websocket_connection_and_handshake():
    """Verify WebSocket client connection and initial handshake payload."""
    client = TestClient(app)
    with client.websocket_connect("/ws") as websocket:
        data = websocket.receive_json()
        assert data["type"] == "CONNECTION_ESTABLISHED"
        assert "message" in data["data"]


def test_websocket_ping_pong():
    """Verify bidirectional keepalive on WebSocket."""
    client = TestClient(app)
    with client.websocket_connect("/ws") as websocket:
        _ = websocket.receive_json()
        websocket.send_text("ping")
        assert websocket.receive_text() == "pong"


@pytest.mark.asyncio
async def test_websocket_broadcast_event():
    """Verify broadcasting event payloads to connected clients."""
    client = TestClient(app)
    with client.websocket_connect("/ws") as websocket:
        _ = websocket.receive_json()  # Handshake

        # Broadcast test telemetry event
        event_data = {
            "session_id": "test_sess_01",
            "active_batch": ["dev_01", "dev_02"],
            "queue_depths": {"dev_01": 5, "dev_02": 0},
            "pdr": 0.98,
        }
        await ws_manager.broadcast("SLOT_ROTATION", event_data)

        # Receive broadcasted payload on client
        received = websocket.receive_json()
        assert received["type"] == "SLOT_ROTATION"
        assert received["data"]["session_id"] == "test_sess_01"
        assert received["data"]["active_batch"] == ["dev_01", "dev_02"]
