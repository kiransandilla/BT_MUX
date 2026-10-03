"""BT-Mux Concurrency and Race-Condition Hardening Test Suite (Step 11).

Tests multi-task concurrency, asynchronous slot preemption, rapid mid-transmission T_slice
cancellations, dedup cache thread safety, and per-stream queue isolation.
"""
import asyncio
import pytest

from src.config.constants import ChunkState, SocketState
from src.core.buffer import StreamBuffer
from src.core.chunk import Chunk
from src.core.dedup_cache import DedupCache
from src.core.scheduler import TDMScheduler
from src.core.session_manager import SessionManager
from src.core.virtual_socket import LogicalSocketState, VirtualSocket
from src.hal.simulated import SimulatedTransport


@pytest.mark.asyncio
async def test_concurrent_enqueue_dequeue_stress():
    """Verify StreamBuffer remains consistent under heavy concurrent producer-consumer loads."""
    buf = StreamBuffer(device_id="DEV_STRESS_1")
    total_chunks = 100
    produced_chunks = [
        Chunk.create(media_id="file1", sequence_number=i, payload=f"data_{i}".encode())
        for i in range(total_chunks)
    ]

    async def producer():
        for chk in produced_chunks:
            await buf.enqueue(chk)
            await asyncio.sleep(0.0001)

    dispatched = []

    async def consumer():
        while len(dispatched) < total_chunks:
            chk = await buf.dequeue_for_transmission(timeout=0.2)
            if chk:
                dispatched.append(chk)
                # Randomly simulate ACK after short delay
                await asyncio.sleep(0.0001)
                await buf.handle_ack(chk.chunk_id)

    await asyncio.gather(producer(), consumer())

    assert len(dispatched) == total_chunks
    assert buf.queue_depth == 0
    assert buf.in_flight_count == 0


@pytest.mark.asyncio
async def test_slot_preemption_mid_transmission_requeues_in_flight():
    """Verify that when a slot expires mid-transmission, all in-flight chunks safely revert to RETRY."""
    session_mgr = SessionManager(session_id="SESS_PREEMPT")
    dev_id = "DEV_PREEMPT_1"
    sock = session_mgr.get_or_create_socket(dev_id)
    buf = session_mgr.get_buffer(dev_id)

    # Populate 10 chunks in buffer
    for i in range(10):
        c = Chunk.create("stream", i, f"payload_{i}".encode())
        await buf.enqueue(c)

    # Simulate link connection
    await session_mgr.on_physical_link_connected(dev_id)
    assert sock.physical_state == SocketState.ACTIVE_PHYSICAL_LINK

    # Dequeue 3 chunks into in-flight state
    c1 = await buf.dequeue_for_transmission(timeout=0.1)
    c2 = await buf.dequeue_for_transmission(timeout=0.1)
    c3 = await buf.dequeue_for_transmission(timeout=0.1)

    assert c1 is not None and c2 is not None and c3 is not None
    assert buf.in_flight_count == 3
    assert c1.state == ChunkState.SENT

    # Preempt slot (T_slice expires -> on_physical_link_paused)
    await session_mgr.on_physical_link_paused(dev_id)

    # Verify socket is still logically open in RAM but physical link is paused
    assert sock.logical_state == LogicalSocketState.OPEN
    assert sock.physical_state == SocketState.PAUSED_QUEUED

    # Verify in-flight count cleared and unconfirmed chunks re-enqueued to RETRY (REQ-7)
    assert buf.in_flight_count == 0
    assert c1.state == ChunkState.RETRY
    assert c2.state == ChunkState.RETRY
    assert c3.state == ChunkState.RETRY
    # Initial 10 chunks: 3 dequeued and re-enqueued + 7 remaining = 10 total depth
    assert buf.queue_depth == 10

    await session_mgr.close()


@pytest.mark.asyncio
async def test_rapid_tdm_slot_rotation_with_continuous_sending():
    """Simulate high-speed TDM slot rotations (T_slice=50ms) with multiple active nodes."""
    transport = SimulatedTransport(max_connections=2, handshake_delay_sec=0.005, transmission_delay_sec=0.002)
    session_mgr = SessionManager(session_id="SESS_RAPID")
    nodes = [f"NODE_{i:02d}" for i in range(6)]

    scheduler = TDMScheduler(
        transport=transport,
        session_manager=session_mgr,
        t_slice_ms=50,  # fast rotation
    )
    for n in nodes:
        scheduler.register_node(n)
        session_mgr.get_or_create_socket(n)

    # Start continuous background sending on all virtual sockets
    stop_event = asyncio.Event()

    async def sender(node_id: str):
        sock = session_mgr.get_socket(node_id)
        seq = 0
        while not stop_event.is_set():
            try:
                await sock.send(f"msg_{seq}".encode())
                seq += 1
                await asyncio.sleep(0.01)
            except Exception:
                break

    sender_tasks = [asyncio.create_task(sender(n)) for n in nodes]

    # Run scheduler for 300ms (multiple rotations across 6 nodes with N_max=2)
    await scheduler.start()
    await asyncio.sleep(0.35)
    await scheduler.stop()

    stop_event.set()
    await asyncio.gather(*sender_tasks, return_exceptions=True)

    # Verify all sockets remain cleanly OPEN in user space
    for n in nodes:
        sock = session_mgr.get_socket(n)
        assert sock.logical_state == LogicalSocketState.OPEN
        assert sock.total_bytes_sent > 0

    await session_mgr.close()


@pytest.mark.asyncio
async def test_concurrent_dedup_cache_access():
    """Verify thread-safe concurrent reads and writes to DedupCache."""
    cache = DedupCache(ttl_seconds=10)
    dev_id = "DEV_DEDUP_CONCURRENT"

    async def writer(start_idx: int):
        for i in range(start_idx, start_idx + 50):
            cache.mark_completed(dev_id, f"chk_{i}")
            await asyncio.sleep(0.0001)

    async def reader():
        completed = 0
        for _ in range(50):
            for i in range(200):
                if cache.is_completed(dev_id, f"chk_{i}"):
                    completed += 1
            await asyncio.sleep(0.0001)
        return completed

    writers = [writer(i * 50) for i in range(4)]
    readers = [reader() for _ in range(2)]

    await asyncio.gather(*writers, *readers)

    # Cache should now hold 200 items cleanly without corruptions
    completed_ids = cache.get_completed_chunk_ids(dev_id)
    assert len(completed_ids) == 200
