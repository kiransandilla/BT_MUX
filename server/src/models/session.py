"""Session data model for BT-Mux experiments.

Authoritative source: BT-Mux_Agent_Instructions.md Section 4 & SRS REQ-2.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from ..config.constants import (
    DEFAULT_T_SLICE_MS,
    N_MAX_PHYSICAL_DEFAULT,
    T_SLICE_MAX_MS,
    T_SLICE_MIN_MS,
)
from .common import PyObjectId


class SessionStatus(str, Enum):
    """Lifecycle status of an experiment session."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"


class Session(BaseModel):
    """Session document representing one experiment or test run.
    
    Fields:
    - id / _id: MongoDB document identifier.
    - test_name: Descriptive name for the test run.
    - slice_duration_ms: TDM time-slice window duration (100ms <= T_slice <= 2000ms, SRS REQ-2).
    - max_hardware_limit: Host physical GATT connection limit (N_max, default 4).
    - status: Current session status (pending, running, completed).
    - created_at: Timestamp when session was registered.
    - started_at: Timestamp when session execution began.
    - ended_at: Timestamp when session execution finalized.
    """
    id: Optional[PyObjectId] = Field(None, alias="_id")
    test_name: str
    slice_duration_ms: int = Field(
        default=DEFAULT_T_SLICE_MS,
        ge=T_SLICE_MIN_MS,
        le=T_SLICE_MAX_MS,
        description="TDM time-slice duration in milliseconds (100 <= x <= 2000, SRS REQ-2)",
    )
    max_hardware_limit: int = Field(
        default=N_MAX_PHYSICAL_DEFAULT,
        ge=1,
        description="Maximum concurrent physical GATT radio connections (N_max, default 4)",
    )
    status: SessionStatus = SessionStatus.PENDING
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC creation timestamp",
    )
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )
