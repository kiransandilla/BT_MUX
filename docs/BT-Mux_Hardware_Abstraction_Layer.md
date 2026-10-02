# BT-Mux — Hardware Abstraction Layer: Design Instructions & Tips

Read this alongside `BT-Mux_Agent_Instructions.md`. That file governs the project as a
whole; this file governs one specific, non-negotiable architectural constraint:
**BT-Mux's core logic must never depend directly on a specific BLE driver library.**

## 1. Why this exists

The current development target is Windows (via `bleak` using WinRT). There is a real
possibility the project will later need to run on physical hardware — most likely a
Raspberry Pi — for a faculty-requested hardware demo. Porting at that point must mean
"write one new adapter file and flip one config value," not "rewrite the scheduler,
session manager, and buffer logic." That's only possible if those modules never
reference a driver-specific library, type, or API directly.

Treat this as a hard constraint on Steps 4–7 of the build order, not a nice-to-have.

## 2. The interface contract: `BLETransport`

All core modules (Virtual Socket, Session Manager, RAM/FIFO Buffer, TDM Scheduler)
depend only on this interface — never on `bleak` or any driver-specific import.

```python
from abc import ABC, abstractmethod
from typing import Callable, Any

class BLETransport(ABC):
    @abstractmethod
    async def connect(self, deviceId: str) -> None:
        """Establish physical GATT connection to peripheral."""
        pass

    @abstractmethod
    async def disconnect(self, deviceId: str) -> None:
        """Tear down physical GATT connection."""
        pass

    @abstractmethod
    async def send(self, deviceId: str, data: bytes) -> None:
        """Transmit raw payload chunk to peripheral."""
        pass

    @abstractmethod
    def on(self, event: str, callback: Callable[..., Any]) -> None:
        """Register event listeners ('data', 'connected', 'disconnected')."""
        pass

    @abstractmethod
    async def scanForDevices(self) -> list[dict]:
        """Scan for available BLE peripherals."""
        pass

    @abstractmethod
    def getMaxConnections(self) -> int:
        """Return host physical radio N_max connection limit (REQ-1)."""
        pass
```

Notes on shape:
- `deviceId` should be a plain string/UUID the rest of the system defines — never pass
  a raw `bleak` `BleakClient` object or an OS-specific handle up into Session Manager
  or the Scheduler. Translate driver-native objects into plain data at the adapter
  boundary and nowhere else.
- `getMaxConnections()` implements REQ-1 (dynamic detection of the host's `N_max`).
  Different adapters may detect this differently (or fall back to a config default) —
  that detection logic belongs entirely inside the adapter, not in the Scheduler.
- Events (`data`, `connected`, `disconnected`) are how the adapter talks back up the
  stack. The Scheduler and Session Manager should only ever register against these
  named events — never against a driver's own event names.

## 3. Planned adapters

| Adapter | Backing library | Platform | Status |
|---|---|---|---|
| `WinRTTransport` | `bleak` | Windows 10/11 | Current, primary target |
| `LinuxBLETransport` | `bleak` (via BlueZ D-Bus) | Raspberry Pi / Linux via BlueZ | Future, works via same bleak implementation |
| `SimulatedTransport` | none (in-memory fakes) | any | Build early — see Section 5 |

Note on cross-platform simplicity: `bleak` communicates via WinRT on Windows and via
BlueZ D-Bus on Linux/Raspberry Pi natively. Because `bleak` abstracts both platforms
under the same Python API with zero OS driver modification, `LinuxBLETransport` may not
even need to be a separate class — the same bleak-backed transport can serve both
environments, selected via configuration.

## 4. Config-driven selection

Adapter choice is a single config value, read once at startup by a small factory —
nowhere else in the codebase should branch on "which platform am I on."

```
BLE_TRANSPORT=winrt          → loads WinRTTransport
BLE_TRANSPORT=linux-bluez    → loads LinuxBLETransport (or shared BleakTransport)
BLE_TRANSPORT=simulated      → loads SimulatedTransport
```

```python
import os
from .base import BLETransport
from .winrt import WinRTTransport
from .simulated import SimulatedTransport

def create_ble_transport() -> BLETransport:
    mode = os.getenv("BLE_TRANSPORT", "simulated").lower()
    if mode in ("winrt", "linux-bluez"):
        return WinRTTransport()
    elif mode == "simulated":
        return SimulatedTransport()
    raise ValueError(f"Unknown BLE_TRANSPORT: {mode}")
```

The factory is the *only* place that imports a concrete adapter class. Everything else
in the system imports the `BLETransport` abstract base class and receives an already-
constructed instance (dependency injection, not a global singleton import).

## 5. Build early: the Simulated adapter pays for itself immediately

Don't wait until Step 12 (simulated node testbed) to build `SimulatedTransport`. Build
it as soon as the interface is defined, right after Step 7 starts, for two reasons:

1. It lets you develop and test the Scheduler, Session Manager, and buffer logic
   *before* real BLE hardware or even `bleak` is working — faster iteration.
2. It's the cheapest possible proof that the abstraction actually holds. If the
   Scheduler runs correctly against `SimulatedTransport` with zero code changes, that's
   concrete evidence the interface boundary is clean. If you find yourself needing to
   special-case the Scheduler for "simulated mode," that's a signal the abstraction has
   a leak — fix the leak, don't special-case around it.

## 6. Rules for the agent when implementing this

- When building Steps 4–6 (Virtual Socket, Session Manager, Buffer, Scheduler), do not
  import `bleak` or any transport library. If a task seems to require it, stop
  and flag that the task belongs in the transport adapter layer instead.
- When building Step 7, build the `BLETransport` interface/type definition **first**,
  as its own file, before writing the `WinRTTransport` adapter that implements it.
- Every new capability the Scheduler or Session Manager needs from the hardware must
  be added to the `BLETransport` interface and implemented in **all** adapters that
  exist at the time (including `SimulatedTransport`) — never bolted on as an
  adapter-specific extra method that only `WinRTTransport` exposes.
- This is a checkpoint-worthy design area under the review rules in the main agent
  instructions file: before implementing the interface, produce an Implementation
  Plan explaining the exact method signatures proposed and why, and wait for approval.

## 7. Common pitfalls to avoid

- **Leaking driver types upward.** The most common way this abstraction breaks: a
  `bleak` `BleakClient` object, a WinRT handle, or a library-specific error type
  ends up passed into or thrown by Session Manager / Scheduler code. Convert at the
  adapter boundary, always.
- **Platform `if` statements outside the factory.** If you see `if sys.platform == "win32"`
  anywhere other than the transport factory, that's the abstraction leaking.
- **Do not use asyncio.run() inside a coroutine.** Only call it at the top-level entry
  point. Never make blocking calls or call `time.sleep()` inside async functions; always
  await `asyncio.sleep()`.
- **Config values assumed rather than reported.** `N_max` should come from
  `getMaxConnections()`, not be hardcoded as `4` inside the Scheduler — even though 4
  is the current SRS target, hardcoding it defeats the purpose of REQ-1 and makes the
  Linux port harder later (a Pi's Bluetooth chipset may report a different cap).
- **Building the Linux adapter speculatively right now.** Don't — there's no hardware
  to test it against yet, and speculative code without a way to verify it is worse
  than no code. Build the interface, the Windows adapter, and the Simulated adapter
  now; add the Linux adapter when the Raspberry Pi is actually in hand.

## 8. Verification checklist for "is this actually abstracted?"

Before considering Steps 4–7 done, confirm:

- [ ] `grep`-ing the Scheduler, Session Manager, and Buffer source files for
      `bleak`/`winrt`/`bluez` returns nothing.
- [ ] The Scheduler runs its full test suite against `SimulatedTransport` with no
      code changes and no simulated-mode special cases.
- [ ] Swapping `BLE_TRANSPORT` in config is the only change needed to point the system
      at a different adapter.
- [ ] `getMaxConnections()`, not a hardcoded constant, is what the Scheduler uses for
      `N_max` at runtime.

## 9. What a future Raspberry Pi port should actually require

If this is done correctly, the day the Raspberry Pi arrives, the port should be:

1. `bleak` on Linux uses BlueZ D-Bus natively. No setcap, no root, no raw HCI socket.
   The only requirement is that BlueZ is installed and the bluetooth service is running.
2. Set `BLE_TRANSPORT=linux-bluez` in config.
3. Confirm Python dependencies install cleanly on ARM via pip (they should — no
   platform-specific C++ packages beyond bleak).

Nothing in the Scheduler, Session Manager, Buffer, database layer, FastAPI routes, or
React dashboard should need to change. If it does, that's a sign the abstraction
wasn't actually clean, and it's worth documenting *what* leaked, since that's directly
useful evidence for the thesis report's discussion of the system's design tradeoffs.
