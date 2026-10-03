"""Unit tests for StreamBuffer dedicated per-stream FIFO queue (REQ-6, REQ-7, REQ-8)."""
import pytest

from src.config.constants import ChunkState
from src.core.buffer import StreamBuffer
from src.core.chunk import Chunk
from src.core.dedup_cache import DedupCache


@pytest.mark.asyncio
async def test_stream_buffer_enqueue_dequeue():
    """Verify standard FIFO buffering and dispatching."""
    buf = StreamBuffer(device_id="dev_01")
    chunk_1 = Chunk.create(media_id="m1", sequence_number=0, payload=b"chunk1")
    chunk_2 = Chunk.create(media_id="m1", sequence_number=1, payload=b"chunk2")

    assert await buf.enqueue(chunk_1) is True
    assert await buf.enqueue(chunk_2) is True
    assert buf.queue_depth == 2
    assert buf.in_flight_count == 0

    # Dequeue for transmission
    dispatched_1 = await buf.dequeue_for_transmission()
    assert dispatched_1.chunk_id == chunk_1.chunk_id
    assert dispatched_1.state == ChunkState.SENT
    assert buf.queue_depth == 1
    assert buf.in_flight_count == 1

    dispatched_2 = await buf.dequeue_for_transmission()
    assert dispatched_2.chunk_id == chunk_2.chunk_id
    assert buf.queue_depth == 0
    assert buf.in_flight_count == 2


@pytest.mark.asyncio
async def test_stream_buffer_ack_advances_to_completed_and_dedup():
    """Verify explicit remote ACK moves chunk to COMPLETED and populates dedup cache."""
    cache = DedupCache(ttl_seconds=300)
    buf = StreamBuffer(device_id="dev_01", dedup_cache=cache)
    chunk = Chunk.create(media_id="m1", sequence_number=0, payload=b"test_ack")

    await buf.enqueue(chunk)
    dispatched = await buf.dequeue_for_transmission()
    assert dispatched.state == ChunkState.SENT

    # ACK received
    assert await buf.handle_ack(chunk.chunk_id) is True
    assert dispatched.state == ChunkState.COMPLETED
    assert buf.in_flight_count == 0
    assert cache.is_completed("dev_01", chunk.chunk_id) is True

    # Re-enqueueing the same completed chunk should now be rejected as duplicate
    re_enqueued = await buf.enqueue(chunk)
    assert re_enqueued is False
    assert buf.queue_depth == 0


@pytest.mark.asyncio
async def test_stream_buffer_nack_requeues_to_retry():
    """Verify NACK or timeout transitions chunk to RETRY and places back into queue."""
    buf = StreamBuffer(device_id="dev_01")
    chunk = Chunk.create(media_id="m1", sequence_number=0, payload=b"retry_test")

    await buf.enqueue(chunk)
    dispatched = await buf.dequeue_for_transmission()
    assert buf.in_flight_count == 1

    # NACK or timeout
    assert await buf.handle_nack_or_timeout(chunk.chunk_id) is True
    assert buf.in_flight_count == 0
    assert buf.queue_depth == 1
    assert chunk.state == ChunkState.RETRY

    # Can be dequeued again
    re_dispatched = await buf.dequeue_for_transmission()
    assert re_dispatched.chunk_id == chunk.chunk_id


@pytest.mark.asyncio
async def test_stream_buffer_requeue_all_in_flight_on_slot_rotation():
    """Verify all in-flight chunks are saved and retried when physical slot expires."""
    buf = StreamBuffer(device_id="dev_01")
    for i in range(3):
        chunk = Chunk.create(media_id="m1", sequence_number=i, payload=f"data_{i}".encode())
        await buf.enqueue(chunk)
        await buf.dequeue_for_transmission()

    assert buf.in_flight_count == 3
    assert buf.queue_depth == 0

    # TDM slot expires before ACKs returned -> requeue all in flight
    requeued_count = await buf.requeue_all_in_flight()
    assert requeued_count == 3
    assert buf.in_flight_count == 0
    assert buf.queue_depth == 3
