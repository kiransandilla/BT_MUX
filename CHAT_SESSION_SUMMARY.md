# BT-Mux — Session Working Context & Execution Log

**Date / Timestamp**: 2026-10-07T12:35:00+05:30  
**Repository**: `https://github.com/kiransandilla/BT_MUX.git`  
**Workspace**: `E:\College materials\Sem5\BTP`  
**Target Architecture**: User-Space Virtual Socket Multiplexing Middleware for Bluetooth Low Energy (BLE)  

---

## 1. Remote Synchronization & Updates Pulled

### Remote Merge (`origin/main`)
- Executed `git pull origin main` resulting in a fast-forward merge to commit `25e8394` (Merge PR #1 from `manav160/manav-feature`).
- **65 files modified/created (+7,092 / -374 lines)**.

### Core Modules Integrated
1. **Core Scheduling & Multiplexing Engine** (`server/src/core/`):
   - `scheduler.py`: Time-Division Multiplexing (TDM) scheduler with round-robin batch rotation, dynamic $N_{\text{max}}$ hardware slot detection (REQ-1), 1000ms degraded node timeout handling (REQ-4), and runtime $T_{\text{slice}}$ adjustments (REQ-11).
   - `virtual_socket.py`: Transparent user-space RAM FIFO buffering (`asyncio.Queue`) maintaining persistent `OPEN` state across physical GATT connect/disconnect cycles (REQ-5).
   - `session_manager.py`: Session lifecycle manager driving GATT connected flush pumps and in-flight chunk tracking.
   - `buffer.py`, `chunk.py`, `dedup_cache.py`: Chunk segmentation, deduplication cache with 5-minute TTL, and FIFO queue depth monitoring.
   - `csv_export.py`: Telemetry reconciliation generator outputting global PDR, mean RTT, handoff latency, and per-node metrics (REQ-13).

2. **Hardware Abstraction Layer (HAL)** (`server/src/hal/`):
   - `base.py`: Abstract `BLETransport` interface.
   - `simulated.py`: In-memory simulated BLE radio with latency and fault modeling.
   - `bleak_adapter.py`: Physical BLE transport adapter using `bleak` via Windows WinRT / Linux BlueZ D-Bus.
   - `factory.py`: Config-driven adapter factory (`create_ble_transport()`).

3. **API & WebSockets Control Plane** (`server/src/api/`):
   - FastAPI routers for `/api/sessions`, `/api/devices`, `/api/session-nodes`, `/api/telemetry`, and `/api/health`.
   - `ws.py` & `websocket.py`: Real-time WebSocket event broadcaster for slot rotations, buffer queue depths, and node state transitions.

4. **Diagnostic Dashboard** (`client/`):
   - React 18 + Vite frontend with real-time slot gauges, node status visualization ($N \ge 10$ nodes), and dynamic $T_{\text{slice}}$ range slider.

---

## 2. Issues Diagnosed & Resolved

### Issue 1: Windows `ModuleNotFoundError: No module named 'resource'`
- **Root Cause**: The Python standard library `resource` module (`resource.getrusage`) is exclusive to Unix/macOS for POSIX resource limits; it does not exist on Windows. The PyPI package `resource` installed via `pip install resource` is an unrelated third-party library that does not provide `resource.getrusage`.
- **Resolution**:
  - Implemented cross-platform memory tracking function `_get_memory_mb()` using Windows native API via `ctypes.windll.psapi.GetProcessMemoryInfo` (retrieving `WorkingSetSize`) on Windows, with fallback to `resource` on Unix/macOS.
  - Updated `server/src/demo_testbed.py` and `server/tests/test_end_to_end_testbed.py`.
  - Removed invalid dependency `resource>=4.15.0` from `server/requirements.txt`.

### Issue 2: `ModuleNotFoundError: No module named 'src'`
- **Root Cause**: When executing test scripts directly (e.g., `python server/tests/test_end_to_end_testbed.py` or from within `server/tests/`), Python added `server/tests` to `sys.path[0]` instead of `server/`, causing imports from `src...` to fail. Additionally, a manual `import src` statement was temporarily placed before the `sys.path` injection code.
- **Resolution**:
  - Moved `sys.path` injection to execute immediately after importing `sys` and `Path`:
    ```python
    from pathlib import Path
    import sys

    _SERVER_DIR = Path(__file__).resolve().parent.parent
    if str(_SERVER_DIR) not in sys.path:
        sys.path.insert(0, str(_SERVER_DIR))
    ```
  - Added entrypoint in `test_end_to_end_testbed.py` to allow direct execution via `pytest.main()`.
  - Configured `server/tests/conftest.py` with automatic `_SERVER_DIR` path injection.

### Issue 3: Missing Test Dependency `httpx`
- Installed `httpx` in virtual environment (`server/venv`) to satisfy API client requirements in `server/tests/conftest.py`.

---

## 3. Test Suite & Validation Results

### 1. Simulated End-to-End Testbed Suite
- **Command**: `python server/tests/test_end_to_end_testbed.py`
- **Result**: **3 passed in 1.91s (100% PASS)**
  - `test_end_to_end_node_testbed_10_nodes_file_transfer`: **PASSED** (12 logical nodes over 4 physical slots)
  - `test_testbed_short_slice_no_data_loss`: **PASSED** (10ms rapid preemption stress test)
  - `test_late_ack_after_requeue_no_duplicate`: **PASSED** (Late ACK deduplication idempotency)

### 2. Live CLI Benchmark Demonstration
- **Command**: `python server/src/demo_testbed.py`
- **Benchmark Results**:
  - Total Chunks Sent: **60**
  - Total Chunks Acknowledged: **60**
  - Packet Delivery Ratio (PDR): **100.00%** (Target: $\ge 95\%$) $\to$ **PASS**
  - Host RAM Footprint: **32.83 MB** (Ceiling: $< 150\text{ MB}$) $\to$ **PASS**
  - Mean Handoff Latency: **22.50 ms** (Target: $\le 300\text{ ms}$) $\to$ **PASS**
  - Logical Sockets Preserved: **ALL OPEN** (REQ-5) $\to$ **PASS**
  - Telemetry CSV generated: `btmux_benchmark_telemetry.csv`

---

## 4. Real Hardware BLE Integration Artifacts Created

To enable testing against real physical devices (Smartphones & Microcontrollers), the following new tools and firmware were added to the repository:

### 1. [`server/src/scan_ble.py`](file:///e:/College%20materials/Sem5/BTP/server/src/scan_ble.py)
- Standalone CLI scanner using Windows WinRT and `BleakScanner`.
- Discovers physical BLE peripherals in radio range, reports RSSI signal strength, and identifies Nordic UART Service (NUS) advertising packets.
- **Verification**: Executed on host machine; successfully discovered 58 real BLE devices over the air.

### 2. [`server/src/real_device_transfer.py`](file:///e:/College%20materials/Sem5/BTP/server/src/real_device_transfer.py)
- Over-The-Air (OTA) file transfer CLI.
- Connects to physical BLE peripherals via WinRT (`BLETransport`).
- Segments any input file into `Chunk` payloads (20-byte BLE standard MTU frames).
- Dispatches chunks over GATT TX, listens for RX ACKs, displays live percentage and throughput (KB/s), and performs clean disconnection.
- Auto-detects target devices advertising `BT` / `BT_P` / NUS UUID, or prompts interactively.

### 3. [`server/src/demo_12_devices.py`](file:///e:/College%20materials/Sem5/BTP/server/src/demo_12_devices.py)
- Live interactive multiplexing CLI with real-time ASCII matrix dashboard.
- **Four operating modes** (A, B, C, D) covering simulated, hybrid, all-real, and fully dynamic configurations.
- Hardened for Windows console `cp1252` character encoding.
- Generates reconciled telemetry CSV per run.

### 4. [`LIVE_DEMO.md`](file:///e:/College%20materials/Sem5/BTP/LIVE_DEMO.md)
- Complete demonstration playbook for viva/faculty reviews.
- Step-by-step procedures for all 5 demo scenarios: Demo 1 (Single Phone OTA), Demo 2 Modes A–D.
- Includes core examiner talking points (SRS REQ-1, REQ-5, REQ-9, REQ-13).

### 5. [`firmware/esp32_nus_peripheral/esp32_nus_peripheral.ino`](file:///e:/College%20materials/Sem5/BTP/firmware/esp32_nus_peripheral/esp32_nus_peripheral.ino)
- Arduino IDE firmware for ESP32 / ESP32-C3 / ESP32-S3 boards.
- Advertises as `BTMUX_ESP32_01` with Nordic UART Service (NUS).
- Accepts file chunks on RX write characteristic, prints received byte metrics to Serial (115200 baud), and returns `ACK:<chunk_num>` notifications.

### 6. [`firmware/README.md`](file:///e:/College%20materials/Sem5/BTP/firmware/README.md)
- Setup guide for nRF Connect for Mobile and ESP32 hardware flashing.

---

## 5. Quick Reference Commands

### Running the Full System
```bash
# 1. Start Backend REST & WebSocket Server:
python -m uvicorn server.src.main:app --reload --port 8000

# 2. Start React Frontend Dashboard:
cd client && npm run dev
```

### Live Demonstrations
```bash
# Demo 1: Single Phone Real BLE Transfer (auto-detects phone):
python server/src/real_device_transfer.py

# Demo 1 with custom document:
python server/src/real_device_transfer.py --file "PROJECT_STATUS.md"

# Demo 2: 12-Device Simultaneous TDM Multiplexer (Standard Testbed):
python server/src/demo_12_devices.py --slice-ms 400

# Demo 2: Hybrid Mode (Real Smartphone + 11 Virtual Peers):
python server/src/demo_12_devices.py --phone auto
```

---

## 6. Real Hardware Over-the-Air Validation Milestone

- **Physical Target Peripheral**: User Smartphone running nRF Connect (`BT_P` / `BT`, MAC: `6E:B9:EF:52:BF:3A`).
- **Host Radio Driver**: Windows WinRT via Bleak HAL (`BleakTransport`).
- **Connection Type**: Physical GATT connection over 2.4 GHz BLE radio spectrum using `winrt={"address_type": "random"}` for RPA support.
- **Payload**: 1,440 bytes segmented into 72 chunks (20-byte BLE MTU frames).
- **Execution Log**:
  - `[+] Physical GATT connection established successfully!`
  - `[+] Sliced file into 72 chunks.`
  - `[+] Transmitted: 72/72 chunks (100.0% delivery, 1,440 bytes).`
  - `[+] Transmission status: SUCCESS.`
  - `[+] Graceful GATT session teardown.`
- **Live Verification on Phone**:
  - In nRF Connect on Android, navigate to **☰ (Menu) -> Log** to view the real-time incoming GATT write command stream:
    `[Server] Write command received from [Laptop MAC], value: (0x48656C6C6F...) "Hello from BT-Mux!"`

---

## 7. 12-Device Simultaneous Multiplexing Architecture & Validation

- **Implementation**: [`server/src/demo_12_devices.py`](file:///e:/College%20materials/Sem5/BTP/server/src/demo_12_devices.py)
- **Problem Solved**: Standard BLE controllers enforce a hardware constraint of $N_{\text{max}} = 4$ concurrent connections. BT-Mux decouples logical streams from physical radio slots via user-space virtual sockets.
- **Metrics Validated**:
  - Total Concurrent Streams: **$N = 12$ Logical Peripheral Streams (SRS REQ-9)**
  - Physical Radio Allocation: **$N_{\text{max}} = 4$ Slots Max (SRS REQ-1)**
  - Packet Delivery Ratio ($PDR$): **$100.00\%$** (Ceiling: $\ge 95\%$) $\to$ **PASS**
  - Host RAM Footprint: **$33.04\text{ MB}$** (Ceiling: $< 150\text{ MB}$) $\to$ **PASS**
  - Virtual Socket Invariant: **All 12 Virtual Sockets Preserved in `OPEN` State throughout physical GATT disconnect/connect rotations (SRS REQ-5) $\to$ PASS**
  - Telemetry Output: Reconciled into [`btmux_12_device_telemetry.csv`](file:///e:/College%20materials/Sem5/BTP/btmux_12_device_telemetry.csv) (SRS REQ-13).

---

## 8. Mode C: All-Real Devices Simultaneous Transfer (Added 2026-10-12)

### What Was Added
- **New CLI flag** `--all-real` on `server/src/demo_12_devices.py`.
- `scan_and_select_real_devices()`: BLE scan with NUS-prioritised ranking, comma-separated device selection prompt, and Y/n confirmation.
- `run_12_real_devices_demo()`: Full TDM run with all-real nodes — zero simulated peers. Features:
  - Sequential pre-connect with per-device skip-on-failure (graceful degradation).
  - Live ASCII dashboard where every active slot shows `(2.4GHz)` tag.
  - Dashboard header changes to `12-REAL-DEVICE` to clearly distinguish from simulated runs.
  - Per-device PDR table in final report.
  - Separate telemetry CSV: `btmux_12_real_device_telemetry.csv`.
- **LIVE_DEMO.md** updated: Mode C section with hardware table, prompt walkthrough, dashboard screenshot, post-transfer report preview.

### Quick Reference
```powershell
python server/src/demo_12_devices.py --all-real
python server/src/demo_12_devices.py --all-real --file "PROJECT_STATUS.md"
```

---

## 9. Mode D: Dynamic Real Devices — Interactive N & N_max (Added 2026-10-12)

### What Was Added
- **New CLI flag** `--dynamic` on `server/src/demo_12_devices.py`.
- `_prompt_n_max(n_devices)`: Validates and returns user-chosen N_max (1 ≤ N_max ≤ N).
- `run_dynamic_real_devices_demo()`: Full TDM session where **both N and N_max are set at runtime**:
  - BLE scan with no upper device limit (up to whatever is in range).
  - User picks exactly which devices (any subset).
  - User enters desired N_max with contextual explanation printed inline.
  - Configuration summary printed before run: N, N_max, multiplexing ratio, T_slice.
  - Live dashboard footer shows `[Config] N=X devices | N_max=Y slots | Ratio=Z.Wx | T_slice=T ms` on every frame.
  - Final report includes `Multiplexing ratio: Zx` in the N_max line.
  - CSV filename encodes parameters: `btmux_dynamic_telemetry_N{N}_Nmax{N_max}.csv`.
- **LIVE_DEMO.md** updated: Mode D section with complete interactive prompt walkthrough, dashboard example with config footer, viva talking-point callout.
- **Overview table** in LIVE_DEMO.md updated with Mode D row.
- **Cheat-sheet** updated with Mode D commands.

### Viva Demonstration Strategy
| Scenario | N | N_max | What It Proves |
| :--- | :--- | :--- | :--- |
| Extreme TDM | 3 | 1 | Radio handles 1 link, BT-Mux keeps 3 sockets OPEN |
| Standard thesis | 5 | 2 | 2.5× multiplexing ratio over real hardware |
| Full concurrency | 4 | 4 | All slots occupied — baseline comparison |

### Quick Reference
```powershell
python server/src/demo_12_devices.py --dynamic
python server/src/demo_12_devices.py --dynamic --file "PROJECT_STATUS.md"
```

---
*Context export updated: 2026-10-12T20:48:00+05:30*
