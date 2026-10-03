# Traceability Matrix

| REQ ID | Feature / Module | Target File(s) | Status |
|--------|------------------|----------------|--------|
| REQ-01 | Environment & SRS Constants Setup | `server/src/config/constants.py` | Done |
| REQ-12 | Motor & Pydantic v2 Schemas (Session, Device, SessionNode, Telemetry) | `server/src/models/`, `server/src/db/` | Done |
| REQ-02 / REQ-12 | FastAPI Backend Skeleton & Control Plane REST Routes | `server/src/api/`, `server/src/main.py` | Done |
| REQ-05 / REQ-06 / REQ-07 | Virtual Socket Abstraction & RAM FIFO Queuing | `server/src/core/virtual_socket.py` | Done |
| REQ-06 / REQ-07 / REQ-08 | Session Manager, Dedicated RAM Buffer, Dedup Cache & Auto-Flush Pump | `server/src/core/buffer.py`, `server/src/core/chunk.py`, `server/src/core/session_manager.py` | Done |
| REQ-01 / REQ-02 / REQ-03 / REQ-04 / REQ-11 | TDM Scheduler (Dynamic N_max, Batch Rotation, Graceful Disconnect, Degraded Node Handling, Dynamic T_slice) | `server/src/core/scheduler.py`, `server/src/core/transport.py` | Done |
| SRS 2.5 / 5.4 / REQ-01 | Hardware Abstraction Layer (HAL) Adapters & Factory (SimulatedTransport, BleakTransport) | `server/src/hal/` | Done |
| REQ-09 / REQ-10 | WebSocket Real-Time Event Broadcaster (Slot Rotations, Queue Depths, Telemetry) | `server/src/api/websocket.py`, `server/src/api/routers/ws.py` | Done |
| REQ-09 / REQ-10 / REQ-11 | React Diagnostic Dashboard (Node Canvas, Real-Time Profiler, Dynamic T_slice Control) | `client/src/App.jsx`, `client/src/App.css`, `client/src/api.js` | Done |
| REQ-13 | Telemetry Benchmark Recording & CSV Export Generator | `server/src/core/csv_export.py`, `server/src/api/routers/telemetry.py` | Done |
| REQ-06 / REQ-07 / REQ-08 | Concurrency Hardening & Async Slot Preemption Safety | `server/src/core/session_manager.py`, `server/src/core/dedup_cache.py`, `server/tests/test_concurrency.py` | Done |
| REQ-01 / REQ-09 / REQ-13 / SRS 5.1 | Simulated Node Testbed Validation & Live Demo CLI (12 nodes, 4 slots, file transfer benchmark, 100% PDR, CSV export) | `server/tests/test_end_to_end_testbed.py`, `server/src/demo_testbed.py` | Done |
