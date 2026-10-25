"""Physical BLE Transport Adapter using Bleak (WinRT / BlueZ D-Bus).

Authoritative source: BT-Mux_Hardware_Abstraction_Layer.md Sections 3, 4, 9.

Android 16 / Windows WinRT fix (2026-10 v2):

  Problem: Android 16's GATT stack exits the 7.5ms high-speed discovery burst
  much faster than Android 12 (~400ms vs ~1600ms).  When a second device is
  connected or data is sent before the first device's link has settled to the
  balanced 60ms interval, the radio contention causes packet loss and the
  degraded-connection symptom.

  v1 attempted to gate connect() on a Bleak connection_update_callback.
  That callback is not reliably fired on Windows WinRT, so settled_event
  never triggered, the 1.8s timeout blocked the TDM scheduler's send loop,
  and the scheduler marked the Android 16 device as unresponsive — producing
  the status=19 (GATT_CONN_TERMINATE_PEER_USER) disconnect seen in logs.

  v2 fix:
    - connect() returns immediately after the GATT link is up and services
      are subscribed — it does NOT block on settling.
    - A post-connect asyncio.sleep() of SETTLE_DELAY_SEC runs as a fire-and-
      forget background task, marking the device settled after the delay.
    - send() checks the settled flag; if not yet settled it waits for at most
      SETTLE_TIMEOUT_SEC before proceeding anyway.  This means the first few
      sends after connect() are naturally rate-limited to let the radio
      stabilise, but the scheduler's view of the connection is never blocked.
    - The connection_update_callback hook is preserved but wrapped in a
      try/except so it degrades gracefully on WinRT builds that lack it.
"""
import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional

from bleak import BleakClient, BleakScanner

from ..config.constants import N_MAX_PHYSICAL_DEFAULT
from .base import BLETransport

logger = logging.getLogger("btmux.hal.bleak")

DEFAULT_TX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
DEFAULT_RX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

# How long to wait after connect() before the first send() on a new link.
# Covers the 7.5ms -> 60ms interval negotiation on both Android 12 and 16.
# Used only when the connection_update_callback is unavailable (WinRT).
SETTLE_DELAY_SEC: float = 1.2

# Hard ceiling: if the settled event still hasn't fired after this long,
# proceed anyway rather than blocking the scheduler indefinitely.
SETTLE_TIMEOUT_SEC: float = 2.0

# Balanced interval threshold in 1.25ms units (48 * 1.25ms = 60ms).
_SETTLED_INTERVAL_UNITS = 48

# Detect at import time whether this Bleak build accepts
# connection_update_callback so we never pass an unknown kwarg.
_BLEAK_SUPPORTS_CONN_UPDATE = (
    "connection_update_callback" in inspect.signature(BleakClient.__init__).parameters
)


class BleakTransport(BLETransport):
    """Concrete BLETransport adapter backed by Bleak."""

    def __init__(
        self,
        max_connections: int = N_MAX_PHYSICAL_DEFAULT,
        tx_char_uuid: str = DEFAULT_TX_CHAR_UUID,
        rx_char_uuid: str = DEFAULT_RX_CHAR_UUID,
    ) -> None:
        self.max_connections = max_connections
        self.tx_char_uuid = tx_char_uuid
        self.rx_char_uuid = rx_char_uuid

        self._clients: Dict[str, BleakClient] = {}
        # Resolved TX char UUID cached per device (no GATT walk on every write)
        self._tx_char_cache: Dict[str, str] = {}
        # Per-device event set once radio parameters have settled
        self._settled: Dict[str, asyncio.Event] = {}

        self._callbacks: Dict[str, List[Callable[..., Any]]] = {
            "data": [],
            "connected": [],
            "disconnected": [],
        }
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_tx_uuid(self, client: BleakClient) -> str:
        for s in client.services:
            for c in s.characteristics:
                if c.uuid.lower() == self.tx_char_uuid.lower():
                    return self.tx_char_uuid
        for s in client.services:
            if s.uuid.lower().startswith(("00001800", "00001801")):
                continue
            for c in s.characteristics:
                if "write-without-response" in c.properties or "write" in c.properties:
                    logger.debug("NUS TX absent on '%s'; fallback to %s", client.address, c.uuid)
                    return c.uuid
        return self.tx_char_uuid

    def _resolve_rx_uuid(self, client: BleakClient) -> str:
        for s in client.services:
            for c in s.characteristics:
                if c.uuid.lower() == self.rx_char_uuid.lower():
                    return self.rx_char_uuid
        for s in client.services:
            for c in s.characteristics:
                if "notify" in c.properties:
                    return c.uuid
        return self.rx_char_uuid

    async def _settle_after_delay(self, device_id: str) -> None:
        """Background task: mark device settled after SETTLE_DELAY_SEC.

        Used as the fallback path when connection_update_callback is not
        available (Windows WinRT) or never fires.
        """
        await asyncio.sleep(SETTLE_DELAY_SEC)
        event = self._settled.get(device_id)
        if event and not event.is_set():
            logger.info("'%s' settled via timer fallback (%.1fs)", device_id, SETTLE_DELAY_SEC)
            event.set()

    # ------------------------------------------------------------------
    # BLETransport interface
    # ------------------------------------------------------------------

    async def connect(self, device_id: str) -> None:
        """Establish physical GATT connection.

        Returns as soon as the link is up and service subscription is done.
        A background task begins counting down the settling window so that
        the first send() call waits out the 7.5ms->60ms radio negotiation
        without blocking the scheduler's view of this connection.
        """
        async with self._lock:
            if device_id in self._clients and self._clients[device_id].is_connected:
                return

            settled_event = asyncio.Event()
            self._settled[device_id] = settled_event

            def on_disconnect(client: BleakClient) -> None:
                logger.info("BleakClient '%s' disconnected", device_id)
                self._clients.pop(device_id, None)
                self._tx_char_cache.pop(device_id, None)
                self._settled.pop(device_id, None)
                self._trigger_event("disconnected", device_id)

            # Build kwargs; add connection_update_callback only if supported
            extra_kwargs: Dict[str, Any] = {}
            if _BLEAK_SUPPORTS_CONN_UPDATE:
                def _on_conn_update(interval: int, latency: int, timeout: int, status: int) -> None:
                    if interval >= _SETTLED_INTERVAL_UNITS and not settled_event.is_set():
                        logger.info(
                            "'%s' settled via conn-update event: interval=%d (%.1fms)",
                            device_id, interval, interval * 1.25,
                        )
                        settled_event.set()
                extra_kwargs["connection_update_callback"] = _on_conn_update

            client = None
            last_err = None
            for addr_type in ("random", "public"):
                try:
                    c = BleakClient(
                        device_id,
                        disconnected_callback=on_disconnect,
                        winrt={"address_type": addr_type},
                        **extra_kwargs,
                    )
                    logger.info("Connecting to '%s' (addr_type=%s)...", device_id, addr_type)
                    await c.connect()
                    client = c
                    break
                except Exception as ex:
                    last_err = ex

            if not client or not client.is_connected:
                self._settled.pop(device_id, None)
                raise ConnectionError(f"Failed to connect to '{device_id}': {last_err}")

            self._clients[device_id] = client
            self._tx_char_cache[device_id] = self._resolve_tx_uuid(client)

            rx_uuid = self._resolve_rx_uuid(client)
            try:
                def notification_handler(sender: Any, data: bytearray) -> None:
                    self._trigger_event("data", device_id, bytes(data))
                await client.start_notify(rx_uuid, notification_handler)
            except Exception as e:
                logger.debug("Notify subscription skipped on '%s': %s", device_id, e)

        # Fire-and-forget settling timer — runs concurrently, does NOT block
        # connect() return.  If connection_update_callback fires first it sets
        # the event early; the timer then finds it already set and does nothing.
        asyncio.create_task(self._settle_after_delay(device_id))

        logger.info("BleakClient connected (settling in background): '%s'", device_id)
        self._trigger_event("connected", device_id)

    async def wait_for_settle(self, device_id: str) -> None:
        """Block until this device's radio parameters have settled.

        Safe to call from the TDM scheduler before the first send() on a
        freshly connected slot.  Returns immediately if already settled or
        if the device is not tracked (e.g. simulated peer).
        """
        event = self._settled.get(device_id)
        if not event or event.is_set():
            return
        try:
            await asyncio.wait_for(asyncio.shield(event.wait()), timeout=SETTLE_TIMEOUT_SEC)
        except asyncio.TimeoutError:
            logger.warning(
                "'%s' settle wait timed out after %.1fs — proceeding",
                device_id, SETTLE_TIMEOUT_SEC,
            )
            event.set()

    async def disconnect(self, device_id: str) -> None:
        """Tear down physical GATT connection."""
        async with self._lock:
            client = self._clients.pop(device_id, None)
            self._tx_char_cache.pop(device_id, None)
            self._settled.pop(device_id, None)

        if client and client.is_connected:
            logger.info("Disconnecting '%s'...", device_id)
            await client.disconnect()
            self._trigger_event("disconnected", device_id)

    async def send(self, device_id: str, data: bytes) -> None:
        """Transmit raw payload chunk via GATT write.

        If called before the settling window has closed (i.e. very soon after
        connect()) this will briefly wait — preventing writes during the
        7.5ms high-speed radio phase.  Once settled the wait is a no-op.
        """
        # Settle check — fast path once the event is set (is_set() is O(1))
        event = self._settled.get(device_id)
        if event and not event.is_set():
            await self.wait_for_settle(device_id)

        client = self._clients.get(device_id)
        if not client or not client.is_connected:
            raise ConnectionResetError(f"Bleak client '{device_id}' is not connected")

        target_tx_uuid = self._tx_char_cache.get(device_id, self.tx_char_uuid)
        await client.write_gatt_char(target_tx_uuid, data, response=False)
        logger.debug("TX %d bytes -> '%s' (char=%s)", len(data), device_id, target_tx_uuid)

    def on(self, event: str, callback: Callable[..., Any]) -> None:
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    async def scan_for_devices(self) -> List[Dict[str, Any]]:
        logger.info("Scanning for BLE peripherals...")
        devices = await BleakScanner.discover(timeout=3.0)
        return [
            {"device_id": d.address, "name": d.name or "Unknown", "rssi": getattr(d, "rssi", None)}
            for d in devices
        ]

    def _trigger_event(self, event: str, *args: Any, **kwargs: Any) -> None:
        for cb in self._callbacks.get(event, []):
            try:
                res = cb(*args, **kwargs)
                if asyncio.iscoroutine(res):
                    asyncio.create_task(res)
            except Exception as exc:
                logger.error("Error in event callback '%s': %s", event, exc)
                
    def get_max_connections(self) -> int:
        """Return host physical radio N_max connection limit (SRS REQ-1)."""
        return self.max_connections