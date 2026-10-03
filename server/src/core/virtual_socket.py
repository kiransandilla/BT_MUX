"""BT-Mux Virtual Socket Abstraction.

Authoritative source: BT-Mux_Agent_Instructions.md & SRS REQ-5, REQ-6, REQ-7, REQ-10.
Non-negotiable architectural constraint: Core modules must never depend directly on a
specific BLE driver library (BT-Mux_Hardware_Abstraction_Layer.md).
"""
import asyncio
import logging
from enum import Enum
from typing import Optional
import uuid

from ..config.constants import SocketState

logger = logging.getLogger("btmux.core.virtual_socket")


class LogicalSocketState(str, Enum):
    """API-facing logical socket state machine.
    
    Remains OPEN regardless of underlying physical GATT connection duty-cycling (REQ-5).
    """
    OPEN = "OPEN"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"


class VirtualSocket:
    """Virtual socket representing a persistent logical stream over multiplexed BLE.
    
    Provides standard asynchronous socket-like semantics (send, recv, close) to
    higher-layer applications (e.g. multi-peer file transfer). Physical disconnects
    caused by TDM batch rotation are masked by dedicated per-stream RAM FIFO buffers,
    ensuring logical streams never appear dropped (SRS REQ-5, REQ-7).
    """

    def __init__(
        self,
        device_id: str,
        session_id: str,
        socket_id: Optional[str] = None,
        max_queue_size: int = 0,
    ) -> None:
        """Initialize a new virtual socket.
        
        Args:
            device_id: Identifier of target peripheral (plain string, never raw Bleak client).
            session_id: Associated experiment run ID.
            socket_id: Optional unique socket ID; generated automatically if omitted.
            max_queue_size: Max capacity of FIFO queues (0 = unbounded within memory ceiling).
        """
        self.socket_id: str = socket_id or uuid.uuid4().hex
        self.device_id: str = device_id
        self.session_id: str = session_id

        # Logical state visible to application layer
        self.logical_state: LogicalSocketState = LogicalSocketState.OPEN

        # Physical link state tracked from TDM scheduler / HAL
        self.physical_state: SocketState = SocketState.UNINITIALIZED

        # Dedicated per-stream RAM FIFO queues (REQ-6: dedicated thread-safe queues per stream)
        # Dedicated queues isolate slow/paused streams so one blocked node does not stall others.
        self._tx_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=max_queue_size)
        self._rx_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=max_queue_size)

        # Event signalled when physical radio link is established and ready for transmission
        self._link_ready_event: asyncio.Event = asyncio.Event()

        # State lock protecting transitions
        self._lock: asyncio.Lock = asyncio.Lock()

        # Byte throughput counters for telemetry profiling (REQ-10)
        self.total_bytes_sent: int = 0
        self.total_bytes_received: int = 0

    @property
    def is_active(self) -> bool:
        """Check if logical socket is active.
        
        The socket remains ACTIVE in user space even when physical radio is paused or
        reconnecting during TDM slot rotation (REQ-5 viva requirement).
        """
        return self.logical_state == LogicalSocketState.OPEN

    @property
    def is_physical_link_active(self) -> bool:
        """Check if physical GATT connection is currently active."""
        return self.physical_state == SocketState.ACTIVE_PHYSICAL_LINK

    @property
    def tx_queue_depth(self) -> int:
        """Return number of pending un-flushed payload chunks in RAM buffer (REQ-10)."""
        return self._tx_queue.qsize()

    @property
    def rx_queue_depth(self) -> int:
        """Return number of pending received payload chunks in RX queue."""
        return self._rx_queue.qsize()

    async def send(self, data: bytes) -> int:
        """Accept outgoing payload from application layer and buffer in RAM.
        
        Buffer instead of dropping so physical disconnect is completely invisible
        to the higher-layer application (REQ-7). Does not throw connection reset
        or pipe errors during TDM rotation phases.
        
        Args:
            data: Raw byte payload to transmit.
            
        Returns:
            Number of bytes accepted into the buffer queue.
            
        Raises:
            ConnectionResetError: If logical socket has been explicitly closed by user.
        """
        if self.logical_state != LogicalSocketState.OPEN:
            raise ConnectionResetError(f"VirtualSocket '{self.socket_id}' is closed (state: {self.logical_state})")

        if not data:
            return 0

        # Enqueue outgoing payload into per-stream RAM FIFO without blocking the caller (REQ-6, REQ-7)
        await self._tx_queue.put(data)
        self.total_bytes_sent += len(data)
        logger.debug(
            "Socket '%s' queued %d bytes (tx_depth=%d, physical_state=%s)",
            self.socket_id,
            len(data),
            self.tx_queue_depth,
            self.physical_state.value,
        )
        return len(data)

    async def recv(self, max_bytes: int = 4096) -> bytes:
        """Receive incoming payload from the stream's RX queue.
        
        Awaits data if the queue is empty. Returns empty bytes `b""` if the socket
        is closed and all pending bytes have been consumed (standard POSIX socket EOF).
        
        Args:
            max_bytes: Maximum chunk slice to return.
            
        Returns:
            Received byte payload or b"" on stream termination.
        """
        if self.logical_state == LogicalSocketState.CLOSED and self._rx_queue.empty():
            return b""

        # Await incoming data placed into RX queue by transport pump
        chunk = await self._rx_queue.get()
        self._rx_queue.task_done()
        self.total_bytes_received += len(chunk)
        return chunk[:max_bytes]

    async def close(self) -> None:
        """Gracefully close the virtual socket.
        
        Transitions state to CLOSED and releases waiting tasks.
        """
        async with self._lock:
            if self.logical_state == LogicalSocketState.CLOSED:
                return
            self.logical_state = LogicalSocketState.CLOSED
            self._link_ready_event.clear()
            # Push EOF sentinel to wake any blocking recv() calls
            await self._rx_queue.put(b"")
            logger.info("VirtualSocket '%s' for device '%s' closed", self.socket_id, self.device_id)

    def set_physical_state(self, state: SocketState) -> None:
        """Update physical link state delivered from TDM scheduler / HAL adapter.
        
        Updates state without mutating or dropping logical_state (REQ-5).
        Signals link_ready_event when active, clears it when paused or degraded.
        """
        prev_state = self.physical_state
        self.physical_state = state

        if state == SocketState.ACTIVE_PHYSICAL_LINK:
            # Physical GATT link ready: unblock flushing pumps (REQ-8)
            self._link_ready_event.set()
        else:
            # Paused for rotation or degraded: hold pending data in RAM without dropping (REQ-7)
            self._link_ready_event.clear()

        logger.debug(
            "Socket '%s' physical state transition: %s -> %s",
            self.socket_id,
            prev_state.value,
            state.value,
        )

    async def wait_until_physical_link_ready(self, timeout: Optional[float] = None) -> bool:
        """Wait until underlying physical radio link transitions to ACTIVE_PHYSICAL_LINK.
        
        Args:
            timeout: Maximum seconds to wait (None = wait indefinitely).
            
        Returns:
            True if physical link became ready, False on timeout.
        """
        try:
            if timeout is not None:
                await asyncio.wait_for(self._link_ready_event.wait(), timeout=timeout)
            else:
                await self._link_ready_event.wait()
            return True
        except asyncio.TimeoutError:
            return False

    async def dequeue_tx(self, timeout: Optional[float] = None) -> Optional[bytes]:
        """Internal helper for Session Manager to drain pending chunks for radio transmission.
        
        Args:
            timeout: Maximum seconds to wait for a queued packet.
            
        Returns:
            Next bytes to transmit, or None if queue is empty / timed out.
        """
        try:
            if timeout == 0:
                if not self._tx_queue.empty():
                    chunk = self._tx_queue.get_nowait()
                else:
                    return None
            elif timeout is not None:
                chunk = await asyncio.wait_for(self._tx_queue.get(), timeout=timeout)
            else:
                chunk = await self._tx_queue.get()
            self._tx_queue.task_done()
            return chunk
        except (asyncio.TimeoutError, asyncio.QueueEmpty):
            return None

    async def inject_rx(self, data: bytes) -> None:
        """Internal helper for HAL / Session Manager to inject incoming radio data into socket.
        
        Args:
            data: Payload received over physical GATT characteristic.
        """
        if self.logical_state != LogicalSocketState.CLOSED:
            await self._rx_queue.put(data)
