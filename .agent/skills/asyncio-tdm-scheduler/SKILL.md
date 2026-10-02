---
name: asyncio-tdm-scheduler
description: Use this skill when implementing the TDM scheduler, batch rotation, slot management, T_slice timing, DEGRADED node handling, or session queue logic
---

# TDM Scheduler Implementation Pattern

## SRS Constants (never hardcode elsewhere)
```python
N_MAX = 4                    # REQ-1
T_SLICE_MIN_MS = 100         # REQ-2
T_SLICE_MAX_MS = 2000        # REQ-2
DEGRADED_TIMEOUT_MS = 1000   # REQ-4
HANDOFF_TARGET_MS = 300      # SRS 5.1
```

## Scheduler Loop Pattern
```python
async def scheduler_loop(
    sessions: list[SessionNode],
    transport: BLETransport,
    t_slice_ms: int
):
    queue = list(sessions)  # round-robin queue

    while queue:
        batch = queue[:transport.get_max_connections()]
        connected = []

        for node in batch:
            try:
                await asyncio.wait_for(
                    transport.connect(node.device_id),
                    timeout=DEGRADED_TIMEOUT_MS / 1000
                )
                node.status = NodeState.ACTIVE_PHYSICAL_LINK
                connected.append(node)
            except asyncio.TimeoutError:
                node.status = NodeState.DEGRADED
                # skip slot, will retry next cycle

        # run T_slice window
        await asyncio.sleep(t_slice_ms / 1000)

        # flush buffers for connected nodes
        for node in connected:
            await flush_buffer(node, transport)
            node.status = NodeState.PAUSED_QUEUED
            await transport.disconnect(node.device_id)

        # advance round-robin
        queue = queue[len(batch):] + batch
```

## Buffer Flush Pattern
```python
async def flush_buffer(node: SessionNode, transport: BLETransport):
    buf = get_buffer(node.device_id)  # RamFifoBuffer
    while not buf.empty():
        chunk = await buf.get()
        if await is_duplicate(node.device_id, chunk.chunk_id):
            continue
        chunk.state = ChunkState.SENT
        await transport.send(node.device_id, chunk.payload)
        chunk.state = ChunkState.COMPLETED
        update_delivery_cache(node.device_id, chunk.chunk_id)
```

## Anti-patterns
- Never `time.sleep()` inside the scheduler — always `asyncio.sleep()`
- Never hardcode `4` for batch size — always `transport.get_max_connections()`
- Never mark a chunk COMPLETED before ACK is confirmed
- Never let one DEGRADED node block the rest of the batch---
name: asyncio-tdm-scheduler
description: Use this skill when implementing the TDM scheduler, batch rotation, slot management, T_slice timing, DEGRADED node handling, or session queue logic
---

# TDM Scheduler Implementation Pattern

## SRS Constants (never hardcode elsewhere)
```python
N_MAX = 4                    # REQ-1
T_SLICE_MIN_MS = 100         # REQ-2
T_SLICE_MAX_MS = 2000        # REQ-2
DEGRADED_TIMEOUT_MS = 1000   # REQ-4
HANDOFF_TARGET_MS = 300      # SRS 5.1
```

## Scheduler Loop Pattern
```python
async def scheduler_loop(
    sessions: list[SessionNode],
    transport: BLETransport,
    t_slice_ms: int
):
    queue = list(sessions)  # round-robin queue

    while queue:
        batch = queue[:transport.get_max_connections()]
        connected = []

        for node in batch:
            try:
                await asyncio.wait_for(
                    transport.connect(node.device_id),
                    timeout=DEGRADED_TIMEOUT_MS / 1000
                )
                node.status = NodeState.ACTIVE_PHYSICAL_LINK
                connected.append(node)
            except asyncio.TimeoutError:
                node.status = NodeState.DEGRADED
                # skip slot, will retry next cycle

        # run T_slice window
        await asyncio.sleep(t_slice_ms / 1000)

        # flush buffers for connected nodes
        for node in connected:
            await flush_buffer(node, transport)
            node.status = NodeState.PAUSED_QUEUED
            await transport.disconnect(node.device_id)

        # advance round-robin
        queue = queue[len(batch):] + batch
```

## Buffer Flush Pattern
```python
async def flush_buffer(node: SessionNode, transport: BLETransport):
    buf = get_buffer(node.device_id)  # RamFifoBuffer
    while not buf.empty():
        chunk = await buf.get()
        if await is_duplicate(node.device_id, chunk.chunk_id):
            continue
        chunk.state = ChunkState.SENT
        await transport.send(node.device_id, chunk.payload)
        chunk.state = ChunkState.COMPLETED
        update_delivery_cache(node.device_id, chunk.chunk_id)
```

## Anti-patterns
- Never `time.sleep()` inside the scheduler — always `asyncio.sleep()`
- Never hardcode `4` for batch size — always `transport.get_max_connections()`
- Never mark a chunk COMPLETED before ACK is confirmed
- Never let one DEGRADED node block the rest of the batch