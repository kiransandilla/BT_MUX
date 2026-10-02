---
name: python-async-patterns
description: Use this skill when writing any Python async code, asyncio tasks, coroutines, event loops, queues, or concurrent BLE/network operations
---

# Python Asyncio Patterns

## Core Rules
- Always use `async def` and `await` — never `time.sleep()`, always `asyncio.sleep()`
- Use `asyncio.Queue` for all inter-coroutine data passing (FIFO buffers, chunk queues)
- Use `asyncio.Event` for signalling between tasks (e.g. GATT_CONNECTED event)
- Use `asyncio.Lock` to protect shared state from concurrent coroutine access
- Always cancel background tasks cleanly on shutdown: `task.cancel(); await task`
- Never block the event loop — wrap any blocking call in `asyncio.to_thread()`
- Entry point: `asyncio.run(main())` — never `loop.run_until_complete()`

## Task Lifecycle Pattern
```python
async def main():
    task = asyncio.create_task(scheduler_loop())
    try:
        await asyncio.gather(task)
    except asyncio.CancelledError:
        pass
```

## Queue Pattern (RAM FIFO Buffer)
```python
queue: asyncio.Queue[Chunk] = asyncio.Queue()
await queue.put(chunk)          # enqueue (non-blocking)
chunk = await queue.get()       # dequeue (waits if empty)
queue.task_done()
```

## Timeout Pattern (DEGRADED node detection)
```python
try:
    await asyncio.wait_for(connect(), timeout=1.0)  # 1000 ms
except asyncio.TimeoutError:
    mark_degraded(device_id)
```

## Anti-patterns to Avoid
- Do NOT use `threading.Thread` — use `asyncio.create_task()`
- Do NOT use `queue.Queue` — use `asyncio.Queue`
- Do NOT mix sync and async without `asyncio.to_thread()`