"""Integration tests for BT-Mux REST API endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "bt-mux-server"
    assert "ble_transport" in data


@pytest.mark.asyncio
async def test_session_lifecycle_api(client: AsyncClient):
    """Test full session creation, retrieval, and status lifecycle."""
    # 1. Create a session
    payload = {
        "test_name": "TDM_Benchmark_Run_01",
        "slice_duration_ms": 300,
        "max_hardware_limit": 4,
    }
    resp = await client.post("/api/sessions", json=payload)
    assert resp.status_code == 201
    created = resp.json()
    session_id = created["id"]
    assert created["test_name"] == "TDM_Benchmark_Run_01"
    assert created["slice_duration_ms"] == 300
    assert created["status"] == "pending"
    assert created["started_at"] is None

    # 2. Get session by ID
    resp = await client.get(f"/api/sessions/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == session_id

    # 3. Transition session to running
    resp = await client.patch(
        f"/api/sessions/{session_id}/status",
        json={"status": "running"},
    )
    assert resp.status_code == 200
    running_data = resp.json()
    assert running_data["status"] == "running"
    assert running_data["started_at"] is not None

    # 4. Transition session to completed
    resp = await client.patch(
        f"/api/sessions/{session_id}/status",
        json={"status": "completed"},
    )
    assert resp.status_code == 200
    completed_data = resp.json()
    assert completed_data["status"] == "completed"
    assert completed_data["ended_at"] is not None

    # 5. List sessions
    resp = await client.get("/api/sessions")
    assert resp.status_code == 200
    sessions = resp.json()
    assert len(sessions) >= 1
    assert any(s["id"] == session_id for s in sessions)


@pytest.mark.asyncio
async def test_session_validation_error(client: AsyncClient):
    """Verify that invalid slice duration (<100ms or >2000ms) is rejected with 422."""
    resp = await client.post(
        "/api/sessions",
        json={"test_name": "Invalid", "slice_duration_ms": 50},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_device_registry_api(client: AsyncClient):
    """Test device registration and query."""
    device_payload = {
        "device_name": "Smart_Sensor_01",
        "device_type": "sensor",
        "mac_address": "AA:BB:CC:DD:EE:01",
    }
    resp = await client.post("/api/devices", json=device_payload)
    assert resp.status_code == 201
    device = resp.json()
    device_id = device["id"]
    assert device["device_name"] == "Smart_Sensor_01"

    # Registering duplicate MAC returns existing record idempotently
    resp_dup = await client.post("/api/devices", json=device_payload)
    assert resp_dup.status_code == 201
    assert resp_dup.json()["id"] == device_id

    # Query device by ID
    resp = await client.get(f"/api/devices/{device_id}")
    assert resp.status_code == 200
    assert resp.json()["mac_address"] == "AA:BB:CC:DD:EE:01"

    # List devices
    resp = await client.get("/api/devices")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_session_nodes_and_telemetry_flow(client: AsyncClient):
    """Test attaching nodes to session, updating states, and telemetry summary recording."""
    # Create session
    s_resp = await client.post(
        "/api/sessions",
        json={"test_name": "Nodes_Test_Session", "slice_duration_ms": 500},
    )
    session_id = s_resp.json()["id"]

    # Register device
    d_resp = await client.post(
        "/api/devices",
        json={
            "device_name": "File_Peer_Node_01",
            "device_type": "file_peer",
            "mac_address": "11:22:33:44:55:66",
        },
    )
    device_id = d_resp.json()["id"]

    # Attach device to session
    node_payload = {
        "device_id": device_id,
        "priority_rank": 1,
    }
    n_resp = await client.post(f"/api/sessions/{session_id}/nodes", json=node_payload)
    assert n_resp.status_code == 201
    node = n_resp.json()
    node_id = node["id"]
    assert node["status"] == "UNINITIALIZED"
    assert node["priority_rank"] == 1

    # Transition socket state to ACTIVE_PHYSICAL_LINK
    n_update = await client.patch(
        f"/api/sessions/{session_id}/nodes/{node_id}/status",
        json={"status": "ACTIVE_PHYSICAL_LINK"},
    )
    assert n_update.status_code == 200
    assert n_update.json()["status"] == "ACTIVE_PHYSICAL_LINK"

    # Record telemetry summary
    t_payload = {
        "total_packets_sent": 500,
        "total_packets_received": 490,
        "pdr": 0.98,
        "average_rtt": 22.5,
        "average_handoff_latency": 130.0,
        "nodes": [
            {"node_id": node_id, "average_rssi": -65.0, "average_rtt": 22.5}
        ],
    }
    t_resp = await client.post(f"/api/sessions/{session_id}/telemetry", json=t_payload)
    assert t_resp.status_code == 201
    telemetry = t_resp.json()
    assert telemetry["pdr"] == 0.98
    assert len(telemetry["nodes"]) == 1

    # Fetch latest telemetry for session
    t_get = await client.get(f"/api/sessions/{session_id}/telemetry")
    assert t_get.status_code == 200
    assert t_get.json()["total_packets_sent"] == 500

    # Delete session (cascades to nodes & telemetry)
    del_resp = await client.delete(f"/api/sessions/{session_id}")
    assert del_resp.status_code == 204

    # Confirm session is gone
    assert (await client.get(f"/api/sessions/{session_id}")).status_code == 404
