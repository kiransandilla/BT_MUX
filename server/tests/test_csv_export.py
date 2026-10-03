"""Unit tests for Telemetry CSV Export (SRS REQ-13)."""
import pytest
from httpx import AsyncClient

from src.core.csv_export import generate_telemetry_csv


def test_generate_telemetry_csv_content():
    """Verify CSV formatting includes session metadata, global aggregates, and node breakdowns."""
    session = {
        "id": "sess_export_01",
        "test_name": "MultiPeer_Evaluation_Run",
        "slice_duration_ms": 300,
        "max_hardware_limit": 4,
        "status": "completed",
        "created_at": "2026-10-03T12:00:00Z",
    }
    telemetry = {
        "total_packets_sent": 1000,
        "total_packets_received": 985,
        "pdr": 0.985,
        "average_rtt": 22.4,
        "average_handoff_latency": 142.1,
        "nodes": [
            {"node_id": "node_01", "average_rssi": -62.0, "average_rtt": 21.0},
            {"node_id": "node_02", "average_rssi": -68.5, "average_rtt": 23.8},
        ],
    }
    nodes = [
        {"device_id": "node_01", "priority_rank": 0, "status": "ACTIVE_PHYSICAL_LINK"},
        {"device_id": "node_02", "priority_rank": 1, "status": "PAUSED_QUEUED"},
    ]

    csv_text = generate_telemetry_csv(session, telemetry, nodes)

    assert "Session ID,sess_export_01" in csv_text
    assert "Test Name,MultiPeer_Evaluation_Run" in csv_text
    assert "Packet Delivery Ratio (PDR),98.50%,>= 95% at N=10 (SRS 5.1)" in csv_text
    assert "Average Handoff Overhead,142.10 ms,<= 300 ms (SRS 5.1)" in csv_text
    assert "node_01,0,ACTIVE_PHYSICAL_LINK,-62.0,21.0" in csv_text
    assert "node_02,1,PAUSED_QUEUED,-68.5,23.8" in csv_text


@pytest.mark.asyncio
async def test_csv_export_endpoint(client: AsyncClient):
    """Verify GET /api/sessions/{session_id}/export/csv endpoint returns downloadable CSV."""
    # 1. Create a session
    s_resp = await client.post(
        "/api/sessions",
        json={"test_name": "CSV_Endpoint_Test", "slice_duration_ms": 400},
    )
    session_id = s_resp.json()["id"]

    # 2. Attach a node
    d_resp = await client.post(
        "/api/devices",
        json={"device_name": "Dev_CSV", "device_type": "sensor", "mac_address": "AA:BB:CC:99:88:77"},
    )
    device_id = d_resp.json()["id"]

    await client.post(f"/api/sessions/{session_id}/nodes", json={"device_id": device_id})

    # 3. Post telemetry
    await client.post(
        f"/api/sessions/{session_id}/telemetry",
        json={
            "total_packets_sent": 200,
            "total_packets_received": 196,
            "pdr": 0.98,
            "average_rtt": 19.5,
            "average_handoff_latency": 150.0,
            "nodes": [{"node_id": device_id, "average_rssi": -64.0, "average_rtt": 19.5}],
        },
    )

    # 4. Request CSV export
    export_resp = await client.get(f"/api/sessions/{session_id}/export/csv")
    assert export_resp.status_code == 200
    assert "text/csv" in export_resp.headers["content-type"]
    assert f"btmux_telemetry_{session_id}.csv" in export_resp.headers["content-disposition"]

    csv_body = export_resp.text
    assert "CSV_Endpoint_Test" in csv_body
    assert "98.00%" in csv_body
    assert device_id in csv_body
