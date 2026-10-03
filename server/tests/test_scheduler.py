"""Unit tests for TDMScheduler batch rotation, timing, and degraded node handling (REQ-1/2/3/4/11)."""
import asyncio
import pytest

from src.config.constants import SocketState
from src.core.scheduler import TDMScheduler
from src.core.session_manager import SessionManager
from tests.mock_transport import MockTransport


@pytest.mark.asyncio
async def test_scheduler_dynamic_n_max_detection():
    """Verify scheduler dynamically queries N_max from transport (REQ-1)."""
    transport_4 = MockTransport(max_connections=4)
    sm = SessionManager(session_id="s1")
    sched_4 = TDMScheduler(transport=transport_4, session_manager=sm)
    assert sched_4.n_max == 4

    transport_7 = MockTransport(max_connections=7)
    sched_7 = TDMScheduler(transport=transport_7, session_manager=sm)
    assert sched_7.n_max == 7


@pytest.mark.asyncio
async def test_scheduler_t_slice_clamp_and_dynamic_update():
    """Verify T_slice bounds [100, 2000] and runtime dynamic adjustment (REQ-2, REQ-11)."""
    transport = MockTransport(max_connections=4)
    sm = SessionManager(session_id="s1")
    sched = TDMScheduler(transport=transport, session_manager=sm, t_slice_ms=500)
    assert sched.t_slice_ms == 500

    # Dynamic update within bounds (REQ-11)
    sched.set_t_slice_ms(800)
    assert sched.t_slice_ms == 800

    # Clamp below minimum (<100ms)
    sched.set_t_slice_ms(50)
    assert sched.t_slice_ms == 100

    # Clamp above maximum (>2000ms)
    sched.set_t_slice_ms(2500)
    assert sched.t_slice_ms == 2000


@pytest.mark.asyncio
async def test_scheduler_round_robin_batch_rotation():
    """Verify round-robin batch rotation across N >= 10 logical nodes (REQ-2, REQ-3)."""
    transport = MockTransport(max_connections=3)
    sm = SessionManager(session_id="s_rr")
    sched = TDMScheduler(
        transport=transport,
        session_manager=sm,
        t_slice_ms=100,  # Fast 100ms slice for test
    )

    # Register 6 nodes (Batch 1: n0, n1, n2; Batch 2: n3, n4, n5)
    for i in range(6):
        sched.register_node(f"node_{i}")

    # Initial order
    assert sched.node_queue == ["node_0", "node_1", "node_2", "node_3", "node_4", "node_5"]

    # Execute single step rotation
    await sched.step_rotation()

    # After step 1: batch 1 (node_0, node_1, node_2) was evaluated and rotated to the back
    assert sched.node_queue == ["node_3", "node_4", "node_5", "node_0", "node_1", "node_2"]
    # All slots gracefully disconnected after slice window (REQ-3)
    assert len(sched.active_slots) == 0
    assert len(transport.connected_devices) == 0

    # Execute step 2: batch 2 rotated to back
    await sched.step_rotation()
    assert sched.node_queue == ["node_0", "node_1", "node_2", "node_3", "node_4", "node_5"]


@pytest.mark.asyncio
async def test_scheduler_degraded_node_bypass_on_failure():
    """Verify failing/timeout peripheral is flagged DEGRADED and bypassed without stalling (REQ-4)."""
    transport = MockTransport(max_connections=2)
    transport.failing_devices.add("failing_node")

    sm = SessionManager(session_id="s_deg")
    sched = TDMScheduler(
        transport=transport,
        session_manager=sm,
        t_slice_ms=100,
        degraded_timeout_ms=50,  # Low timeout for test speed
    )

    sched.register_node("failing_node")
    sched.register_node("healthy_node_1")
    sched.register_node("healthy_node_2")

    # Step rotation
    await sched.step_rotation()

    # Failing node is flagged as degraded (REQ-4)
    assert "failing_node" in sched.degraded_nodes
    failing_sock = sm.get_socket("failing_node")
    assert failing_sock.physical_state == SocketState.DEGRADED_RETRY

    # Healthy node succeeded and rotated
    assert "healthy_node_1" not in sched.degraded_nodes
    # Failing node is rotated to back to retry on next cycle
    assert sched.node_queue[-2:] == ["failing_node", "healthy_node_1"]


@pytest.mark.asyncio
async def test_scheduler_background_start_and_stop():
    """Verify starting and stopping scheduler lifecycle loop."""
    transport = MockTransport(max_connections=2)
    sm = SessionManager(session_id="s_lifecycle")
    sched = TDMScheduler(
        transport=transport,
        session_manager=sm,
        t_slice_ms=100,
    )
    sched.register_node("node_a")
    sched.register_node("node_b")

    await sched.start()
    assert sched._running is True
    assert sched._loop_task is not None

    # Let it run 1 rotation
    await asyncio.sleep(0.15)

    await sched.stop()
    assert sched._running is False
    assert len(sched.active_slots) == 0
