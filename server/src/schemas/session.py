"""Session API request and response schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from ..config.constants import (
    DEFAULT_T_SLICE_MS,
    N_MAX_PHYSICAL_DEFAULT,
    T_SLICE_MAX_MS,
    T_SLICE_MIN_MS,
)
from ..models.session import SessionStatus


class SessionCreate(BaseModel):
    """Payload to initialize a new experiment session."""
    test_name: str = Field(..., description="Descriptive name of the test run")
    slice_duration_ms: int = Field(
        default=DEFAULT_T_SLICE_MS,
        ge=T_SLICE_MIN_MS,
        le=T_SLICE_MAX_MS,
        description="TDM time-slice duration in milliseconds (100 <= x <= 2000, SRS REQ-2)",
    )
    max_hardware_limit: int = Field(
        default=N_MAX_PHYSICAL_DEFAULT,
        ge=1,
        description="Maximum physical radio connection capacity (N_max, SRS REQ-1)",
    )


class SessionStatusUpdate(BaseModel):
    """Payload to update an existing session's status."""
    status: SessionStatus


class SessionResponse(BaseModel):
    """Complete session document representation returned by API."""
    id: str
    test_name: str
    slice_duration_ms: int
    max_hardware_limit: int
    status: SessionStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
