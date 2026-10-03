"""SessionNode API request and response schemas."""
from pydantic import BaseModel, ConfigDict, Field

from ..models.session_node import NodeState


class SessionNodeCreate(BaseModel):
    """Payload to attach a device to an active session."""
    device_id: str = Field(..., description="ID of registered device to attach")
    priority_rank: int = Field(default=0, ge=0, description="Priority ordering (0 = equal)")


class SessionNodeStatusUpdate(BaseModel):
    """Payload to transition a session node's socket state."""
    status: NodeState = Field(..., description="New socket lifecycle state")


class SessionNodeResponse(BaseModel):
    """Complete session node join document representation returned by API."""
    id: str
    session_id: str
    device_id: str
    priority_rank: int
    status: NodeState

    model_config = ConfigDict(from_attributes=True)
