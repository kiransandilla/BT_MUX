---
name: fastapi-patterns
description: Use this skill when writing FastAPI routes, endpoints, WebSocket handlers, middleware, dependency injection, or startup/shutdown lifecycle events
---

# FastAPI Patterns for BT-Mux

## Core Rules
- Always use `async def` for route handlers — never `def`
- Use `lifespan` context manager for startup/shutdown (not deprecated `on_event`)
- Use `Depends()` for dependency injection (DB session, transport instance)
- WebSocket endpoint pushes scheduler state events to the React dashboard

## App Bootstrap
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    asyncio.create_task(scheduler.start_loop())
    yield
    # shutdown
    await scheduler.stop()

app = FastAPI(lifespan=lifespan)
```

## REST Route Pattern
```python
@app.post("/api/sessions", response_model=SessionResponse)
async def create_session(body: SessionCreate, db=Depends(get_db)):
    session = await db["sessions"].insert_one(body.model_dump())
    return SessionResponse(id=str(session.inserted_id), **body.model_dump())
```

## WebSocket Pattern (IPC to React dashboard)
```python
from fastapi import WebSocket
connected_clients: list[WebSocket] = []

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)
    try:
        while True:
            await ws.receive_text()  # keep alive
    except:
        connected_clients.remove(ws)

async def broadcast(event: dict):
    for ws in connected_clients:
        await ws.send_json(event)
```

## CORS (for React dev server on different port)
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"], allow_headers=["*"])
```

## Anti-patterns
- Never use `def` (sync) for route handlers that touch DB or BLE
- Never use deprecated `@app.on_event("startup")`
- Never return raw dicts — always use Pydantic response models