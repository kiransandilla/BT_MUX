"""SessionNode data model joining sessions and devices for a test run.

Authoritative source: BT-Mux_Agent_Instructions.md Section 4 & SRS Appendix B.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from ..config.constants import SocketState
from .common import PyObjectId


class NodeState(str, Enum):
    """Lifecycle state machine for a session node.
    
    Tracks SRS Appendix B:
    UNINITIALIZED -> PAUSED_QUEUED -> CONNECTING -> ACTIVE_PHYSICAL_LINK
    -> PAUSED_QUEUED (on slice-timer expiry)
    -> DEGRADED / DEGRADED_RETRY (on timeout/error)
    
    Note (Section 4): No separate TRANSMITTING sub-state is included.
    ACTIVE_PHYSICAL_LINK remains the single connected state.
    """
    UNINITIALIZED = "UNINITIALIZED"
    PAUSED_QUEUED = "PAUSED_QUEUED"
    CONNECTING = "CONNECTING"
    ACTIVE_PHYSICAL_LINK = "ACTIVE_PHYSICAL_LINK"
    DEGRADED = "DEGRADED"
    DEGRADED_RETRY = "DEGRADED_RETRY"


class SessionNode(BaseModel):
    """SessionNode document joining a session with a target device.
    
    Fields:
    - id / _id: MongoDB document identifier.
    - session_id: Foreign key reference to session _id.
    - device_id: Foreign key reference to device _id.
    - priority_rank: Scheduling priority order (0 = default/equal).
    - status: Virtual socket lifecycle state (NodeState).
    """
    id: Optional[PyObjectId] = Field(None, alias="_id")
    session_id: str
    device_id: str
    priority_rank: int = 0
    status: NodeState = NodeState.UNINITIALIZED

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )
