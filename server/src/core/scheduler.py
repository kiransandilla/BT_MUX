"""BT-Mux Time-Division Multiplexing (TDM) Scheduler.
Authoritative source: BT-Mux_Agent_Instructions.md & SRS REQ-1, REQ-2, REQ-3, REQ-4.
Coordinates batch rotation of physical GATT slots across N >= 10 logical peripheral streams.
Decoupled strictly from BLE drivers via BLETransport interface (BT-Mux_Hardware_Abstraction_Layer.md).
"""
import asyncio
import logging
import time
from typing import Callable, Dict, List, Optional, Set

from ..demo_config import (
    TDM_GUARD_BAND_MS,
    GUARD_BAND_FLOOR_MS,
    GUARD_BAND_CEILING_MS,
    PERIPHERAL_COOLDOWN_MS,
)
from ..config.constants import (
    DEGRADED_TIMEOUT_MS,
    DEFAULT_T_SLICE_MS,
    T_SLICE_MAX_MS,
    T_SLICE_MIN_MS,
    SocketState,
)
from .session_manager import SessionManager
from .transport import BLETransport

logger = logging.getLogger("btmux.core.scheduler")

# Fix 1: Architectural floor/ceiling for the post-disconnect guard band.
_GUARD_BAND_FLOOR_MS: int = 150
_GUARD_BAND_CEILING_MS: int = 300


class TDMScheduler:
    """TDM Scheduler rotating N_max physical radio slots across N logical streams.

    Responsibilities:
     - Queries host controller cap N_max dynamically via transport (REQ-1).
     - Rotates peripheral batches in configurable T_slice windows (REQ-2).
     - Gracefully disconnects physical GATT slots prior to connecting the next batch (REQ-3).
     - Enforces a non-negotiable post-disconnect guard band before re-connecting (Fix 1).
     - Awaits OS-level HCI teardown confirmation before freeing slots (Fix 2).
     - Enforces per-device cooldowns to prevent stalling slow peripherals (Fix 3).
     - Flags peripherals exceeding DEGRADED_TIMEOUT as DEGRADED_RETRY and bypasses slot (REQ-4).
     - Supports dynamic adjustment of T_slice during active sessions (REQ-11).
    """

    def __init__(
        self,
        transport: BLETransport,
        session_manager: SessionManager,
        t_slice_ms: int = DEFAULT_T_SLICE_MS,
        degraded_timeout_ms: int = DEGRADED_TIMEOUT_MS,
    ) -> None:
        self.transport: BLETransport = transport
        self.session_manager: SessionManager = session_manager

        # Dynamic detection of physical connection cap N_max from HAL adapter (SRS REQ-1)
        self.n_max: int = self.transport.get_max_connections()

        # Duty-cycling time window duration (SRS REQ-2)
        self.t_slice_ms: int = min(max(t_slice_ms, T_SLICE_MIN_MS), T_SLICE_MAX_MS)
        self.degraded_timeout_ms: int = degraded_timeout_ms

        # Round-robin queue of device IDs
        self.node_queue: List[str] = []
        # Currently occupied physical radio slots (bounded by self.n_max)
        self.active_slots: Set[str] = set()
        # Nodes flagged as degraded due to connection timeout or link failure (REQ-4)
        self.degraded_nodes: Set[str] = set()

        # Fix 3: Track the last disconnect timestamp per device to enforce cooldowns.
        self._last_disconnect_times: Dict[str, float] = {}

        # Node status callbacks for UI / Telemetry updates
        self._status_callbacks: List[Callable] = []

        # Scheduler lifecycle loop task
        self._running: bool = False
        self._loop_task: Optional[asyncio.Task] = None
        self._lock: asyncio.Lock = asyncio.Lock()

        # Register session manager transport callback if not already configured
        if not self.session_manager._transport_send_fn:
            self.session_manager.set_transport_send_callback(self.transport.send)

    def register_node(self, device_id: str) -> None:
        """Register a logical node into the scheduler's round-robin queue."""
        if device_id not in self.node_queue:
            self.node_queue.append(device_id)
            self.session_manager.get_or_create_socket(device_id)
            logger.info(
                "TDMScheduler: Registered node '%s' (total_nodes=%d)",
                device_id,
                len(self.node_queue),
            )

    def unregister_node(self, device_id: str) -> None:
        """Remove a logical node from the scheduling queue."""
        if device_id in self.node_queue:
            self.node_queue.remove(device_id)
        self.active_slots.discard(device_id)
        self.degraded_nodes.discard(device_id)
        # Fix 3: Clean up cooldown tracking
        self._last_disconnect_times.pop(device_id, None)

    def set_t_slice_ms(self, duration_ms: int) -> None:
        """Dynamically update T_slice duration during active test run (SRS REQ-11)."""
        duration_ms = min(max(duration_ms, T_SLICE_MIN_MS), T_SLICE_MAX_MS)
        logger.info(
            "TDMScheduler: Updated T_slice from %d ms to %d ms (REQ-11)",
            self.t_slice_ms,
            duration_ms,
        )
        self.t_slice_ms = duration_ms

    async def start(self) -> None:
        """Start the background TDM scheduling loop."""
        async with self._lock:
            if self._running:
                return
            self._running = True
            self._loop_task = asyncio.create_task(self._run_loop(), name="tdm_scheduler_loop")
            logger.info(
                "TDMScheduler started (N_max=%d, T_slice=%d ms, guard_band=%d ms, cooldown=%d ms, total_nodes=%d)",
                self.n_max,
                self.t_slice_ms,
                self._effective_guard_band_ms(),
                PERIPHERAL_COOLDOWN_MS,
                len(self.node_queue),
            )

    async def stop(self) -> None:
        """Stop the scheduling loop and gracefully disconnect all active slots."""
        async with self._lock:
            if not self._running:
                return
            self._running = False

            if self._loop_task and not self._loop_task.done():
                self._loop_task.cancel()
                try:
                    await self._loop_task
                except asyncio.CancelledError:
                    pass

            active_devs = list(self.active_slots)
            for dev_id in active_devs:
                await self._disconnect_node_graceful(dev_id)

            logger.info("TDMScheduler stopped. All physical radio slots freed.")

    def _effective_guard_band_ms(self) -> int:
        """Clamp the configured guard band into the mandatory 150-300 ms window (Fix 1)."""
        clamped = min(
            max(int(TDM_GUARD_BAND_MS), GUARD_BAND_FLOOR_MS),
            GUARD_BAND_CEILING_MS,
        )
        if clamped != TDM_GUARD_BAND_MS:
            logger.warning(
                "TDMScheduler: Configured guard band %s ms is outside the mandatory "
                "%d-%d ms window; enforcing %d ms (Fix 1).",
                TDM_GUARD_BAND_MS,
                GUARD_BAND_FLOOR_MS,
                GUARD_BAND_CEILING_MS,
                clamped,
            )
        return clamped

    async def step_rotation(self) -> None:
        """Execute a single deterministic TDM batch rotation step."""
        if not self.node_queue:
            return

        # =====================================================================
        # FIX 3: SMART PER-DEVICE CONNECTION COOLDOWN FILTER
        # =====================================================================
        # Android peripherals require time to reset their internal BLE state 
        # machines after a disconnect. We filter the queue to only select nodes 
        # that have sufficiently recovered.
        current_time = time.monotonic()
        cooldown_sec = PERIPHERAL_COOLDOWN_MS / 1000.0
        
        available_nodes = [
            dev_id for dev_id in self.node_queue 
            if (current_time - self._last_disconnect_times.get(dev_id, 0.0)) >= cooldown_sec
        ]
        
        # Smart Sleep Fallback: If ALL nodes are in cooldown (which is guaranteed 
        # to happen immediately if N=1), calculate the exact remaining time for 
        # the earliest node to recover and sleep for that duration. This prevents 
        # the 9000ms DEGRADED timeout loop.
        if not available_nodes:
            min_remaining = min(
                (self._last_disconnect_times.get(dev_id, 0.0) + cooldown_sec) - current_time
                for dev_id in self.node_queue
            )
            if min_remaining > 0:
                logger.info(
                    "TDMScheduler: All nodes in cooldown. Waiting %.2f ms for earliest node to recover (Fix 3).",
                    min_remaining * 1000.0
                )
                await asyncio.sleep(min_remaining)
            
            # Re-evaluate after sleep
            current_time = time.monotonic()
            available_nodes = [
                dev_id for dev_id in self.node_queue 
                if (current_time - self._last_disconnect_times.get(dev_id, 0.0)) >= cooldown_sec
            ]
            
            # Absolute fallback for floating-point edge cases
            if not available_nodes:
                available_nodes = self.node_queue

        batch_size = min(self.n_max, len(available_nodes))
        current_batch = available_nodes[:batch_size]
        connected_nodes: List[str] = []

        # 1. Establish physical links for current batch concurrently with timeout
        connect_results = await asyncio.gather(
            *(self._connect_node_with_timeout(dev_id) for dev_id in current_batch)
        )
        for dev_id, connected in zip(current_batch, connect_results):
            if connected:
                connected_nodes.append(dev_id)
                self.active_slots.add(dev_id)

        # 2. Run active transmission window for T_slice
        slice_seconds = self.t_slice_ms / 1000.0
        await asyncio.sleep(slice_seconds)

        # 3. Gracefully tear down physical connections concurrently
        if connected_nodes:
            await asyncio.gather(
                *(self._disconnect_node_graceful(dev_id) for dev_id in connected_nodes)
            )

        # =====================================================================
        # FIX 1: STRICT, NON-NEGOTIABLE TDM GUARD BAND
        # =====================================================================
        guard_band_ms = self._effective_guard_band_ms()
        logger.info(
            "TDMScheduler: Guard band start - holding radio quiet for %d ms "
            "before next batch (Fix 1, REQ-3).",
            guard_band_ms,
        )
        await asyncio.sleep(guard_band_ms / 1000.0)
        logger.info(
            "TDMScheduler: Guard band complete - radio slots available for next batch."
        )
        # =====================================================================

        # 4. Advance round-robin queue.
        # We remove the selected batch from the main queue and append them to the back.
        # This correctly preserves the order of any nodes that were skipped due to cooldown.
        remaining_queue = [dev_id for dev_id in self.node_queue if dev_id not in current_batch]
        self.node_queue = remaining_queue + current_batch

    async def _connect_node_with_timeout(self, device_id: str) -> bool:
        """Connect to peripheral with strict DEGRADED timeout (SRS REQ-4)."""
        sock = self.session_manager.get_or_create_socket(device_id)
        sock.set_physical_state(SocketState.CONNECTING)
        timeout_sec = self.degraded_timeout_ms / 1000.0

        try:
            await asyncio.wait_for(self.transport.connect(device_id), timeout=timeout_sec)
            self.degraded_nodes.discard(device_id)
            await self.session_manager.on_physical_link_connected(device_id)
            return True
        except (asyncio.TimeoutError, Exception) as exc:
            logger.warning(
                "TDMScheduler: Node '%s' failed link establishment within %d ms -> DEGRADED "
                "(bypass slot): %s",
                device_id,
                self.degraded_timeout_ms,
                exc,
            )
            self.degraded_nodes.add(device_id)
            await self.session_manager.on_physical_link_degraded(device_id)
            return False

    async def _disconnect_node_graceful(self, device_id: str) -> None:
        """Gracefully release physical GATT connection and notify session manager (SRS REQ-3).
        
        Fix 2: The transport.disconnect() call blocks until the OS confirms 
        the HCI Disconnection Complete event. 
        Fix 3: We record the exact teardown time to enforce the peripheral cooldown.
        """
        try:
            await self.session_manager.on_physical_link_paused(device_id)
            logger.info("Scheduler: Awaiting OS-level HCI teardown for '%s' (Fix 2)...", device_id)
            
            # This await blocks until the Bleak adapter confirms the OS teardown
            await self.transport.disconnect(device_id)
            
            logger.info("Scheduler: Slot '%s' is now physically free.", device_id)
            
            # Fix 3: Record the exact time the physical link was fully freed
            self._last_disconnect_times[device_id] = time.monotonic()
            
        except Exception as exc:
            logger.warning("Error disconnecting node '%s': %s", device_id, exc)
            # Even on error, record the time to prevent infinite rapid retries
            self._last_disconnect_times[device_id] = time.monotonic()
        finally:
            self.active_slots.discard(device_id)

    async def _run_loop(self) -> None:
        """Internal continuous rotation loop."""
        try:
            while self._running:
                await self.step_rotation()
                await asyncio.sleep(0.005)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.exception("Unexpected exception in TDMScheduler loop: %s", exc)