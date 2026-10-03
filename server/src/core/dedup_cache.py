"""BT-Mux In-Memory Delivery-History Dedup Cache.

Authoritative source: BT-Mux_Agent_Instructions.md Section 4.1 & SRS 5.1.
Maintains a short-lived in-memory cache of COMPLETED chunks per device.
"""
import threading
import time
from typing import Dict, Set

from ..config.constants import DEDUP_CACHE_TTL_SECONDS


class DedupCache:
    """In-memory cache tracking recently completed chunks to avoid redundant retransmission.
    
    When a peripheral disconnects and reconnects during TDM slot rotation, this cache
    ensures the host does not resend chunks that were already acknowledged (Section 4.1).
    This cache is purely a dedup optimization in RAM, not persistence. Expired entries
    are purged to guarantee host memory stays well below the 150 MB ceiling (SRS 5.1).
    """

    def __init__(self, ttl_seconds: int = DEDUP_CACHE_TTL_SECONDS) -> None:
        self.ttl_seconds: int = ttl_seconds
        # Structure: {device_id: {chunk_id: completion_monotonic_time}}
        self._cache: Dict[str, Dict[str, float]] = {}
        self._lock: threading.RLock = threading.RLock()

    def mark_completed(self, device_id: str, chunk_id: str) -> None:
        """Record chunk as completed for target device with current timestamp."""
        with self._lock:
            if device_id not in self._cache:
                self._cache[device_id] = {}
            self._cache[device_id][chunk_id] = time.monotonic()

    def is_completed(self, device_id: str, chunk_id: str) -> bool:
        """Check whether chunk was completed recently within TTL window."""
        with self._lock:
            device_entries = self._cache.get(device_id)
            if not device_entries:
                return False

            recorded_time = device_entries.get(chunk_id)
            if recorded_time is None:
                return False

            # Verify whether entry has expired beyond TTL
            if time.monotonic() - recorded_time > self.ttl_seconds:
                # Purge expired entry immediately
                del device_entries[chunk_id]
                return False

            return True

    def get_completed_chunk_ids(self, device_id: str) -> Set[str]:
        """Return set of valid (unexpired) completed chunk IDs for a device."""
        with self._lock:
            self.cleanup_expired()
            return set(self._cache.get(device_id, {}).keys())

    def cleanup_expired(self) -> int:
        """Purge all expired entries across all devices. Returns number of purged entries."""
        with self._lock:
            now = time.monotonic()
            purged = 0
            devices_to_prune = []

            for device_id, chunk_map in self._cache.items():
                expired_keys = [cid for cid, t in chunk_map.items() if now - t > self.ttl_seconds]
                for cid in expired_keys:
                    del chunk_map[cid]
                    purged += 1
                if not chunk_map:
                    devices_to_prune.append(device_id)

            for dev_id in devices_to_prune:
                del self._cache[dev_id]

            return purged

    def clear(self) -> None:
        """Flush the entire cache."""
        with self._lock:
            self._cache.clear()
