"""Real Hardware Over-The-Air File Transfer CLI using BT-Mux WinRT HAL.

Transfers a local file to a physical BLE peripheral (e.g., smartphone running nRF Connect
or ESP32 running NUS firmware) via Nordic UART Service (NUS).

Usage:
    # Send a custom file to a known MAC address:
    python server/src/real_device_transfer.py --target "C4:DE:E2:1A:3B:5F" --file "my_file.txt"

    # Send a generated test payload:
    python server/src/real_device_transfer.py --target "C4:DE:E2:1A:3B:5F"

    # Interactive mode (scans and asks you to pick a device):
    python server/src/real_device_transfer.py
"""
import argparse
import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Optional

_SERVER_DIR = Path(__file__).resolve().parent.parent
if str(_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_SERVER_DIR))

from src.core.chunk import Chunk
from src.hal.factory import create_ble_transport
from bleak import BleakScanner


async def select_device_interactively() -> Optional[str]:
    """Scan and prompt user to choose a target peripheral, prioritizing NUS/BT devices."""
    print("[*] Scanning for nearby BLE peripherals (4 seconds, active mode)...")
    scanner = BleakScanner(scanning_mode="active")
    devs = await scanner.discover(return_adv=True, timeout=4.0)

    nus_matches = []
    other_devs = []

    for addr, (dev, adv) in devs.items():
        name = dev.name or adv.local_name or "[Unnamed]"
        uuids = [str(u).lower() for u in (adv.service_uuids or [])]
        is_nus = (
            name in ("BT", "BT_P")
            or "btmux" in name.lower()
            or "6e400001-b5a3-f393-e0a9-e50e24dcca9e" in uuids
        )
        if is_nus:
            nus_matches.append((addr, name, adv.rssi))
        elif name != "[Unnamed]":
            other_devs.append((addr, name, adv.rssi))

    if nus_matches:
        print(f"\n[+] Detected {len(nus_matches)} target BT-Mux peripheral(s):")
        for idx, (addr, name, rssi) in enumerate(nus_matches):
            print(f"  [{idx + 1}] {addr} - {name} ({rssi} dBm) [TARGET]")
        choice = input(f"\nPress Enter to connect to [{nus_matches[0][0]}] or enter number [1]: ").strip()
        idx = int(choice) - 1 if choice.isdigit() else 0
        if 0 <= idx < len(nus_matches):
            return nus_matches[idx][0]
        return nus_matches[0][0]

    all_candidates = other_devs
    if not all_candidates:
        print("[!] No BLE devices discovered in range. Ensure phone advertising is ON.")
        return None

    print("\nSelect a device from discovered list:")
    for idx, (addr, name, rssi) in enumerate(all_candidates):
        print(f"  [{idx + 1}] {addr} - {name} ({rssi} dBm)")

    choice = input("\nEnter device number [1]: ").strip()
    idx = int(choice) - 1 if choice.isdigit() else 0
    if 0 <= idx < len(all_candidates):
        return all_candidates[idx][0]
    return all_candidates[0][0]


async def run_real_transfer(
    target_mac: str,
    file_path: Optional[str] = None,
    chunk_size: int = 128,
) -> bool:
    """Execute real over-the-air file transfer to a physical BLE device."""
    print("=" * 72)
    print("         BT-MUX REAL HARDWARE OVER-THE-AIR FILE TRANSFER")
    print("=" * 72)
    print(f"[*] Target Device Address: {target_mac}")
    print(f"[*] BLE Transport:         Windows WinRT (Native Bluetooth)")
    print(f"[*] Chunk Size:            {chunk_size} bytes")

    # 1. Load or generate payload
    if file_path and os.path.exists(file_path):
        with open(file_path, "rb") as f:
            data = f.read()
        media_id = os.path.basename(file_path)
        print(f"[*] Payload Source:        {file_path} ({len(data)} bytes)")
    else:
        sample_text = (
            "Hello from BT-Mux!\n"
            "This is a real over-the-air transmission benchmark running on Windows WinRT.\n"
            "Testing virtual socket multiplexing and chunk reassembly across physical BLE links.\n"
            * 8
        )
        data = sample_text.encode("utf-8")
        media_id = "btmux_ota_test.txt"
        print(f"[*] Payload Source:        Generated test file ({len(data)} bytes)")

    print("-" * 72)

    # 2. Slice file into Chunk segments
    chunks = []
    for seq, offset in enumerate(range(0, len(data), chunk_size)):
        slice_bytes = data[offset : offset + chunk_size]
        chk = Chunk.create(
            media_id=media_id,
            sequence_number=seq,
            payload=slice_bytes,
        )
        chunks.append(chk)

    total_chunks = len(chunks)
    print(f"[+] Sliced file into {total_chunks} chunks.")

    # 3. Instantiate real WinRT BLE transport
    transport = create_ble_transport("winrt")

    # ACK tracking
    ack_received = set()

    def on_rx_data(dev_id: str, rx_bytes: bytes):
        text = rx_bytes.decode("utf-8", errors="ignore").strip()
        ack_received.add(text)

    transport.on("data", on_rx_data)

    print(f"[*] Connecting to physical peripheral {target_mac}...")
    t_start = time.perf_counter()
    try:
        await transport.connect(target_mac)
        print(f"[+] Physical GATT connection established successfully!")
    except Exception as exc:
        print(f"\n[!] Connection failed: {exc}")
        print("    Troubleshooting tips:")
        print("    1. Ensure the device is powered on and within 5 meters.")
        print("    2. If using nRF Connect on phone, ensure the 'Advertiser' is turned ON.")
        print("    3. If previously paired in Windows Settings, unpair and retry.")
        return False

    print("\n[*] Starting over-the-air chunk transmission...")
    bytes_sent = 0

    try:
        for chk in chunks:
            # Transmit chunk payload over GATT TX characteristic
            await transport.send(target_mac, chk.payload)
            bytes_sent += len(chk.payload)

            pct = (chk.sequence_number + 1) / total_chunks * 100
            sys.stdout.write(
                f"\r    [Chunk {chk.sequence_number + 1:3d}/{total_chunks:3d}] "
                f"Sent: {bytes_sent:5d}/{len(data):5d} bytes ({pct:5.1f}%)"
            )
            sys.stdout.flush()

            # Small inter-frame pacing delay to prevent BLE controller buffer overflow
            await asyncio.sleep(0.04)

        t_end = time.perf_counter()
        elapsed = t_end - t_start

        print("\n\n" + "=" * 72)
        print("                    TRANSMISSION SUMMARY")
        print("=" * 72)
        print(f"Status:                      SUCCESS (ALL CHUNKS SENT)")
        print(f"Total Bytes Transmitted:     {bytes_sent} bytes")
        print(f"Total Chunks Transmitted:    {total_chunks}")
        print(f"Total Elapsed Time:          {elapsed:.2f} seconds")
        print(f"Effective Throughput:        {(bytes_sent / 1024) / elapsed:.2f} KB/s")
        print("=" * 72)
        return True

    except Exception as exc:
        print(f"\n[!] Error during transmission: {exc}")
        return False
    finally:
        print(f"[*] Tearing down GATT connection to {target_mac}...")
        try:
            await transport.disconnect(target_mac)
            print("[+] Disconnected gracefully.")
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Transfer a real file over BLE using BT-Mux")
    parser.add_argument(
        "--target",
        type=str,
        default=None,
        help="Target BLE device MAC address or UUID (e.g. 'C4:DE:E2:1A:3B:5F')",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Path to file to transmit (if omitted, sends generated test payload)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=20,
        help="Payload chunk size in bytes (default: 20 bytes per BLE MTU standard)",
    )

    args = parser.parse_args()

    target = args.target
    if not target:
        target = asyncio.run(select_device_interactively())
        if not target:
            sys.exit(1)

    ok = asyncio.run(
        run_real_transfer(
            target_mac=target,
            file_path=args.file,
            chunk_size=args.chunk_size,
        )
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
