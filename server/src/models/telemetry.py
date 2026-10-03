"""Telemetry summary data model for session benchmarks.

Authoritative source: BT-Mux_Agent_Instructions.md Section 4 & SRS REQ-12, REQ-13.
"""
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from .common import PyObjectId


class NodeMetric(BaseModel):
    """Per-node aggregate metrics embedded in Telemetry summary.
    
    Fields:
    - node_id: Identifier of the node (SessionNode or Device ID).
    - average_rssi: Mean Received Signal Strength Indication in dBm.
    - average_rtt: Mean round-trip latency in milliseconds.
    """
    node_id: str
    average_rssi: Optional[float] = None
    average_rtt: Optional[float] = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )


class Telemetry(BaseModel):
    """Session summary telemetry document.
    
    Deliberate summary-level representation of session logs (REQ-12).
    Raw per-packet logs are omitted by design (Section 4).
    
    Fields:
    - id / _id: MongoDB document identifier.
    - session_id: Reference to the session.
    - total_packets_sent: Total packet/chunk count sent during session.
    - total_packets_received: Total ACKed/received packet count.
    - pdr: Global Packet Delivery Ratio (0.0 <= pdr <= 1.0, SRS 5.1 target >= 0.95).
    - average_rtt: Global average round-trip time in milliseconds.
    - average_handoff_latency: Mean context-switch handoff latency in milliseconds (SRS 5.1 <= 300ms).
    - nodes: Embedded per-node aggregate metrics.
    - created_at: Timestamp when telemetry record was generated.
    """
    id: Optional[PyObjectId] = Field(None, alias="_id")
    session_id: str
    total_packets_sent: int = Field(default=0, ge=0)
    total_packets_received: int = Field(default=0, ge=0)
    pdr: float = Field(default=0.0, ge=0.0, le=1.0, description="Packet Delivery Ratio [0.0, 1.0]")
    average_rtt: float = Field(default=0.0, ge=0.0, description="Average RTT in ms")
    average_handoff_latency: float = Field(default=0.0, ge=0.0, description="Average handoff latency in ms")
    nodes: list[NodeMetric] = Field(default_factory=list)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC record creation timestamp",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )
