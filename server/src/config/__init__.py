"""BT-Mux Configuration and Constants Package."""
from .constants import (
    N_LOGICAL_TARGET,
    N_MAX_PHYSICAL_DEFAULT,
    T_SLICE_MIN_MS,
    T_SLICE_MAX_MS,
    DEFAULT_T_SLICE_MS,
    RECONNECT_LATENCY_MIN_MS,
    RECONNECT_LATENCY_MAX_MS,
    DEGRADED_TIMEOUT_MS,
    HANDOFF_LATENCY_TARGET_MS,
    PDR_TARGET,
    MEMORY_FOOTPRINT_LIMIT_MB,
    DEDUP_CACHE_TTL_SECONDS,
    SocketState,
    ChunkState,
)
from .settings import Settings, get_settings

__all__ = [
    "N_LOGICAL_TARGET",
    "N_MAX_PHYSICAL_DEFAULT",
    "T_SLICE_MIN_MS",
    "T_SLICE_MAX_MS",
    "DEFAULT_T_SLICE_MS",
    "RECONNECT_LATENCY_MIN_MS",
    "RECONNECT_LATENCY_MAX_MS",
    "DEGRADED_TIMEOUT_MS",
    "HANDOFF_LATENCY_TARGET_MS",
    "PDR_TARGET",
    "MEMORY_FOOTPRINT_LIMIT_MB",
    "DEDUP_CACHE_TTL_SECONDS",
    "SocketState",
    "ChunkState",
    "Settings",
    "get_settings",
]
