"""WebSocket Connection Manager and Real-Time Event Broadcaster.

Authoritative source: fastapi-patterns skill & SRS REQ-9, REQ-10.
Streams real-time slot rotations, socket state machine transitions,
and packet queue telemetry to the React diagnostic dashboard.
"""
import asyncio
import logging
from typing import Any, Dict, List, Set
from fastapi import WebSocket

logger = logging.getLogger("btmux.ws")


class ConnectionManager:
    """Manages active WebSocket connections from React diagnostic dashboard clients."""

    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()
        self._lock: asyncio.Lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept incoming client connection and register in active set."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info("WebSocket client connected (total_clients=%d)", len(self.active_connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove disconnected client from active set."""
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info("WebSocket client disconnected (remaining_clients=%d)", len(self.active_connections))

    async def broadcast(self, event_type: str, data: Dict[str, Any]) -> None:
        """Broadcast structured event payload to all connected dashboard clients."""
        payload = {
            "type": event_type,
            "data": data,
        }
        async with self._lock:
            clients = list(self.active_connections)

        if not clients:
            return

        dead_connections = []
        for connection in clients:
            try:
                await connection.send_json(payload)
            except Exception as exc:
                logger.debug("Failed sending to client, scheduling removal: %s", exc)
                dead_connections.append(connection)

        if dead_connections:
            async with self._lock:
                for dead in dead_connections:
                    self.active_connections.discard(dead)


# Global singleton instance
ws_manager = ConnectionManager()
