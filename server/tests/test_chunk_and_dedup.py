"""Unit tests for Chunk model and DedupCache (Section 4.1)."""
import time
from src.config.constants import ChunkState
from src.core.chunk import Chunk
from src.core.dedup_cache import DedupCache


def test_chunk_creation_and_checksum():
    """Verify chunk generation with automatic SHA-256 and size computation."""
    payload = b"Hello, BT-Mux Multi-Peer Chunk!"
    chunk = Chunk.create(media_id="file_01", sequence_number=0, payload=payload)

    assert chunk.media_id == "file_01"
    assert chunk.sequence_number == 0
    assert chunk.size == len(payload)
    assert chunk.payload == payload
    assert chunk.state == ChunkState.PENDING
    assert len(chunk.checksum) == 64  # SHA-256 hex digest length


def test_chunk_lifecycle_states():
    """Verify valid chunk state transitions per Section 4.1."""
    chunk = Chunk.create(media_id="m1", sequence_number=1, payload=b"test")
    assert chunk.state == ChunkState.PENDING

    chunk.mark_sent()
    assert chunk.state == ChunkState.SENT

    chunk.mark_completed()
    assert chunk.state == ChunkState.COMPLETED

    # Reset to retry
    chunk.mark_retry()
    assert chunk.state == ChunkState.RETRY


def test_dedup_cache_hit_and_miss():
    """Verify in-memory dedup tracking per target device."""
    cache = DedupCache(ttl_seconds=10)
    dev_a = "device_A"
    dev_b = "device_B"
    chunk_1 = "chunk_01"

    # Initially missing
    assert cache.is_completed(dev_a, chunk_1) is False

    # Mark completed for Device A
    cache.mark_completed(dev_a, chunk_1)
    assert cache.is_completed(dev_a, chunk_1) is True
    # Should not mark completed for Device B (per-device separation)
    assert cache.is_completed(dev_b, chunk_1) is False


def test_dedup_cache_ttl_expiration():
    """Verify entries expire and are pruned after TTL window."""
    # Use very short TTL of 0.05 seconds for test speed
    cache = DedupCache(ttl_seconds=0.05)
    dev = "device_01"
    cid = "chunk_expiring"

    cache.mark_completed(dev, cid)
    assert cache.is_completed(dev, cid) is True

    # Sleep slightly past TTL
    time.sleep(0.06)
    assert cache.is_completed(dev, cid) is False

    # Cleanup method cleans up empty maps
    cache.mark_completed(dev, "chunk_2")
    time.sleep(0.06)
    purged = cache.cleanup_expired()
    assert purged >= 1
    assert dev not in cache._cache
