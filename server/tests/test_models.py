"""Unit tests for BT-Mux Pydantic v2 schemas and Motor ODM serialization."""
import pytest
from bson import ObjectId
from datetime import datetime, timezone
from pydantic import ValidationError

from src.models import (
    Device,
    NodeMetric,
    NodeState,
    PyObjectId,
    Session,
    SessionNode,
    SessionStatus,
    Telemetry,
)
from src.config.constants import (
    DEFAULT_T_SLICE_MS,
    N_MAX_PHYSICAL_DEFAULT,
    T_SLICE_MAX_MS,
    T_SLICE_MIN_MS,
)


class TestSessionModel:
    """Tests for Session model."""

    def test_session_defaults(self):
        session = Session(test_name="MultiPeer_Transfer_Test")
        assert session.test_name == "MultiPeer_Transfer_Test"
        assert session.slice_duration_ms == DEFAULT_T_SLICE_MS
        assert session.max_hardware_limit == N_MAX_PHYSICAL_DEFAULT
        assert session.status == SessionStatus.PENDING
        assert session.created_at is not None
        assert session.started_at is None
        assert session.ended_at is None
        assert session.id is None

    def test_session_slice_duration_boundaries(self):
        # Valid lower bound
        s_min = Session(test_name="MinSlice", slice_duration_ms=T_SLICE_MIN_MS)
        assert s_min.slice_duration_ms == 100

        # Valid upper bound
        s_max = Session(test_name="MaxSlice", slice_duration_ms=T_SLICE_MAX_MS)
        assert s_max.slice_duration_ms == 2000

        # Below lower bound (<100ms)
        with pytest.raises(ValidationError):
            Session(test_name="TooSmall", slice_duration_ms=99)

        # Above upper bound (>2000ms)
        with pytest.raises(ValidationError):
            Session(test_name="TooBig", slice_duration_ms=2001)

    def test_session_mongo_objectid_parsing(self):
        oid = ObjectId()
        session = Session(_id=oid, test_name="Mongo_Oid_Test")
        assert session.id == str(oid)

        # Dump with alias for MongoDB insertion
        dump = session.model_dump(by_alias=True, exclude_none=True)
        assert dump["_id"] == str(oid)
        assert dump["test_name"] == "Mongo_Oid_Test"
        assert dump["status"] == "pending"


class TestDeviceModel:
    """Tests for Device model."""

    def test_device_creation(self):
        device = Device(
            device_name="Peripheral_01",
            device_type="file_peer",
            mac_address="AA:BB:CC:DD:EE:01",
        )
        assert device.device_name == "Peripheral_01"
        assert device.device_type == "file_peer"
        assert device.mac_address == "AA:BB:CC:DD:EE:01"
        assert device.id is None

    def test_device_with_objectid(self):
        oid = ObjectId()
        device = Device.model_validate({
            "_id": oid,
            "device_name": "Sensor_02",
            "device_type": "sensor",
            "mac_address": "AA:BB:CC:DD:EE:02",
        })
        assert device.id == str(oid)
        dump = device.model_dump(by_alias=True)
        assert dump["_id"] == str(oid)


class TestSessionNodeModel:
    """Tests for SessionNode model."""

    def test_session_node_lifecycle_states(self):
        node = SessionNode(
            session_id="session_123",
            device_id="device_456",
        )
        assert node.status == NodeState.UNINITIALIZED
        assert node.priority_rank == 0

        # Test valid state transitions
        for state in [
            NodeState.PAUSED_QUEUED,
            NodeState.CONNECTING,
            NodeState.ACTIVE_PHYSICAL_LINK,
            NodeState.DEGRADED,
            NodeState.DEGRADED_RETRY,
        ]:
            node.status = state
            assert node.status == state

    def test_session_node_invalid_state_rejection(self):
        with pytest.raises(ValidationError):
            SessionNode(
                session_id="session_123",
                device_id="device_456",
                status="TRANSMITTING",  # Specifically rejected in design instructions
            )


class TestTelemetryModel:
    """Tests for Telemetry model and NodeMetric subdocuments."""

    def test_telemetry_defaults(self):
        telemetry = Telemetry(session_id="session_123")
        assert telemetry.session_id == "session_123"
        assert telemetry.total_packets_sent == 0
        assert telemetry.total_packets_received == 0
        assert telemetry.pdr == 0.0
        assert telemetry.average_rtt == 0.0
        assert telemetry.average_handoff_latency == 0.0
        assert telemetry.nodes == []
        assert telemetry.created_at is not None

    def test_telemetry_with_node_metrics(self):
        node_1 = NodeMetric(node_id="node_01", average_rssi=-62.5, average_rtt=18.4)
        node_2 = NodeMetric(node_id="node_02", average_rssi=-70.1, average_rtt=24.1)

        telemetry = Telemetry(
            session_id="session_123",
            total_packets_sent=1000,
            total_packets_received=980,
            pdr=0.98,
            average_rtt=21.25,
            average_handoff_latency=145.0,
            nodes=[node_1, node_2],
        )

        assert telemetry.pdr == 0.98
        assert len(telemetry.nodes) == 2
        assert telemetry.nodes[0].average_rssi == -62.5
        assert telemetry.nodes[1].node_id == "node_02"

        dump = telemetry.model_dump(by_alias=True)
        assert len(dump["nodes"]) == 2
        assert dump["pdr"] == 0.98

    def test_telemetry_pdr_bounds(self):
        # Valid PDR bounds [0.0, 1.0]
        Telemetry(session_id="s1", pdr=0.0)
        Telemetry(session_id="s1", pdr=1.0)

        # Invalid bounds
        with pytest.raises(ValidationError):
            Telemetry(session_id="s1", pdr=-0.01)

        with pytest.raises(ValidationError):
            Telemetry(session_id="s1", pdr=1.01)
