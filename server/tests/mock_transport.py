"""Mock BLETransport implementation for unit testing core scheduler and session manager."""
import asyncio
from typing import Any, Callable, Dict, List, Set
from src.core.transport import BLETransport


class MockTransport(BLETransport):
    """In-memory simulated BLE transport with controllable latencies and failure modes."""

    def __init__(self, max_connections: int = 4) -> None:
        self.max_connections = max_connections
        self.connected_devices: Set[str] = set()
        self.sent_payloads: List[tuple[str, bytes]] = []
        self.failing_devices: Set[str] = set()
        self.connect_delays: Dict[str, float] = {}
        self.event_callbacks: Dict[str, List[Callable[..., Any]]] = {}

    async def connect(self, device_id: str) -> None:
        if device_id in self.failing_devices:
            raise ConnectionError(f"Simulated link failure connecting to {device_id}")

        delay = self.connect_delays.get(device_id, 0.005)
        await asyncio.sleep(delay)
        self.connected_devices.add(device_id)

    async def disconnect(self, device_id: str) -> None:
        await asyncio.sleep(0.002)
        self.connected_devices.discard(device_id)

    async def send(self, device_id: str, data: bytes) -> None:
        self.sent_payloads.append((device_id, data))

    def on(self, event: str, callback: Callable[..., Any]) -> None:
        if event not in self.event_callbacks:
            self.event_callbacks[event] = []
        self.event_callbacks[event].append(callback)

    async def scan_for_devices(self) -> List[Dict[str, Any]]:
        return [{"device_id": d} for d in self.connected_devices]

    def get_max_connections(self) -> int:
        return self.max_connections
