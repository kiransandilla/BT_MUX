"""Telemetry API request and response schemas."""
from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict, Field

from ..models.telemetry import NodeMetric


class TelemetryCreate(BaseModel):
    """Payload to record session summary telemetry metrics."""
    total_packets_sent: int = Field(default=0, ge=0)
    total_packets_received: int = Field(default=0, ge=0)
    pdr: float = Field(default=0.0, ge=0.0, le=1.0, description="Packet Delivery Ratio [0.0, 1.0]")
    average_rtt: float = Field(default=0.0, ge=0.0, description="Average RTT in ms")
    average_handoff_latency: float = Field(default=0.0, ge=0.0, description="Average handoff latency in ms")
    nodes: List[NodeMetric] = Field(default_factory=list, description="Per-node metrics")


class TelemetryResponse(BaseModel):
    """Complete telemetry document representation returned by API."""
    id: str
    session_id: str
    total_packets_sent: int
    total_packets_received: int
    pdr: float
    average_rtt: float
    average_handoff_latency: float
    nodes: List[NodeMetric]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
