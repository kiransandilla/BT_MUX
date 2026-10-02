---
name: bleak-ble-transport
description: Use this skill when writing any BLE code, Bluetooth connection, GATT characteristic, BLE scan, device connect/disconnect, or implementing BLETransport
---

# Bleak BLE Transport Patterns

## Core Rules
- Always use `bleak` — never `noble`, `noble-winrt`, or any Node.js BLE binding
- `bleak` uses WinRT on Windows natively — zero driver modification, SRS 2.5 compliant
- `bleak` uses BlueZ D-Bus on Raspberry Pi/Linux — no sudo needed
- All BLE operations are async — always `await` them inside `async def`

## BLETransport Abstract Base Class (HAL)
```python
from abc import ABC, abstractmethod

class BLETransport(ABC):
    @abstractmethod
    async def connect(self, device_id: str) -> None: ...
    @abstractmethod
    async def disconnect(self, device_id: str) -> None: ...
    @abstractmethod
    async def send(self, device_id: str, data: bytes) -> None: ...
    @abstractmethod
    async def scan(self) -> list[str]: ...
    @abstractmethod
    def get_max_connections(self) -> int: ...
```

## WinRTTransport (bleak implementation)
```python
from bleak import BleakClient, BleakScanner

class WinRTTransport(BLETransport):
    def __init__(self):
        self._clients: dict[str, BleakClient] = {}

    async def connect(self, device_id: str) -> None:
        client = BleakClient(device_id)
        await client.connect()
        self._clients[device_id] = client

    async def disconnect(self, device_id: str) -> None:
        client = self._clients.pop(device_id, None)
        if client:
            await client.disconnect()

    async def send(self, device_id: str, data: bytes) -> None:
        client = self._clients[device_id]
        await client.write_gatt_char(CHAR_UUID, data)

    def get_max_connections(self) -> int:
        return 4  # detected from SRS N_max
```

## SimulatedTransport (for testing without hardware)
```python
class SimulatedTransport(BLETransport):
    async def connect(self, device_id: str) -> None:
        await asyncio.sleep(0.05)  # simulate 50ms handshake

    async def disconnect(self, device_id: str) -> None:
        await asyncio.sleep(0.01)

    async def send(self, device_id: str, data: bytes) -> None:
        await asyncio.sleep(0.01)  # simulate transmission

    def get_max_connections(self) -> int:
        return 4
```

## Config-driven adapter selection
```python
import os
transport: BLETransport = (
    WinRTTransport() if os.getenv("BLE_TRANSPORT") == "winrt"
    else SimulatedTransport()
)
```

## Anti-patterns
- Never call `client.connect()` without `await`
- Never import or reference `noble`, `noble-winrt`, or any JS BLE library
- Never hardcode N_max — always call `transport.get_max_connections()`
- Never add `if platform == "win32"` checks outside the transport factory