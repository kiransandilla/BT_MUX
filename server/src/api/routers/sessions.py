"""FastAPI router for Session management."""
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ...db.motor import get_db
from ...models.session import Session, SessionStatus
from ...schemas.session import SessionCreate, SessionResponse, SessionStatusUpdate
from ..utils import doc_to_response, id_query

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: SessionCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> SessionResponse:
    """Create a new experiment session."""
    session = Session(
        test_name=payload.test_name,
        slice_duration_ms=payload.slice_duration_ms,
        max_hardware_limit=payload.max_hardware_limit,
    )
    doc = session.model_dump(by_alias=True, exclude_none=True)
    result = await db["sessions"].insert_one(doc)
    doc["id"] = str(result.inserted_id)
    return SessionResponse(**doc)


@router.get("", response_model=List[SessionResponse])
async def list_sessions(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> List[SessionResponse]:
    """Retrieve all recorded experiment sessions."""
    cursor = db["sessions"].find().sort("created_at", -1)
    sessions = await cursor.to_list(length=100)
    return [SessionResponse(**doc_to_response(s)) for s in sessions]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> SessionResponse:
    """Retrieve details of a specific session by ID."""
    doc = await db["sessions"].find_one(id_query(session_id))
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found",
        )
    return SessionResponse(**doc_to_response(doc))


@router.patch("/{session_id}/status", response_model=SessionResponse)
async def update_session_status(
    session_id: str,
    payload: SessionStatusUpdate,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> SessionResponse:
    """Update session status (e.g. running, completed) and set appropriate timestamps."""
    doc = await db["sessions"].find_one(id_query(session_id))
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found",
        )

    now = datetime.now(timezone.utc)
    update_data: dict = {"status": payload.status.value}

    if payload.status == SessionStatus.RUNNING and not doc.get("started_at"):
        update_data["started_at"] = now
    elif payload.status == SessionStatus.COMPLETED and not doc.get("ended_at"):
        update_data["ended_at"] = now

    await db["sessions"].update_one(id_query(session_id), {"$set": update_data})
    updated_doc = await db["sessions"].find_one(id_query(session_id))
    return SessionResponse(**doc_to_response(updated_doc))


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> None:
    """Delete a session and cascade delete its session nodes and telemetry."""
    query = id_query(session_id)
    doc = await db["sessions"].find_one(query)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found",
        )

    await db["sessions"].delete_one(query)
    await db["session_nodes"].delete_many({"session_id": session_id})
    await db["telemetry"].delete_many({"session_id": session_id})
