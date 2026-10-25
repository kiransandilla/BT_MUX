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
| **Demo 2 — Mode C: 12 Real Android Phones** | All 12 nodes are real physical Android smartphones (nRF Connect) — no simulation whatsoever. Maximum hardware proof. | 1 Laptop + 12 Android Phones | `server/src/demo_12_devices.py --all-real` |
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

#### Run Mode A with a Custom File:
To demonstrate multiplexing a real file across all 12 nodes (every node receives its own complete copy of the file):
```powershell
python server/src/demo_12_devices.py --file "PROJECT_STATUS.md"
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
2. Run standard hybrid demo (generated test stream):
   ```powershell
   python server/src/demo_12_devices.py --phone auto
   ```
   *(Or specify your phone's address: `python server/src/demo_12_devices.py --phone "6E:B9:EF:52:BF:3A"`)*

3. **Run with a Custom File**:
   Stream an actual file from your laptop directly over the multiplexed hybrid testbed:
   ```powershell
   python server/src/demo_12_devices.py --phone auto --file "PROJECT_STATUS.md"
   ```
   > **Note on Full Delivery**: Every single node (your real smartphone and all 11 virtual peers) receives a **complete, independent copy** of the custom file (all chunks from start to finish). Your phone receives its copy over physical 2.4 GHz BLE while the other 11 peers receive their copies over virtual sockets in the multiplexer.

#### What Happens in Hybrid Mode:
- **Batch 1**: Physical Slot 1 connects to your **real smartphone over the air**, transmitting actual chunks of the complete file to your phone, while Slots 2, 3, and 4 transmit the complete file chunks to virtual peers.
- **Batch 2 & 3**: Your phone's physical link is cleanly paused, while its user-space virtual socket remains **`OPEN`**. The radio rotates to peers 4–7 and 8–11.
- **Next Rotation**: Physical Slot 1 reconnects to your phone and resumes transmission seamlessly until 100% of the file is delivered!

---

### Mode C: 12 Real Android Phones Simultaneous Transfer

This is the **strongest possible hardware proof**. All 12 nodes are **real physical Android smartphones** running the Nordic UART Service (NUS) via the free **nRF Connect for Mobile** app. There are **zero simulated nodes**.

This mode directly demonstrates the core thesis of BT-Mux: **a host laptop Bluetooth adapter physically capped at $N_{\text{max}} = 4$ concurrent links seamlessly multiplexes $N = 12$ physical Android phones over physical 2.4 GHz radio without dropping user-space virtual sockets.**

---

#### 1. Hardware & Software Requirements

| Item | Details | Notes |
| :--- | :--- | :--- |
| **Android Phones** | **12 physical Android smartphones** | Any Android version (Android 6.0 through Android 15). Borrow from classmates / lab mates. |
| **Mobile App** | **nRF Connect for Mobile** | Free on Google Play Store. Must be installed on all 12 phones. |
| **Host Laptop** | Windows 10/11 (or Linux/macOS) | Running BT-Mux in PowerShell (`server/venv` Python environment). |
| **Table Space** | Desk with ~1.5 m width | Arrange the 12 phones in a neat **3 × 4 grid** for examiner viewing. |

> [!TIP]
> **Viva Contingency Plan (Fewer than 12 phones on demo day):**  
> If only 5 to 8 classmates are present on your viva day, run **Mode D** (`python server/src/demo_12_devices.py --dynamic`). You can select your exact number of available phones (e.g., $N = 6$) and set physical slots to $N_{\text{max}} = 2$ or $1$. This proves the exact same multiplexing thesis!

---

#### 2. Fast Setup on All 12 Android Phones

Setting up 12 phones manually can take 30 minutes. Use the **1-minute Profile Share Shortcut** below:

##### The 1-Minute Share Shortcut (Recommended)
1. Configure **Phone 1** completely using the parameters below.
2. In nRF Connect $\to$ **ADVERTISER** tab $\to$ tap the **three dots (⋮)** on your created card $\to$ Tap **Share** (or **Export**).
3. Send the file (`.xml`) to the other 11 phones via **Quick Share / Nearby Share / WhatsApp**.
4. On Phones 2 through 12: Open nRF Connect $\to$ **ADVERTISER** tab $\to$ tap top-right **(⋮)** $\to$ **Import profile** $\to$ select the file.
5. Tap the imported card to edit the **Display Name**: change it to `BT_P2`, `BT_P3`, `BT_P4`....up to `BT_P12`.
6. Toggle the advertiser switch to **ON** on all 12 phones!

---

##### Manual Advertiser Profile Configuration
If setting up manually on any phone:

1. Open **nRF Connect for Mobile** $\to$ Navigate to the **ADVERTISER** tab.
2. Tap **+** (Add profile):
   - **Display Name**: `BTMUX_PHONE_01` (increment per phone: `_01`, `_02`, ..., `_12`).
   - **Connectable**: Toggle switch to **ON** (Mandatory).
   - **Advertising Interval**: Default (100 ms or 250 ms).
   - **TX Power Level**: Default.
3. Tap **Add Service**:
   - **Service UUID**: `6E400001-B5A3-F393-E0A9-E50E24DCCA9E` (Nordic UART Service)
4. Under this service, tap **Add Characteristic** (RX - Chunk Receiver):
   - **Characteristic UUID**: `6E400002-B5A3-F393-E0A9-E50E24DCCA9E`
   - **Properties**: Check both **Write** AND **Write Without Response**.
5. Tap **Add Characteristic** again (TX - Peripheral ACK Sender):
   - **Characteristic UUID**: `6E400003-B5A3-F393-E0A9-E50E24DCCA9E`
   - **Properties**: Check **Notify**.
6. Tap **Save** (top right) $\to$ Toggle the card switch to **ON**.

---

#### 3. Critical Android OS Settings (Prevent Disconnections & Sleep)

Android OS power management will kill background BLE advertising if not configured properly. **Ensure these 4 settings are applied on each of the 12 phones**:

1. **Keep Screens Awake (Do Not Sleep)**:
   - Go to Android **Settings > Display > Screen Timeout** $\to$ Set to **10 minutes** or **30 minutes**.
   - *Developer Option (Optional)*: Enable **"Stay awake while charging"** in Developer Options if phones are plugged in.
2. **Nearby Devices & Location Permissions**:
   - Android 12+: Go to **Settings > Apps > nRF Connect > Permissions** $\to$ Grant **Nearby Devices** (Allow).
   - Android 6–11: Ensure **Location (GPS)** is turned **ON** in the quick settings shade (Android blocks BLE beaconing without Location permission).
3. **Disable Battery Optimization (Doze Mode)**:
   - Go to **Settings > Apps > nRF Connect > Battery** $\to$ Choose **Unrestricted** (or "Don't Optimize").
   - Turn OFF "Battery Saver" mode on all phones.
4. **Avoid 2.4 GHz Wi-Fi Congestion**:
   - Ensure **Personal Hotspot is turned OFF** on all 12 phones.
   - If connected to Wi-Fi, ensure they are connected to a **5 GHz** Wi-Fi band, not 2.4 GHz.

---

#### 4. Physical Viva Presentation Table Layout

To give the faculty an impressive visual demonstration:

1. **Arrange the 12 Phones in a 3 × 4 Grid** on the conference/viva table:
   ```text
   Row 1 (Batch 1):  [Phone 01]   [Phone 02]   [Phone 03]   [Phone 04]   <-- Active first (Slots 1-4)
   Row 2 (Batch 2):  [Phone 05]   [Phone 06]   [Phone 07]   [Phone 08]   <-- Active second (Slots 1-4)
   Row 3 (Batch 3):  [Phone 09]   [Phone 10]   [Phone 11]   [Phone 12]   <-- Active third (Slots 1-4)
   ```
2. **Open the Log Tab on Every Phone**:
   - In nRF Connect on each phone, tap top-left **☰ (Menu)** $\to$ **Log**.
   - As the laptop rotates slots, the faculty will visually see **Row 1 stream text chunks live**, then **Row 2 stream live**, then **Row 3 stream live**!

---

#### 5. Step-by-Step Live Execution from Laptop

##### Step 1: Pre-Scan Check on Laptop
Open PowerShell at the project root and activate the environment:
```powershell
.\server\venv\Scripts\Activate.ps1
python server/src/scan_ble.py
```
Verify that all 12 phones appear with `BTMUX_PHONE_XX` and the `[NUS/BT-Mux]` tag.

##### Step 2: Start the 12-Phone Demo
```powershell
# Transfer a real file (e.g., PROJECT_STATUS.md) to all 12 Android phones:
python server/src/demo_12_devices.py --all-real --file "PROJECT_STATUS.md"

# Or transfer the generated test stream:
python server/src/demo_12_devices.py --all-real
```

##### Step 3: Device Selection Prompt
The script executes an active BLE scan (6–10 s). All 12 Android phones are auto-detected and ranked:
```text
[*] Scanning for nearby BLE peripherals (6s, active mode)...

[+] Discovered 16 BLE device(s):
  [ 1] 6E:B9:EF:52:BF:3A  BTMUX_PHONE_01        -52 dBm  [NUS/BT-Mux]
  [ 2] 72:3F:A1:88:C2:10  BTMUX_PHONE_02        -55 dBm  [NUS/BT-Mux]
  [ 3] 8A:44:B0:12:33:FF  BTMUX_PHONE_03        -58 dBm  [NUS/BT-Mux]
  ...
  [12] F4:88:99:AA:BB:CC  BTMUX_PHONE_12        -72 dBm  [NUS/BT-Mux]

Select up to 12 device numbers (comma-separated), or press Enter to use top 12:
  > [Press Enter]

[+] Confirmed 12 real device(s) for simultaneous transfer:
Proceed? [Y/n]: Y
```

##### Step 4: Live Dashboard Display (What to Show Faculty)
The live ASCII matrix shows the 4 physical GATT slots rotating across the 12 Android phones:
```text
======================================================================================
      BT-MUX: 12-REAL-DEVICE VIRTUAL SOCKET TIME-DIVISION MULTIPLEXER
      Time Elapsed:  3.60s | Physical Radio Limit: N_max = 4 Slots
======================================================================================
  Slot 1: BTMUX_PHONE_01 (2.4GHz) | Slot 2: BTMUX_PHONE_02 (2.4GHz) | Slot 3: ... | Slot 4: ...
--------------------------------------------------------------------------------------
  Node Identifier        Socket   Queue   Done       Progress Bar       Physical Link
  ----------------------------------------------------------------------------------
  BTMUX_PHONE_01*        OPEN     0       16/32      [=======.......]  ACTIVE (2.4GHz)
  BTMUX_PHONE_02*        OPEN     0       16/32      [=======.......]  ACTIVE (2.4GHz)
  BTMUX_PHONE_03*        OPEN     0       16/32      [=======.......]  ACTIVE (2.4GHz)
  BTMUX_PHONE_04*        OPEN     0       16/32      [=======.......]  ACTIVE (2.4GHz)
  BTMUX_PHONE_05*        OPEN     32      0/32       [..............]  PAUSED (TDM QUEUE)
  BTMUX_PHONE_06*        OPEN     32      0/32       [..............]  PAUSED (TDM QUEUE)
  ...
  BTMUX_PHONE_12*        OPEN     32      0/32       [..............]  PAUSED (TDM QUEUE)
======================================================================================
  [*] All 12 nodes (*) are REAL physical BLE peripherals transmitting over 2.4 GHz.
  [*] Notice: All Virtual Sockets remain continuously OPEN in user space.
======================================================================================
```

**Key Points to Emphasize to Faculty**:
1. Point to **Physical Radio Limit: $N_{\text{max}} = 4$ Slots**: The laptop's Bluetooth chip can only hold 4 concurrent hardware links.
2. Point to **Socket column**: All 12 virtual sockets remain continuously `OPEN` in user space without connection reset exceptions.
3. Show the phone screens: Watch the incoming write logs stream in real time on each phone as its batch becomes active.

##### Step 5: Verification & CSV Telemetry
At completion, the terminal displays the 100% Packet Delivery Ratio (PDR) report and exports:
[`btmux_12_real_device_telemetry.csv`](file:///e:/College%20materials/Sem5/BTP/btmux_12_real_device_telemetry.csv).

---

#### 6. Android-Specific Common Errors & Exact Solutions

| Error / Symptom | Root Cause on Android | Exact Resolution |
| :--- | :--- | :--- |
| **Phone MAC Address Keeps Changing (RPA Drift)** | Android privacy features rotate the BLE Resolvable Private Address (RPA) every 15 minutes. | **Do not worry about MAC changes**: BT-Mux filters and matches devices by **Display Name** (`BTMUX_PHONE_XX`). In addition, `BleakTransport` automatically attempts connection using both `random` and `public` address types on Windows WinRT. |
| **Phone Disappears from Laptop Scan** | 1. Phone screen timed out and turned black.<br>2. Android Doze Mode throttled BLE advertising beacons.<br>3. Scan window was too short. | 1. Tap phone screens to keep them awake.<br>2. Toggle advertiser switch OFF then ON in nRF Connect.<br>3. Run scan with extended window: `python server/src/demo_12_devices.py --all-real --scan-sec 10`. |
| **Advertiser Shows "ON" but Phone is Never Detected** | Missing Android runtime permissions. On Android 12+, nRF Connect needs "Nearby Devices" permission; on Android 6–11 it needs "Location". | 1. Pull down Android notification shade $\to$ turn **Location (GPS) ON**.<br>2. Go to phone **Settings > Apps > nRF Connect > Permissions** $\to$ ensure **Nearby Devices** (or Location) is **Allowed**. |
| **GATT Write Error: "Write Not Permitted" or "Char Not Found"** | Mistyped UUID or missing write properties during profile creation. | Open the advertiser profile in nRF Connect: verify RX UUID is `6E400001-B5A3-F393-E0A9-E50E24DCCA9E` and that **Write Without Response** is checked. |
| **Radio Congestion / 1000ms Connect Timeout (`DEGRADED_RETRY`)** | Placing 12 phones touching each other in a stack creates severe 2.4 GHz RF collisions on advertising channels 37, 38, and 39. | 1. Separate phones on the table with at least 15–20 cm space between them.<br>2. Turn OFF personal hotspot on all phones.<br>3. Switch laptop Wi-Fi to 5 GHz so the 2.4 GHz channel is clear.<br>4. Note: BT-Mux automatically handles degraded links without crashing (SRS REQ-4). |
| **Windows Controller Error: `0x8007001F` / HCI `0x09` (Connection Limit Exceeded)** | If a program attempts to keep >4–7 physical connections open simultaneously on Windows, the controller driver crashes. | **BT-Mux automatically prevents this** by rotating slots in batches of 4. If Windows Bluetooth locks from a previous crash: toggle Bluetooth **OFF and ON** in Windows Settings, or run PowerShell as Admin: `Restart-Service bthserv`. |
| **One Phone Out of 12 Freezes / Drops Connection** | Phone OS memory killer killed nRF Connect in the background. | Re-open nRF Connect, verify advertiser toggle is ON, and keep screen unlocked. The TDM scheduler's 10-retry fault tolerance (SRS REQ-4) will re-acquire the link on the next batch rotation. |

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

# 4. Mode A with custom file (Delivers full file to each of 12 nodes):
python server/src/demo_12_devices.py --file "PROJECT_STATUS.md"

# 5. 12-Device Hybrid Demo (Mode B — Real Phone + 11 Virtual Peers):
python server/src/demo_12_devices.py --phone auto

# 6. Mode B with custom file (Delivers full file to real phone + 11 virtual peers):
python server/src/demo_12_devices.py --phone auto --file "PROJECT_STATUS.md"

# 7. 12 Real Android Phones Simultaneous Transfer (Mode C — No Simulation):
python server/src/demo_12_devices.py --all-real

# 8. Mode C with custom file (Delivers full file to each of 12 Android phones):
python server/src/demo_12_devices.py --all-real --file "PROJECT_STATUS.md"

# 9. Dynamic N & N_max (Mode D — Interactive real device + slot selection):
python server/src/demo_12_devices.py --dynamic

# 10. Mode D with custom file:
python server/src/demo_12_devices.py --dynamic --file "PROJECT_STATUS.md"
```


# Step 1: Rapid Setup on All 12 Android Phones

Typing 128-bit UUIDs across 12 phones manually takes 30+ minutes. Use the **1-Minute Profile Share Trick** to save time.

## The 1-Minute Share Shortcut

### On Phone 1:
1. Install **nRF Connect for Mobile** from the Google Play Store.
2. Go to the **ADVERTISER** tab and tap **+** (Add profile).
3. Configure the profile using the parameters in the table below.
4. Once saved, tap the three dots on the card and select **Share** (or **Export**).

### Send to the Other 11 Phones:
- Send the 6E400001-B5A3-F393-E0A9-E50E24DCCA9E

### On Phones 2 through 12:
1. Open **nRF Connect**, go to the **ADVERTISER** tab, add new advertisers
2. Advertising Data => Add record => Complete Local Name => 
3. name => "BT_P1", "BT_P2", "BT_P3", ... "BT_P12"
4. Connectable tick
5. Discoverable Tick
6. Scan Response Data => add record => Service UUID => 6E400001-B5A3-F393-E0A9-E50E24DCCA9E