---
name: mongodb-motor-pydantic
description: Use this skill when writing database models, MongoDB queries, Motor async driver calls, Pydantic schemas, or any of the four BT-Mux data models (Session, Device, SessionNode, Telemetry)
---

# MongoDB + Motor + Pydantic Patterns

## Core Rules
- Always use `motor.motor_asyncio.AsyncIOMotorClient` — never sync `pymongo`
- Always use Pydantic v2 models — `model_dump()` not `.dict()`
- `_id` in MongoDB maps to `id` in Pydantic via `alias="_id"`
- All DB calls must be `await`ed inside `async def`

## DB Client Setup
```python
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
db = client["btmux"]

async def get_db():
    return db
```

## The Four Models

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum

class SessionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"

class Session(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    test_name: str
    slice_duration_ms: int          # 100 <= x <= 2000
    max_hardware_limit: int = 4     # N_max
    status: SessionStatus = SessionStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

class Device(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    device_name: str
    device_type: str
    mac_address: str

class NodeState(str, Enum):
    UNINITIALIZED = "UNINITIALIZED"
    PAUSED_QUEUED = "PAUSED_QUEUED"
    CONNECTING = "CONNECTING"
    ACTIVE_PHYSICAL_LINK = "ACTIVE_PHYSICAL_LINK"
    DEGRADED = "DEGRADED"

class SessionNode(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    session_id: str
    device_id: str
    priority_rank: int = 0
    status: NodeState = NodeState.UNINITIALIZED

class NodeMetric(BaseModel):
    node_id: str
    average_rssi: Optional[float] = None
    average_rtt: Optional[float] = None

class Telemetry(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    session_id: str
    total_packets_sent: int = 0
    total_packets_received: int = 0
    pdr: float = 0.0
    average_rtt: float = 0.0
    average_handoff_latency: float = 0.0
    nodes: list[NodeMetric] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

## Query Patterns
```python
# Insert
result = await db["sessions"].insert_one(session.model_dump(by_alias=True))

# Find one
doc = await db["sessions"].find_one({"_id": session_id})

# Find many
cursor = db["session_nodes"].find({"session_id": session_id})
nodes = await cursor.to_list(length=None)

# Update
await db["session_nodes"].update_one(
    {"_id": node_id},
    {"$set": {"status": NodeState.ACTIVE_PHYSICAL_LINK}}
)
```

## Anti-patterns
- Never use `.dict()` — always `model_dump()`
- Never block with sync pymongo inside async functions
- Never store raw per-packet logs in Telemetry — summary only