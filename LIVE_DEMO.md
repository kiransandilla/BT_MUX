# BT-Mux — Live Demonstration Playbook

**Target Audience**: Academic Viva Committee / Faculty Reviewers  
**Project**: BT-Mux User-Space Virtual Socket BLE Multiplexer  
**Repository**: `https://github.com/kiransandilla/BT_MUX.git`

---

## Demonstration Overview

| Demo | Purpose | Hardware Required | Script |
| :--- | :--- | :--- | :--- |
| **Demo 1: Single Real Device OTA Transfer** | Proves real physical 2.4 GHz BLE transmission to a smartphone over Windows WinRT. | 1 Laptop + 1 Phone (nRF Connect) | `server/src/real_device_transfer.py` |
| **Demo 2 — Mode A: Standard Testbed** | Proves the core BT-Mux thesis: $N = 12$ logical streams over $N_{\text{max}} = 4$ slots via TDM batch rotations. | Laptop only (standalone) | `server/src/demo_12_devices.py` |
| **Demo 2 — Mode B: Hybrid** | Real smartphone as Node 0 + 11 virtual peers in the same TDM scheduler. | 1 Laptop + 1 Phone (nRF Connect) | `server/src/demo_12_devices.py --phone auto` |
| **Demo 2 — Mode C: 12 Real Devices** | All 12 nodes are real physical BLE peripherals — no simulation whatsoever. Maximum hardware proof. | 1 Laptop + up to 12 BLE devices | `server/src/demo_12_devices.py --all-real` |
| **Demo 2 — Mode D: Dynamic N & N_max** | You choose N (device count) **and** N_max (slot ceiling) interactively at runtime. Best for customised viva scenarios. | 1 Laptop + any number of BLE devices | `server/src/demo_12_devices.py --dynamic` |

---

# Demo 1: Single Real Device Over-The-Air Transfer

This demonstration proves that your laptop transmits actual binary file chunks over physical Bluetooth radio frequencies directly into your smartphone.

### Step 1: Prepare Your Phone (nRF Connect)
1. Open **nRF Connect for Mobile** on your phone.
2. In the **ADVERTISER** tab, verify your **`BT_P`** (or `BT`) card has its toggle switch **ON**.
   - *Settings Check*: `Connectable: ON`, `Complete Local Name: BT`, `Service UUID: 6e400001-b5a3-f393-e0a9-e50e24dcca9e`.
3. Tap the **☰ (Menu)** icon at the top-left of nRF Connect $\to$ Tap **Log**.
4. **Keep this Log screen open and visible on your phone screen during the demo.**

### Step 2: Start the Transfer from Your Laptop
Open PowerShell at project root and run:

```powershell
python server/src/real_device_transfer.py
```

The script runs an active BLE scan, automatically highlights your phone, and prompts:
```text
[+] Detected 1 target BT-Mux peripheral(s):
  [1] 6E:B9:EF:52:BF:3A - BT (-66 dBm) [TARGET]

Press Enter to connect to [6E:B9:EF:52:BF:3A] or enter number [1]:
```

**Press Enter**.

### Step 3: What to Show the Faculty
1. **On the Laptop Terminal**: Show the live chunk-by-chunk transmission progress:
   ```text
   [*] Connecting to physical peripheral 6E:B9:EF:52:BF:3A...
   [+] Physical GATT connection established successfully!

   [*] Starting over-the-air chunk transmission...
       [Chunk 72/ 72] Sent:  1440/ 1440 bytes (100.0%)
   ```
2. **On the Phone Screen**: Show the nRF Connect **Log** tab streaming the incoming chunks in real time:
   ```text
   [Server] Write command received from [Laptop MAC], value: (0x48656C6C6F...) "Hello from BT-Mux!"
   ```

### (Optional) Transfer a Custom Named File
To demonstrate transferring an actual project document:
```powershell
python server/src/real_device_transfer.py --file "PROJECT_STATUS.md"
```
Or create a custom file with your roll number and send it:
```powershell
"BT-Mux Live Viva Transfer: Kiran Sandilla - Sem 5 BTP" | Out-File -Encoding utf8 my_demo.txt
python server/src/real_device_transfer.py --file "my_demo.txt"
```

---

# Demo 2: 12-Device Simultaneous Multiplexing Demonstration

This is the **primary academic demonstration**. It shows how BT-Mux breaks the physical hardware constraint ($N_{\text{max}} = 4$ slots) to support $N = 12$ simultaneous logical streams without dropping any sockets.

### Mode A: Standard Testbed Demo (Recommended for Projector Presentations)
Runs a clean, high-visibility 12-node visual dashboard in the terminal without requiring 12 physical phones in the room:

```powershell
python server/src/demo_12_devices.py
```

#### For Slower, Clear Visual Pacing:
To allow the committee to observe each TDM time-slice batch rotation clearly, slow down the slice window:
```powershell
python server/src/demo_12_devices.py --slice-ms 500 --chunks 8
```

#### What Appears Live on Screen:
The terminal displays an interactive real-time ASCII matrix updating as the TDM scheduler rotates through the physical slots:
```text
======================================================================================
      BT-MUX: 12-DEVICE VIRTUAL SOCKET TIME-DIVISION MULTIPLEXER
      Time Elapsed:  1.20s | Physical Radio Limit: N_max = 4 Slots
======================================================================================
  Slot 1: PEER_NODE_04  |  Slot 2: PEER_NODE_05  |  Slot 3: PEER_NODE_06  |  Slot 4: PEER_NODE_07
--------------------------------------------------------------------------------------
  Node Identifier    Socket (OS)  Queue   Completed    Progress Bar       Physical Link
  ----------------------------------------------------------------------------------
  PEER_NODE_00       OPEN         0        6/6        [==============] PAUSED (TDM QUEUE)
  PEER_NODE_01       OPEN         0        6/6        [==============] PAUSED (TDM QUEUE)
  PEER_NODE_02       OPEN         0        6/6        [==============] PAUSED (TDM QUEUE)
  PEER_NODE_03       OPEN         0        6/6        [==============] PAUSED (TDM QUEUE)
  PEER_NODE_04       OPEN         0        3/6        [=======.......] ACTIVE (GATT)
  PEER_NODE_05       OPEN         0        3/6        [=======.......] ACTIVE (GATT)
  PEER_NODE_06       OPEN         0        3/6        [=======.......] ACTIVE (GATT)
  PEER_NODE_07       OPEN         0        3/6        [=======.......] ACTIVE (GATT)
  PEER_NODE_08       OPEN         6        0/6        [..............] PAUSED (TDM QUEUE)
  PEER_NODE_09       OPEN         6        0/6        [..............] PAUSED (TDM QUEUE)
  PEER_NODE_10       OPEN         6        0/6        [..............] PAUSED (TDM QUEUE)
  PEER_NODE_11       OPEN         6        0/6        [..............] PAUSED (TDM QUEUE)
======================================================================================
  [*] Notice: All 12 Virtual Sockets remain continuously OPEN in user space.
======================================================================================
```

---

### Mode B: Hybrid Mode (Your Real Phone + 11 Virtual Peers)
Demonstrates your physical smartphone acting as Node 0 (`PEER_NODE_00*`), while Nodes 1–11 are simulated peers in the same TDM scheduler:

1. Turn on the **`BT_P`** advertiser on your phone.
2. Run:
   ```powershell
   python server/src/demo_12_devices.py --phone auto
   ```
   *(Or specify your phone's address: `python server/src/demo_12_devices.py --phone "6E:B9:EF:52:BF:3A"`)*

#### What Happens in Hybrid Mode:
- **Batch 1**: Physical Slot 1 connects to your **real smartphone over the air**, transmitting actual chunks to your phone, while Slots 2, 3, and 4 transmit to virtual peers.
- **Batch 2 & 3**: Your phone's physical link is cleanly paused, while its user-space virtual socket remains **`OPEN`**. The radio rotates to peers 4–7 and 8–11.
- **Next Rotation**: Physical Slot 1 reconnects to your phone and resumes transmission seamlessly!

---

### Mode C: 12 Real Devices Simultaneous Transfer

This is the **strongest possible hardware proof**. Every one of the 12 nodes is a real physical BLE peripheral — smartphones, ESP32 boards, or any BLE device advertising the Nordic UART Service (NUS). There are **zero simulated nodes**.

#### Hardware You Need
| Quantity | Device | Requirement |
| :--- | :--- | :--- |
| Up to 12 | Smartphones, ESP32 boards, or any BLE device | Must be powered on, advertising, and in BLE range (~5 m) |
| 1 | Laptop (Windows / Linux / macOS) | Running BT-Mux `server/venv` Python environment |

> **Tip for viva**: Even 3–4 real phones is impressive. The script lets you confirm exactly which devices to include before anything is transmitted.

#### Step 1: Prepare All Your BLE Devices
1. On **each phone** running nRF Connect:
   - Open the **ADVERTISER** tab → ensure `BT_P` (or `BT`) advertiser toggle is **ON**.
2. On **each ESP32** board: flash the `firmware/esp32_nus_peripheral/esp32_nus_peripheral.ino` sketch and power on.
3. Bring all devices within ~5 metres of your laptop.

#### Step 2: Run Mode C
```powershell
# Default: auto-scan 6s, send generated test payload
python server/src/demo_12_devices.py --all-real

# Transfer a named project file to all real devices
python server/src/demo_12_devices.py --all-real --file "PROJECT_STATUS.md"

# Longer scan window (10s) for slower-advertising devices
python server/src/demo_12_devices.py --all-real --scan-sec 10
```

#### Step 3: Device Selection Prompt
The script scans the radio and presents every discovered BLE device. NUS/BT-Mux devices are labelled `[NUS/BT-Mux]` and ranked first:
```text
[*] Scanning for nearby BLE peripherals (6s, active mode)...

[+] Discovered 14 BLE device(s):
  [ 1] 6E:B9:EF:52:BF:3A  BT_P                  -55 dBm  [NUS/BT-Mux]
  [ 2] C4:DE:E2:1A:3B:5F  BTMUX_ESP32_01        -61 dBm  [NUS/BT-Mux]
  [ 3] A1:23:45:67:89:AB  OnePlus 11             -68 dBm
  [ 4] D3:45:FC:21:AA:00  Samsung Galaxy S23     -71 dBm
  ...

Select up to 12 device numbers (comma-separated), or press Enter to use top 12:
  > 1,2,3,4

[+] Confirmed 4 real device(s) for simultaneous transfer:
    6E:B9:EF:52:BF:3A  (BT_P)
    C4:DE:E2:1A:3B:5F  (BTMUX_ESP32_01)
    A1:23:45:67:89:AB  (OnePlus 11)
    D3:45:FC:21:AA:00  (Samsung Galaxy S23)

Proceed? [Y/n]: Y
```

#### Step 4: Live Dashboard (What to Show Faculty)
The terminal switches to a real-time ASCII matrix. Every slot tag reads `(2.4GHz)` — proving all links are over-the-air:
```text
======================================================================================
      BT-MUX: 12-REAL-DEVICE VIRTUAL SOCKET TIME-DIVISION MULTIPLEXER
      Time Elapsed:  3.40s | Physical Radio Limit: N_max = 4 Slots
======================================================================================
  Slot 1: 6E:B9:EF:52:BF:3A (2.4GHz)  |  Slot 2: C4:DE:E2:1A:3B:5F (2.4GHz)  ...
--------------------------------------------------------------------------------------
  Node Identifier        Socket   Queue   Done       Progress Bar       Physical Link
  ----------------------------------------------------------------------------------
  6E:B9:EF:52:BF:3A*     OPEN     0       48/48      [==============]  PAUSED (TDM QUEUE)
  C4:DE:E2:1A:3B:5F*     OPEN     0       32/48      [=========.....] ACTIVE (2.4GHz)
  A1:23:45:67:89:AB*     OPEN     12      0/48       [..............] PAUSED (TDM QUEUE)
  D3:45:FC:21:AA:00*     OPEN     12      0/48       [..............] PAUSED (TDM QUEUE)
======================================================================================
  [*] All 4 nodes (*) are REAL physical BLE peripherals transmitting over 2.4 GHz.
  [*] Notice: All Virtual Sockets remain continuously OPEN in user space.
======================================================================================
```

#### Step 5: Post-Transfer Report
At the end the script prints a **per-device PDR breakdown** and writes `btmux_12_real_device_telemetry.csv`:
```text
======================================================================================
             MODE C — REAL 12-DEVICE SIMULTANEOUS TRANSFER REPORT
======================================================================================
Real Physical Devices:          4 (connected: 4)
Physical GATT Slots (N_max):    4 (hardware ceiling)
Total File Chunks Transmitted:  192 / 192
Packet Delivery Ratio (PDR):    100.00%  (Target: >= 95.0%) -> PASS
User-Space RAM Footprint:       34.21 MB -> PASS
Logical Virtual Sockets:        ALL PRESERVED OPEN (REQ-5 PASS)
Total Duration:                 18.74 seconds
--------------------------------------------------------------------------------------
  Device MAC             Chunks Sent    PDR
  ----------------------------------------------
  6E:B9:EF:52:BF:3A     48/48          100.0%
  C4:DE:E2:1A:3B:5F     48/48          100.0%
  A1:23:45:67:89:AB     48/48          100.0%
  D3:45:FC:21:AA:00     48/48          100.0%
======================================================================================
[+] Telemetry CSV written: btmux_12_real_device_telemetry.csv
```

> **On each phone/device screen**: Open the nRF Connect **Log** tab to see the incoming GATT write stream arriving in real time from your laptop.

---

### Mode D: Dynamic Real Devices — Interactive N & N_max

This is the **most flexible mode for a viva**. You interactively choose:
- **N** — how many real BLE devices to include (from 1 up to however many are in range)
- **N_max** — how many physical GATT slots the TDM scheduler is allowed to use simultaneously

This lets you live-demonstrate the *multiplexing ratio* ($N / N_{\text{max}}$) to committee members on demand.

#### Hardware You Need
| Quantity | Device | Requirement |
| :--- | :--- | :--- |
| 1–N | Smartphones, ESP32 boards, or any BLE NUS device | Powered on, advertising, in range |
| 1 | Laptop (Windows / Linux / macOS) | Running BT-Mux `server/venv` Python environment |

> **Tip for viva**: Start with N=3, N_max=1 to show extreme TDM: *"The radio can only hold 1 connection at a time, but BT-Mux keeps all 3 sockets permanently OPEN."* Then re-run with N_max=3 for comparison.

#### Step 1: Prepare BLE Devices
Same as Mode C — ensure each phone/ESP32 has its advertiser **ON**.

#### Step 2: Run Mode D
```powershell
# Interactive session (scan → pick devices → choose N_max):
python server/src/demo_12_devices.py --dynamic

# Transfer a real file in dynamic mode:
python server/src/demo_12_devices.py --dynamic --file "PROJECT_STATUS.md"

# Longer scan window (10 s):
python server/src/demo_12_devices.py --dynamic --scan-sec 10
```

#### Step 3: Interactive Prompts Walkthrough
```text
======================================================================================
      BT-MUX — MODE D: DYNAMIC REAL DEVICES (INTERACTIVE N & N_max)
      Select any number of real BLE devices + your own N_max ceiling
======================================================================================
[*] Scanning for nearby BLE peripherals (6s, active mode)...

[+] Discovered 5 BLE device(s):
  [ 1] 6E:B9:EF:52:BF:3A  BT_P                  -55 dBm  [NUS/BT-Mux]
  [ 2] C4:DE:E2:1A:3B:5F  BTMUX_ESP32_01        -61 dBm  [NUS/BT-Mux]
  [ 3] A1:23:45:67:89:AB  OnePlus 11             -68 dBm
  [ 4] D3:45:FC:21:AA:00  Samsung Galaxy S23     -71 dBm
  [ 5] F7:90:12:34:56:78  Pixel 8 Pro            -75 dBm

Select up to 99 device numbers (comma-separated), or press Enter to use top 99:
  > 1,2,3,4,5

[+] Confirmed 5 real device(s) for simultaneous transfer:
    ...
Proceed? [Y/n]: Y

  Physical BLE controllers have a hardware connection ceiling (N_max).
  BT-Mux multiplexes ALL 5 logical streams over N_max physical slots.
  A smaller N_max (e.g. 2) proves stronger multiplexing; larger (e.g. 5) runs all-at-once.

  Enter N_max (physical GATT slots, 1 – 5) [default 4]: 2
  [>] N_max set to 2 — BT-Mux will rotate 5 streams over 2 slot(s).

[>] Session configuration:
    Real Devices (N)  : 5
    Physical Slots    : N_max = 2
    Multiplexing Ratio: 2.5x  (TDM active — slots share the radio)
    T_slice           : 400 ms
```

#### Step 4: Live Dashboard
The config line appears below every dashboard frame during the run:
```text
======================================================================================
      BT-MUX: 12-REAL-DEVICE VIRTUAL SOCKET TIME-DIVISION MULTIPLEXER
      Time Elapsed:  2.80s | Physical Radio Limit: N_max = 2 Slots
======================================================================================
  Slot 1: 6E:B9:EF:52:BF:3A (2.4GHz)  |  Slot 2: C4:DE:E2:1A:3B:5F (2.4GHz)
--------------------------------------------------------------------------------------
  Node Identifier        Socket   Queue   Done       Progress Bar       Physical Link
  6E:B9:EF:52:BF:3A*     OPEN     0       24/32      [=========.....] ACTIVE (2.4GHz)
  C4:DE:E2:1A:3B:5F*     OPEN     0       16/32      [=======.......] ACTIVE (2.4GHz)
  A1:23:45:67:89:AB*     OPEN     32      0/32       [..............] PAUSED (TDM QUEUE)
  D3:45:FC:21:AA:00*     OPEN     32      0/32       [..............] PAUSED (TDM QUEUE)
  F7:90:12:34:56:78*     OPEN     32      0/32       [..............] PAUSED (TDM QUEUE)
======================================================================================
  [*] All 5 nodes (*) are REAL physical BLE peripherals transmitting over 2.4 GHz.
  [*] Notice: All Virtual Sockets remain continuously OPEN in user space.
======================================================================================
  [Config] N=5 devices | N_max=2 slots | Ratio=2.5x | T_slice=400 ms
```

#### Step 5: Post-Transfer Report
```text
======================================================================================
           MODE D — DYNAMIC REAL DEVICES TRANSFER REPORT
======================================================================================
Real Physical Devices (N):      5 (connected: 5)
Physical GATT Slots (N_max):    2  [Multiplexing ratio: 2.5x]
T_slice Window:                 400 ms
Total File Chunks Transmitted:  160 / 160
Packet Delivery Ratio (PDR):    100.00%  (Target: >= 95.0%) -> PASS
...
  Device MAC             Chunks         PDR
  6E:B9:EF:52:BF:3A     32/32          100.0%
  ...
======================================================================================
[+] Telemetry CSV written: btmux_dynamic_telemetry_N5_Nmax2.csv
```

> **Faculty talking point**: *"I can set N_max to 1, and BT-Mux will still keep all 5 virtual sockets OPEN in user space while sequentially serving each device. The application layer sees zero drops."*

---

## Key Talking Points for Faculty & Examiners

When the committee asks questions, highlight these 4 core architectural guarantees proven by the demo:

1. **User-Space Virtual Sockets (SRS REQ-5)**:
   - *"Notice in the second column that all sockets remain continuously `OPEN`."*
   - Applications never experience socket drops or connection reset exceptions during physical GATT handoffs.

2. **Hardware Constraint vs. Multiplexing (SRS REQ-1 & REQ-9)**:
   - *"The Bluetooth controller physically supports only $N_{\text{max}} = 4$ concurrent links."*
   - BT-Mux's TDM scheduler dynamically round-robins across $N = 12$ streams, guaranteeing fair bandwidth sharing.

3. **Packet Delivery Ratio (PDR $\ge 95\%$)**:
   - At the conclusion of the demo, point to the report: **$PDR = 100.00\%$** (zero dropped chunks due to deterministic re-queuing and deduplication).

4. **Telemetry Reconciliation (SRS REQ-13)**:
   - Show the generated CSV file [`btmux_12_device_telemetry.csv`](file:///e:/College%20materials/Sem5/BTP/btmux_12_device_telemetry.csv) with handoff latency ($\le 300\text{ ms}$) and memory footprint ($< 150\text{ MB}$).

---

## Quick Reference Cheat-Sheet

```powershell
# 1. Single Phone Real BLE Transfer:
python server/src/real_device_transfer.py

# 2. Single Phone Custom File Transfer:
python server/src/real_device_transfer.py --file "PROJECT_STATUS.md"

# 3. 12-Device Simultaneous TDM Demo (Mode A — Standard Testbed):
python server/src/demo_12_devices.py --slice-ms 400

# 4. 12-Device Hybrid Demo (Mode B — Real Phone + 11 Virtual Peers):
python server/src/demo_12_devices.py --phone auto

# 5. 12 Real Devices Simultaneous Transfer (Mode C — No Simulation):
python server/src/demo_12_devices.py --all-real

# 6. Mode C with custom file:
python server/src/demo_12_devices.py --all-real --file "PROJECT_STATUS.md"

# 7. Dynamic N & N_max (Mode D — Interactive real device + slot selection):
python server/src/demo_12_devices.py --dynamic

# 8. Mode D with custom file:
python server/src/demo_12_devices.py --dynamic --file "PROJECT_STATUS.md"
```