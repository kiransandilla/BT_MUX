"""Unit tests for VirtualSocket abstraction (SRS REQ-5, REQ-6, REQ-7, REQ-10)."""
import asyncio
import pytest

from src.config.constants import SocketState
from src.core.virtual_socket import LogicalSocketState, VirtualSocket


@pytest.mark.asyncio
async def test_virtual_socket_initialization():
    """Verify virtual socket initialization and defaults."""
    sock = VirtualSocket(device_id="dev_01", session_id="sess_01")
    assert sock.device_id == "dev_01"
    assert sock.session_id == "sess_01"
    assert sock.is_active is True
    assert sock.is_physical_link_active is False
    assert sock.logical_state == LogicalSocketState.OPEN
    assert sock.physical_state == SocketState.UNINITIALIZED
    assert sock.tx_queue_depth == 0
    assert sock.rx_queue_depth == 0
    assert sock.total_bytes_sent == 0
    assert sock.total_bytes_received == 0


@pytest.mark.asyncio
async def test_virtual_socket_send_buffers_in_ram():
    """Verify outgoing payloads buffer in RAM without dropping on physical disconnect (REQ-5, REQ-7)."""
    sock = VirtualSocket(device_id="dev_01", session_id="sess_01")

    # Set physical state to PAUSED_QUEUED (simulating TDM duty-cycle rotation phase)
    sock.set_physical_state(SocketState.PAUSED_QUEUED)
    assert sock.is_physical_link_active is False
    assert sock.is_active is True  # Logical connection remains active to app (REQ-5)

    # Send payload while physical link is disconnected/paused
    payload1 = b"chunk_data_01"
    payload2 = b"chunk_data_02"
    sent1 = await sock.send(payload1)
    sent2 = await sock.send(payload2)

    assert sent1 == len(payload1)
    assert sent2 == len(payload2)
    assert sock.tx_queue_depth == 2  # Buffered in RAM FIFO (REQ-6, REQ-7)
    assert sock.total_bytes_sent == len(payload1) + len(payload2)


@pytest.mark.asyncio
async def test_virtual_socket_fifo_drain_order():
    """Verify FIFO ordering when draining TX queue."""
    sock = VirtualSocket(device_id="dev_01", session_id="sess_01")
    await sock.send(b"first")
    await sock.send(b"second")
    await sock.send(b"third")

    assert await sock.dequeue_tx() == b"first"
    assert await sock.dequeue_tx() == b"second"
    assert await sock.dequeue_tx() == b"third"
    assert sock.tx_queue_depth == 0

    # Dequeue from empty queue returns None with timeout
    assert await sock.dequeue_tx(timeout=0.01) is None


@pytest.mark.asyncio
async def test_virtual_socket_recv_and_rx_injection():
    """Verify receiving incoming payloads via RX queue."""
    sock = VirtualSocket(device_id="dev_01", session_id="sess_01")

    # Inject data from simulated transport
    await sock.inject_rx(b"received_packet_01")
    await sock.inject_rx(b"received_packet_02")
    assert sock.rx_queue_depth == 2

    # Receive data
    r1 = await sock.recv()
    r2 = await sock.recv()
    assert r1 == b"received_packet_01"
    assert r2 == b"received_packet_02"
    assert sock.total_bytes_received == len(b"received_packet_01") + len(b"received_packet_02")


@pytest.mark.asyncio
async def test_virtual_socket_physical_link_synchronization():
    """Verify physical link state event synchronization."""
    sock = VirtualSocket(device_id="dev_01", session_id="sess_01")

    # Initially not ready
    assert await sock.wait_until_physical_link_ready(timeout=0.01) is False

    # Transition to ACTIVE_PHYSICAL_LINK
    sock.set_physical_state(SocketState.ACTIVE_PHYSICAL_LINK)
    assert sock.is_physical_link_active is True
    assert await sock.wait_until_physical_link_ready(timeout=0.05) is True

    # Transition to PAUSED_QUEUED
    sock.set_physical_state(SocketState.PAUSED_QUEUED)
    assert sock.is_physical_link_active is False
    assert await sock.wait_until_physical_link_ready(timeout=0.01) is False


@pytest.mark.asyncio
async def test_virtual_socket_close_semantics():
    """Verify socket close, exception on send, and EOF semantics on recv."""
    sock = VirtualSocket(device_id="dev_01", session_id="sess_01")
    await sock.close()

    assert sock.is_active is False
    assert sock.logical_state == LogicalSocketState.CLOSED

    # Sending on closed socket raises ConnectionResetError
    with pytest.raises(ConnectionResetError):
        await sock.send(b"dropped_data")

    # Recv on closed socket returns EOF b""
    assert await sock.recv() == b""
