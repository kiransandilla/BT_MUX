"""BT-Mux Grounding Constants and State Enums.

Authoritative source: SRS (BT Mux - 3rd Year Project) & BT-Mux_Agent_Instructions.md.
"""
from enum import Enum

# ==============================================================================
# 1. System Scaling & Hardware Limits (SRS 1.4, 2.7)
# ==============================================================================
N_LOGICAL_TARGET: int = 10
"""Target number of persistent logical streams (N >= 10, SRS 1.4)."""

N_MAX_PHYSICAL_DEFAULT: int = 4
"""Default baseline host physical GATT connection limit (range 4–7, SRS 1.4, 2.7, REQ-1)."""

# ==============================================================================
# 2. Timing & Scheduler Constraints (SRS REQ-2, SRS 2.5, SRS REQ-4)
# ==============================================================================
T_SLICE_MIN_MS: int = 100
"""Minimum TDM slice duration in milliseconds (SRS REQ-2)."""

T_SLICE_MAX_MS: int = 2000
"""Maximum TDM slice duration in milliseconds (SRS REQ-2)."""

DEFAULT_T_SLICE_MS: int = 500
"""Default TDM slice duration in milliseconds."""

RECONNECT_LATENCY_MIN_MS: int = 100
"""Physical reconnection latency lower bound in milliseconds (SRS 2.5)."""

RECONNECT_LATENCY_MAX_MS: int = 300
"""Physical reconnection latency upper bound in milliseconds (SRS 2.5)."""

DEGRADED_TIMEOUT_MS: int = 1000
"""Degraded peripheral transition timeout before retry in milliseconds (SRS REQ-4)."""

# ==============================================================================
# 3. Performance & Resource Targets (SRS 5.1)
# ==============================================================================
HANDOFF_LATENCY_TARGET_MS: int = 300
"""Target upper bound for handoff latency in milliseconds (SRS 5.1)."""

PDR_TARGET: float = 0.95
"""Packet Delivery Ratio target (>= 95% at N=10, SRS 5.1)."""

MEMORY_FOOTPRINT_LIMIT_MB: int = 150
"""Host memory footprint ceiling in megabytes (< 150 MB, SRS 5.1)."""

# ==============================================================================
# 4. Cache & Buffer Optimization Parameters (Section 4.1)
# ==============================================================================
DEDUP_CACHE_TTL_SECONDS: int = 300
"""Short-lived in-memory chunk delivery-history cache TTL (5 minutes, Section 4.1)."""


# ==============================================================================
# 5. Socket Lifecycle State Machine (SRS Appendix B & Section 4)
# ==============================================================================
class SocketState(str, Enum):
    """Virtual socket lifecycle states as defined in SRS Appendix B.
    
    Lifecycle flow:
    UNINITIALIZED -> PAUSED_QUEUED -> CONNECTING -> ACTIVE_PHYSICAL_LINK
    -> PAUSED_QUEUED (on slice-timer expiry)
    -> DEGRADED_RETRY (on timeout/error)
    """
    UNINITIALIZED = "UNINITIALIZED"
    PAUSED_QUEUED = "PAUSED_QUEUED"
    CONNECTING = "CONNECTING"
    ACTIVE_PHYSICAL_LINK = "ACTIVE_PHYSICAL_LINK"
    DEGRADED_RETRY = "DEGRADED_RETRY"


# ==============================================================================
# 6. Chunk Delivery State Machine (Section 4.1)
# ==============================================================================
class ChunkState(str, Enum):
    """Chunk delivery states for application-layer file transfer (Section 4.1).
    
    Flow:
    PENDING -> SENT -> (ACK received) -> COMPLETED
                    -> (no ACK)       -> RETRY
    """
    PENDING = "PENDING"
    SENT = "SENT"
    COMPLETED = "COMPLETED"
    RETRY = "RETRY"
