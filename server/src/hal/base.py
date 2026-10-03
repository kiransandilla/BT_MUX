"""Abstract Base Class for Hardware Abstraction Layer (HAL) BLE Transport.

Authoritative source: BT-Mux_Hardware_Abstraction_Layer.md Section 2.
All core modules (Virtual Socket, Session Manager, Scheduler) depend strictly
on this abstract interface — NEVER directly on bleak or driver libraries.
"""
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List


class BLETransport(ABC):
    """Abstract interface contract for physical or simulated BLE GATT connectivity."""

    @abstractmethod
    async def connect(self, device_id: str) -> None:
        """Establish physical GATT connection to peripheral."""
        pass

    @abstractmethod
    async def disconnect(self, device_id: str) -> None:
        """Tear down physical GATT connection."""
        pass

    @abstractmethod
    async def send(self, device_id: str, data: bytes) -> None:
        """Transmit raw payload chunk to peripheral."""
        pass

    @abstractmethod
    def on(self, event: str, callback: Callable[..., Any]) -> None:
        """Register event listeners ('data', 'connected', 'disconnected')."""
        pass

    @abstractmethod
    async def scan_for_devices(self) -> List[Dict[str, Any]]:
        """Scan for available BLE peripherals."""
        pass

    @abstractmethod
    def get_max_connections(self) -> int:
        """Return host physical radio N_max connection limit (SRS REQ-1)."""
        pass
