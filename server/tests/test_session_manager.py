"""Unit tests for SessionManager, multi-stream coordination, and auto-flushing pump."""
import asyncio
import pytest

from src.config.constants import SocketState
from src.core.session_manager import SessionManager


@pytest.mark.asyncio
async def test_session_manager_multi_stream_instantiation():
    """Verify session manager maintains N >= 10 persistent logical streams (SRS 1.4)."""
    sm = SessionManager(session_id="session_bench_01")

    # Instantiate 12 logical nodes (exceeding physical radio limit N_max=4)
    for i in range(12):
        sock = sm.get_or_create_socket(f"device_{i:02d}")
        assert sock.is_active is True
        assert sock.device_id == f"device_{i:02d}"

    assert len(sm.sockets) == 12
    assert len(sm.buffers) == 12
    await sm.close()


@pytest.mark.asyncio
async def test_session_manager_auto_flush_pump_on_gatt_connected():
    """Verify pending RAM buffer bytes are automatically flushed upon GATT_CONNECTED (REQ-8)."""
    transmitted_packets = []

    async def mock_transport_send(device_id: str, data: bytes) -> None:
        transmitted_packets.append((device_id, data))

    sm = SessionManager(
        session_id="session_test_flush",
        transport_send_fn=mock_transport_send,
    )
    dev_id = "target_peripheral_01"
    sock = sm.get_or_create_socket(dev_id)

    # 1. Application queues bytes into VirtualSocket while physical link is disconnected / paused
    sock.set_physical_state(SocketState.PAUSED_QUEUED)
    await sock.send(b"queued_payload_01")
    await sock.send(b"queued_payload_02")
    assert sock.tx_queue_depth == 2
    assert len(transmitted_packets) == 0

    # 2. Physical GATT connection established -> on_physical_link_connected (REQ-8)
    await sm.on_physical_link_connected(dev_id)
    assert sock.is_physical_link_active is True

    # 3. Allow pump to execute cooperative loop
    await asyncio.sleep(0.08)

    # Verify both packets were automatically flushed and delivered across HAL
    assert len(transmitted_packets) == 2
    assert transmitted_packets[0] == (dev_id, b"queued_payload_01")
    assert transmitted_packets[1] == (dev_id, b"queued_payload_02")
    assert sock.tx_queue_depth == 0

    await sm.close()


@pytest.mark.asyncio
async def test_session_manager_pause_and_rotation():
    """Verify TDM slot expiration halts pump and preserves logical socket (REQ-5, REQ-7)."""
    sm = SessionManager(session_id="session_rotation")
    dev_id = "device_rot_01"
    sock = sm.get_or_create_socket(dev_id)

    await sm.on_physical_link_connected(dev_id)
    assert sock.is_physical_link_active is True

    # Slot expires -> pause for rotation
    await sm.on_physical_link_paused(dev_id)
    assert sock.is_physical_link_active is False
    assert sock.is_active is True  # Logical connection remains intact (REQ-5)
    assert sock.physical_state == SocketState.PAUSED_QUEUED
    assert dev_id not in sm._flush_tasks

    await sm.close()


@pytest.mark.asyncio
async def test_session_manager_degraded_node_handling():
    """Verify timeout/failure flags node as DEGRADED_RETRY (REQ-4)."""
    sm = SessionManager(session_id="session_degraded")
    dev_id = "device_failing_01"
    sock = sm.get_or_create_socket(dev_id)

    await sm.on_physical_link_connected(dev_id)
    await sm.on_physical_link_degraded(dev_id)

    assert sock.physical_state == SocketState.DEGRADED_RETRY
    assert sock.is_physical_link_active is False
    assert sock.is_active is True  # Application socket still open for retry
    assert dev_id not in sm._flush_tasks

    await sm.close()
