# BT-Mux — Agent Working Instructions

These are standing instructions for any agent (Antigravity or otherwise) working on the
BT-Mux codebase. Read this file in full before generating a plan or writing code.

## 1. Project summary

BT-Mux is a user-space virtual socket multiplexing middleware for Bluetooth Low Energy
(BLE). It lets a host with a limited number of physical GATT connections (`N_max`,
typically 4) serve a much larger number of persistent logical connections (`N >= 10`)
by rotating the physical slots across peripheral batches using Time-Division
Multiplexing (TDM), while a Session Manager buffers in-flight data in RAM so logical
connections never appear to drop.

This is an academic B.Tech project (3rd year, IIIT Pune). The person you're working
with needs to be able to explain and defend every design decision in a viva — code that
"just works" without a justification they understand is not acceptable, even if it
passes tests.

## 2. Grounding documents — read these before designing anything

Three documents in this workspace are the source of truth, in this priority order:

1. **The SRS** (`BT Mux - 3rd Year Project - Google Docs.pdf` / the formal SRS PDF) —
   authoritative for requirements, terminology, constants, and REQ-IDs.
2. **The finalized ER design** — authoritative for the four data models (Session,
   Device, SessionNode, Telemetry) and their fields/relationships. Implement these
   exactly as specified; do not redesign or add fields that aren't there.
3. **The approved solution overview PDF** — authoritative for the high-level
   architecture narrative and scope boundaries (what's in scope now vs. future work).

**Do not invent requirements, field names, or architecture not present in these
documents.** If something is genuinely unspecified, say so explicitly in your
Implementation Plan artifact as an assumption — don't silently decide and move on.

## 3. Key constants (pull these from the SRS, don't hardcode guesses)

| Constant | Value | Source |
|---|---|---|
| `N` (target logical streams) | >= 10 | SRS 1.4 |
| `N_MAX` (physical GATT connections) | 4 (range 4–7) | SRS 1.4, 2.7 |
| `T_SLICE_MIN` | 100 ms | SRS REQ-2 |
| `T_SLICE_MAX` | 2000 ms | SRS REQ-2 |
| `RECONNECT_LATENCY` | 100–300 ms | SRS 2.5 |
| `DEGRADED_TIMEOUT` | 1000 ms | SRS REQ-4 |
| `HANDOFF_LATENCY_TARGET` | <= 300 ms | SRS 5.1 |
| `PDR_TARGET` | >= 95% at N=10 | SRS 5.1 |
| `MEMORY_FOOTPRINT_TARGET` | < 150 MB | SRS 5.1 |

## 4. Data model — implement as-is

- `sessions` — one row per experiment/test run (test_name, slice_duration_ms,
  max_hardware_limit, status, created_at, started_at, ended_at)
- `devices` — one row per physical BLE peripheral (device_name, device_type,
  mac_address)
- `session_nodes` — join between sessions and devices for a given experiment
  (session_id, device_id, priority_rank, status)
- `Telemetry` — one summary document per session (total_packets_sent/received, pdr,
  average_rtt, average_handoff_latency, embedded `nodes[]` subdocuments) — this is a
  deliberate summary-level simplification of the SRS's request for raw timestamped
  logs (REQ-12); raw per-packet logs are out of scope for now, don't add them
  unprompted.

`session_nodes.status` should track the socket lifecycle from SRS Appendix B:
`UNINITIALIZED -> PAUSED/QUEUED -> CONNECTING -> ACTIVE_PHYSICAL_LINK`, looping back to
`PAUSED/QUEUED` on slice-timer expiry, or `DEGRADED/RETRY` on timeout/error.

**Design decision, considered and rejected:** do not add a separate `TRANSMITTING`
sub-state to this lifecycle to distinguish "connected but idle" from "actively sending
data." That distinction is already covered by chunk-level tracking (Section 4.1 below)
and adding a second, overlapping state machine at the connection level creates two
sources of truth that can drift out of sync for no new capability. `ACTIVE_PHYSICAL_LINK`
remains the single connected state.

### 4.1 Chunk model, delivery tracking, and dedup cache (applies to file-transfer demo)

For the async file-transfer application layer, each unit of transferred data is a
**chunk** with these fields: `media_id`, `chunk_id`, `sequence_number`, `payload`,
`size`, `checksum` (hash), `timestamp`. This is independent of the four ER models in
Section 4 — it's application-layer, not a new top-level Motor / Pydantic model, unless a task
explicitly says otherwise.

Track each chunk's delivery through states defined as a Python Enum:

```python
from enum import Enum

class ChunkState(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    COMPLETED = "COMPLETED"
    RETRY = "RETRY"
```

Only advance on real confirmation — never mark a chunk complete just because it was sent:

```
PENDING -> SENT -> (ACK received) -> COMPLETED
                -> (no ACK)       -> RETRY
```

Store in-flight chunks in per-stream FIFO queues using `asyncio.Queue`, not arrays or shared lists.

Maintain a short-lived in-memory delivery-history cache (TTL ~5 minutes) of
`COMPLETED` chunks per device, so that a device which disconnects and reconnects
during TDM rotation is not sent chunks it already finished. This cache is a
**dedup optimization, not persistence** — do not use it to enable resume-after-restart,
and do not apply it to anything other than the file-transfer demo.

## 5. Build order

1. Repo scaffolding (FastAPI backend + React Vite frontend skeleton, env config, constants file from Section 3)
2. Motor + Pydantic v2 schemas for the four models above
3. FastAPI backend skeleton / routes
4. BT-Mux core: Virtual Socket abstraction
5. Session Manager + RAM/FIFO buffer (include chunk delivery-state tracking and the
   5-minute dedup cache from Section 4.1 here)
6. TDM Scheduler (round-robin baseline; RSSI-guided weighting is a later stretch goal)
7. BLE integration (bleak on Windows via WinRT; bleak on Linux/Raspberry Pi via BlueZ D-Bus — same import, zero code change between platforms)
8. WebSocket/IPC event layer
9. React diagnostic dashboard
10. Telemetry recording + CSV export (REQ-13)
11. Concurrency / race-condition hardening
12. Simulated node testbed, then real BLE testing

Application-layer demo target: **multi-peer file transfer** over N >= 10 simulated
nodes, using chunking + the delivery-state tracking in Section 4.1. This remains the
entire application-layer scope. Do not build a live/real-time media mode, source
arbitration, source handoff, or any headphone/audio-relay variant unless explicitly
asked in a future task — these remain documented as future work only, not current
scope, regardless of any other project document you may encounter.

## 6. Review checkpoints — do not skip these

For **scaffolding, schemas, and dashboard/UI work**: proceed autonomously, no
checkpoint needed.

For **the core BT-Mux modules** (Virtual Socket, Session Manager, RAM/FIFO buffer, TDM
Scheduler): before writing code, produce an Implementation Plan artifact that states,
in plain language:
- what the module does
- *why* this approach was chosen over an obvious alternative (e.g. why a per-stream
  FIFO instead of one shared queue; why buffering instead of dropping on disconnect)
- which SRS REQ-ID(s) it satisfies

Then stop and wait for explicit approval before implementing. This checkpoint exists
so the reasoning can be reviewed and explained back, not just the output.

**BLE binding:** use bleak on all platforms. On Windows it communicates via
WinRT (Windows.Devices.Bluetooth) natively. On Raspberry Pi/Linux it uses
BlueZ via D-Bus. The same import works on both platforms — this is the
entire point of the bleak choice and satisfies SRS 2.5 / 5.4 with no
driver modification. Never reference noble, noble-winrt, or any Node.js
BLE library.

## 7. Traceability log

Maintain a `TRACEABILITY.md` file at the repo root, updated as each module lands, with
one row per implemented REQ-ID:

```
| REQ-ID | Description                  | File(s)                  | Status |
|--------|-------------------------------|---------------------------|--------|
| REQ-1  | Detect host N_max             | src/core/scheduler.py     | Done   |
```

This is required output, not optional — it's used directly for the thesis report and
viva prep, so keep it current rather than reconstructing it at the end.

## 8. Code comments

Comment *why*, not just *what*, in the core modules (Section 6). A comment like
`# buffer instead of dropping so disconnect is invisible to the app (REQ-7)` is worth
more here than a restatement of the code.
