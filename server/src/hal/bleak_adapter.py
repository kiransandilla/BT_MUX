"""Physical BLE Transport Adapter using Bleak (WinRT / BlueZ D-Bus).

Authoritative source: BT-Mux_Hardware_Abstraction_Layer.md Sections 3, 4, 9.
Uses Bleak natively:
- On Windows: Communicates via WinRT (Windows.Devices.Bluetooth)
- On Linux / Raspberry Pi: Communicates via BlueZ D-Bus
Zero driver modification required (SRS 2.5 / 5.4).
"""
import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional
from bleak import BleakClient, BleakScanner

from ..config.constants import N_MAX_PHYSICAL_DEFAULT
from .base import BLETransport

logger = logging.getLogger("btmux.hal.bleak")

# Standard Nordic UART Service (NUS) RX/TX characteristics or generic UART characteristic UUID
DEFAULT_TX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
DEFAULT_RX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"


class BleakTransport(BLETransport):
    """Concrete BLETransport adapter backed by Bleak."""

    def __init__(
        self,
        max_connections: int = N_MAX_PHYSICAL_DEFAULT,
        tx_char_uuid: str = DEFAULT_TX_CHAR_UUID,
        rx_char_uuid: str = DEFAULT_RX_CHAR_UUID,
    ) -> None:
        self.max_connections: int = max_connections
        self.tx_char_uuid: str = tx_char_uuid
        self.rx_char_uuid: str = rx_char_uuid

        # Map of device_id -> active BleakClient instance
        self._clients: Dict[str, BleakClient] = {}
        # Registered event callbacks
        self._callbacks: Dict[str, List[Callable[..., Any]]] = {
            "data": [],
            "connected": [],
            "disconnected": [],
        }
        self._lock: asyncio.Lock = asyncio.Lock()

    def get_max_connections(self) -> int:
        """Return host physical radio N_max connection limit (SRS REQ-1)."""
        return self.max_connections

    async def connect(self, device_id: str) -> None:
        """Establish physical GATT connection to BLE peripheral using Bleak."""
        async with self._lock:
            if device_id in self._clients and self._clients[device_id].is_connected:
                return

            def on_disconnect(client: BleakClient) -> None:
                logger.info("Bleak client '%s' disconnected by host/peripheral", device_id)
                self._clients.pop(device_id, None)
                self._trigger_event("disconnected", device_id)

            # Connect with fallback across random and public address types (crucial for Android RPA)
            client = None
            last_err = None
            for addr_type in ("random", "public"):
                try:
                    c = BleakClient(
                        device_id,
                        disconnected_callback=on_disconnect,
                        winrt={"address_type": addr_type},
                    )
                    logger.info("Connecting BleakClient to '%s' (type=%s)...", device_id, addr_type)
                    await c.connect()
                    client = c
                    break
                except Exception as ex:
                    last_err = ex

            if not client or not client.is_connected:
                raise ConnectionError(f"Failed to connect to BLE device '{device_id}': {last_err}")

            self._clients[device_id] = client

            # Auto-detect writable characteristic if default NUS TX is not in GATT table
            target_rx_uuid = self.rx_char_uuid
            if client.services:
                # Check for notify characteristic for RX ACKs
                has_nus_rx = any(
                    c.uuid.lower() == self.rx_char_uuid.lower()
                    for s in client.services for c in s.characteristics
                )
                if not has_nus_rx:
                    for s in client.services:
                        for c in s.characteristics:
                            if "notify" in c.properties:
                                target_rx_uuid = c.uuid
                                break

            # Optional: subscribe to RX notifications if characteristic is supported
            try:
                def notification_handler(sender: Any, data: bytearray) -> None:
                    self._trigger_event("data", device_id, bytes(data))

                await client.start_notify(target_rx_uuid, notification_handler)
            except Exception as e:
                logger.debug("Characteristic notify subscription skipped on %s: %s", device_id, e)

        logger.info("BleakClient connected successfully to '%s'", device_id)
        self._trigger_event("connected", device_id)

    async def disconnect(self, device_id: str) -> None:
        """Tear down physical GATT connection."""
        async with self._lock:
            client = self._clients.pop(device_id, None)

        if client and client.is_connected:
            logger.info("Disconnecting BleakClient from '%s'...", device_id)
            await client.disconnect()
            self._trigger_event("disconnected", device_id)

    async def send(self, device_id: str, data: bytes) -> None:
        """Transmit raw payload chunk to peripheral via GATT write."""
        client = self._clients.get(device_id)
        if not client or not client.is_connected:
            raise ConnectionResetError(f"Bleak client '{device_id}' is not connected")

        # Resolve target characteristic: look for NUS TX first, then fallback to any writable char
        target_tx_uuid = self.tx_char_uuid
        has_nus_tx = any(
            c.uuid.lower() == self.tx_char_uuid.lower()
            for s in client.services for c in s.characteristics
        )
        if not has_nus_tx:
            # Look for user-level write-without-response characteristics (skip GAP/GATT system services)
            for s in client.services:
                s_uuid = s.uuid.lower()
                if s_uuid.startswith("00001800") or s_uuid.startswith("00001801"):
                    continue
                for c in s.characteristics:
                    if "write-without-response" in c.properties or "write" in c.properties:
                        target_tx_uuid = c.uuid
                        break
                if target_tx_uuid != self.tx_char_uuid:
                    break

        # Write data to GATT characteristic
        await client.write_gatt_char(target_tx_uuid, data, response=False)
        logger.debug("BleakTransport: Transmitted %d bytes to '%s' (char=%s)", len(data), device_id, target_tx_uuid)

    def on(self, event: str, callback: Callable[..., Any]) -> None:
        """Register event listeners ('data', 'connected', 'disconnected')."""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    async def scan_for_devices(self) -> List[Dict[str, Any]]:
        """Scan for available BLE peripherals in radio range."""
        logger.info("Scanning for physical BLE peripherals via BleakScanner...")
        devices = await BleakScanner.discover(timeout=3.0)
        return [
            {
                "device_id": d.address,
                "name": d.name or "Unknown Peripheral",
                "rssi": getattr(d, "rssi", None),
            }
            for d in devices
        ]

    def _trigger_event(self, event: str, *args: Any, **kwargs: Any) -> None:
        for cb in self._callbacks.get(event, []):
            try:
                res = cb(*args, **kwargs)
                if asyncio.iscoroutine(res):
                    asyncio.create_task(res)
            except Exception as exc:
                logger.error("Error in Bleak event callback '%s': %s", event, exc)
