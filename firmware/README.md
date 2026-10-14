# BT-Mux Real Peripheral Setup Guide

This guide details how to set up real Bluetooth Low Energy (BLE) peripheral devices for testing BT-Mux physical over-the-air file multiplexing and chunk transmission.

---

## Option 1: Smartphone (Zero Hardware Required)

You can turn any Android phone or iPhone into a Nordic UART Service (NUS) peripheral in 2 minutes:

1. Download **nRF Connect for Mobile** (Free on Google Play Store or Apple App Store).
2. Open the app and navigate to the **Advertiser** tab.
3. Tap **+** (Add) to create an Advertiser profile:
   - **Display Name**: `BTMUX_PEER_01`
   - **Add Record / Service**: Select **Nordic UART Service** (or enter UUID `6E400001-B5A3-F393-E0A9-E50E24DCCA9E`).
   - Add Characteristics under the service:
     - **RX Characteristic** (`6E400002-B5A3-F393-E0A9-E50E24DCCA9E`): Properties **Write**, **Write Without Response**.
     - **TX Characteristic** (`6E400003-B5A3-F393-E0A9-E50E24DCCA9E`): Properties **Notify**.
4. Enable the toggle switch next to your profile to **Start Advertising**.
5. Note the Bluetooth address displayed (or run `python server/src/scan_ble.py` on your PC).

---

## Option 2: ESP32 Microcontroller (Arduino IDE)

If you have an ESP32 board (ESP32-WROOM-32, NodeMCU ESP32, ESP32-C3, etc.):

1. Open [esp32_nus_peripheral.ino](file:///e:/College%20materials/Sem5/BTP/firmware/esp32_nus_peripheral/esp32_nus_peripheral.ino) in Arduino IDE.
2. Under **Tools > Board**, select **ESP32 Dev Module** (or your specific board).
3. Connect your ESP32 via USB and select the COM port.
4. Click **Upload**.
5. Open the **Serial Monitor** at **115200 baud** to see real-time chunk reception logs and MAC address.

---

## Option 3: Testing from BT-Mux (Your Windows Host)

### Step 1: Scan for your peripheral
Run the scanner tool:
```bash
python server/src/scan_ble.py
```
This lists all active BLE devices and highlights any advertising NUS or BT-Mux peripherals.

### Step 2: Transfer a File Over-the-Air
Run the transfer CLI with the target address:
```bash
# Interactive selection (auto-scans):
python server/src/real_device_transfer.py

# Or specify target MAC directly:
python server/src/real_device_transfer.py --target "C4:DE:E2:1A:3B:5F" --file "path/to/any_file.txt"
```
