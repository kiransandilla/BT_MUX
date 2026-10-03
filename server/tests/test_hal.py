"""Unit tests for Hardware Abstraction Layer (HAL) adapters and factory (SRS 2.5, 5.4, REQ-1)."""
import asyncio
import pytest

from src.core.scheduler import TDMScheduler
from src.core.session_manager import SessionManager
from src.hal import (
    BLETransport,
    BleakTransport,
    SimulatedTransport,
    create_ble_transport,
)


def test_factory_creates_simulated_transport():
    """Verify factory returns SimulatedTransport when configured."""
    transport = create_ble_transport(transport_mode="simulated")
    assert isinstance(transport, SimulatedTransport)
    assert isinstance(transport, BLETransport)
    assert transport.get_max_connections() == 4


def test_factory_creates_bleak_transport():
    """Verify factory returns BleakTransport for winrt or linux-bluez."""
    t_winrt = create_ble_transport(transport_mode="winrt")
    assert isinstance(t_winrt, BleakTransport)
    assert isinstance(t_winrt, BLETransport)

    t_linux = create_ble_transport(transport_mode="linux-bluez")
    assert isinstance(t_linux, BleakTransport)
    assert isinstance(t_linux, BLETransport)


def test_factory_raises_on_invalid_mode():
    """Verify factory raises ValueError on unsupported transport mode."""
    with pytest.raises(ValueError, match="Unknown BLE_TRANSPORT mode"):
        create_ble_transport(transport_mode="unsupported_driver")


@pytest.mark.asyncio
async def test_simulated_transport_lifecycle():
    """Verify connect, send, event dispatch, and disconnect on SimulatedTransport."""
    transport = SimulatedTransport(handshake_delay_sec=0.005, transmission_delay_sec=0.005)
    dev_id = "sim_node_01"

    connected_events = []
    transport.on("connected", lambda d: connected_events.append(d))

    disconnected_events = []
    transport.on("disconnected", lambda d: disconnected_events.append(d))

    received_data = []
    transport.on("data", lambda d, data: received_data.append((d, data)))

    # Connect
    await transport.connect(dev_id)
    assert dev_id in transport.connected_devices
    assert dev_id in connected_events

    # Send
    await transport.send(dev_id, b"test_payload")
    assert (dev_id, b"test_payload") in transport.transmitted_history

    # Inject incoming data
    transport.inject_incoming_data(dev_id, b"incoming_resp")
    assert (dev_id, b"incoming_resp") in received_data

    # Disconnect
    await transport.disconnect(dev_id)
    assert dev_id not in transport.connected_devices
    assert dev_id in disconnected_events


@pytest.mark.asyncio
async def test_simulated_transport_scan():
    """Verify scan returns simulated peripheral metadata."""
    transport = SimulatedTransport()
    devices = await transport.scan_for_devices()
    assert len(devices) == 12
    assert devices[0]["device_id"] == "sim_node_00"


@pytest.mark.asyncio
async def test_scheduler_runs_identically_on_simulated_transport():
    """Verify TDMScheduler runs full batch rotation on SimulatedTransport with ZERO code changes (HAL Section 5)."""
    transport = SimulatedTransport(max_connections=3, handshake_delay_sec=0.005)
    sm = SessionManager(session_id="session_hal_eval")
    sched = TDMScheduler(
        transport=transport,
        session_manager=sm,
        t_slice_ms=100,
    )

    # Register 6 simulated nodes
    for i in range(6):
        sched.register_node(f"sim_node_{i:02d}")

    # Run one full rotation step
    await sched.step_rotation()

    # Batch rotated successfully with zero special cases
    assert sched.node_queue == [
        "sim_node_03", "sim_node_04", "sim_node_05",
        "sim_node_00", "sim_node_01", "sim_node_02",
    ]
    assert len(transport.connected_devices) == 0  # Gracefully disconnected after slot
