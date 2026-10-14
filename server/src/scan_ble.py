"""Scan for nearby physical Bluetooth Low Energy (BLE) peripherals.

Usage:
    python server/src/scan_ble.py
    python server/src/scan_ble.py --timeout 5.0
"""
import argparse
import asyncio
import sys
from pathlib import Path

_SERVER_DIR = Path(__file__).resolve().parent.parent
if str(_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_SERVER_DIR))

from bleak import BleakScanner

# Nordic UART Service (NUS) UUID
NUS_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E".lower()


async def scan_devices(timeout: float = 4.0) -> None:
    """Discover BLE peripherals and display their MAC address, name, and services."""
    print("=" * 72)
    print("           BT-MUX PHYSICAL BLE PERIPHERAL SCANNER")
    print("=" * 72)
    print(f"[*] Scanning radio range for {timeout:.1f} seconds via Windows WinRT / Bleak...")
    print("-" * 72)

    try:
        discovered = await BleakScanner.discover(return_adv=True, timeout=timeout)
    except Exception as exc:
        print(f"[!] Error accessing Bluetooth adapter: {exc}")
        print("    Please ensure Bluetooth is toggled ON in Windows Settings.")
        return

    if not discovered:
        print("[!] No BLE devices discovered in radio range.")
        print("    Ensure your target peripheral (phone / ESP32) is actively advertising.")
        return

    print(f"[+] Discovered {len(discovered)} device(s) total.\n")
    print(f"{'Address / MAC':<24} {'RSSI':<8} {'NUS?':<6} {'Device Name'}")
    print("-" * 72)

    nus_matches = []

    for addr, (device, adv) in discovered.items():
        name = device.name or adv.local_name or "[Unnamed]"
        rssi = f"{adv.rssi} dBm" if adv.rssi is not None else "N/A"
        
        # Check if advertising Nordic UART Service
        service_uuids = [str(u).lower() for u in (adv.service_uuids or [])]
        is_nus = NUS_SERVICE_UUID in service_uuids
        nus_flag = "YES" if is_nus else "no"

        if is_nus or "btmux" in name.lower() or "peer" in name.lower() or "esp32" in name.lower():
            nus_matches.append((addr, name))

        print(f"{addr:<24} {rssi:<8} {nus_flag:<6} {name}")

    print("=" * 72)
    if nus_matches:
        print("\n[*] Recommended BT-Mux target devices detected:")
        for addr, name in nus_matches:
            print(f"    -> {addr} ({name})")
        print("\nTo transfer files to this device, run:")
        print(f"    python server/src/real_device_transfer.py --target {nus_matches[0][0]}")
    else:
        print("\n[*] To use any device above as a target:")
        print("    python server/src/real_device_transfer.py --target <MAC_ADDRESS>")
    print("=" * 72)


def main():
    parser = argparse.ArgumentParser(description="Scan for physical BLE devices")
    parser.add_argument(
        "--timeout",
        type=float,
        default=4.0,
        help="Scanning window duration in seconds (default: 4.0)",
    )
    args = parser.parse_args()
    asyncio.run(scan_devices(timeout=args.timeout))


if __name__ == "__main__":
    main()
