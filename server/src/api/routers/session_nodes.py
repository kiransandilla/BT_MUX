"""FastAPI router for SessionNode management."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ...db.motor import get_db
from ...models.session_node import SessionNode
from ...schemas.session_node import (
    SessionNodeCreate,
    SessionNodeResponse,
    SessionNodeStatusUpdate,
)
from ..utils import doc_to_response, id_query

router = APIRouter(prefix="/api/sessions/{session_id}/nodes", tags=["Session Nodes"])


@router.post("", response_model=SessionNodeResponse, status_code=status.HTTP_201_CREATED)
async def add_node_to_session(
    session_id: str,
    payload: SessionNodeCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> SessionNodeResponse:
    """Attach a registered device to an experiment session."""
    # Verify session exists
    session = await db["sessions"].find_one(id_query(session_id))
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found",
        )

    # Verify device exists
    device = await db["devices"].find_one(id_query(payload.device_id))
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with ID '{payload.device_id}' not found",
        )

    # Check if node already attached
    existing = await db["session_nodes"].find_one({
        "session_id": session_id,
        "device_id": payload.device_id,
    })
    if existing:
        return SessionNodeResponse(**doc_to_response(existing))

    node = SessionNode(
        session_id=session_id,
        device_id=payload.device_id,
        priority_rank=payload.priority_rank,
    )
    doc = node.model_dump(by_alias=True, exclude_none=True)
    result = await db["session_nodes"].insert_one(doc)
    doc["id"] = str(result.inserted_id)
    return SessionNodeResponse(**doc)


@router.get("", response_model=List[SessionNodeResponse])
async def list_session_nodes(
    session_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> List[SessionNodeResponse]:
    """List all nodes attached to a session, sorted by priority_rank."""
    cursor = db["session_nodes"].find({"session_id": session_id}).sort("priority_rank", 1)
    nodes = await cursor.to_list(length=100)
    return [SessionNodeResponse(**doc_to_response(n)) for n in nodes]


@router.get("/{node_id}", response_model=SessionNodeResponse)
async def get_session_node(
    session_id: str,
    node_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> SessionNodeResponse:
    """Retrieve details for a specific session node."""
    doc = await db["session_nodes"].find_one({
        **id_query(node_id),
        "session_id": session_id,
    })
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session node with ID '{node_id}' not found in session '{session_id}'",
        )
    return SessionNodeResponse(**doc_to_response(doc))


@router.patch("/{node_id}/status", response_model=SessionNodeResponse)
async def update_node_status(
    session_id: str,
    node_id: str,
    payload: SessionNodeStatusUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> SessionNodeResponse:
    """Update a session node's socket lifecycle state."""
    query = {**id_query(node_id), "session_id": session_id}
    doc = await db["session_nodes"].find_one(query)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session node with ID '{node_id}' not found in session '{session_id}'",
        )

    await db["session_nodes"].update_one(query, {"$set": {"status": payload.status.value}})
    updated = await db["session_nodes"].find_one(query)
    return SessionNodeResponse(**doc_to_response(updated))


@router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_session_node(
    session_id: str,
    node_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> None:
    """Remove a node from an active session."""
    query = {**id_query(node_id), "session_id": session_id}
    doc = await db["session_nodes"].find_one(query)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session node with ID '{node_id}' not found in session '{session_id}'",
        )
    await db["session_nodes"].delete_one(query)
