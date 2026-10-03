"""FastAPI router for Telemetry metrics and summaries."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ...db.motor import get_db
from ...models.telemetry import Telemetry
from ...schemas.telemetry import TelemetryCreate, TelemetryResponse
from ..utils import doc_to_response, id_query

router = APIRouter(tags=["Telemetry"])


@router.post(
    "/api/sessions/{session_id}/telemetry",
    response_model=TelemetryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_telemetry(
    session_id: str,
    payload: TelemetryCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TelemetryResponse:
    """Record summary telemetry metrics for an experiment session (REQ-12)."""
    # Verify session exists
    session = await db["sessions"].find_one(id_query(session_id))
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found",
        )

    telemetry = Telemetry(
        session_id=session_id,
        total_packets_sent=payload.total_packets_sent,
        total_packets_received=payload.total_packets_received,
        pdr=payload.pdr,
        average_rtt=payload.average_rtt,
        average_handoff_latency=payload.average_handoff_latency,
        nodes=payload.nodes,
    )
    doc = telemetry.model_dump(by_alias=True, exclude_none=True)
    result = await db["telemetry"].insert_one(doc)
    doc["id"] = str(result.inserted_id)
    return TelemetryResponse(**doc)


@router.get(
    "/api/sessions/{session_id}/telemetry",
    response_model=TelemetryResponse,
)
async def get_session_telemetry(
    session_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> TelemetryResponse:
    """Retrieve the latest telemetry summary for a session."""
    doc = await db["telemetry"].find_one(
        {"session_id": session_id},
        sort=[("created_at", -1)],
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No telemetry found for session '{session_id}'",
        )
    return TelemetryResponse(**doc_to_response(doc))


@router.get(
    "/api/telemetry",
    response_model=List[TelemetryResponse],
)
async def list_all_telemetry(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> List[TelemetryResponse]:
    """List recent telemetry records across all sessions."""
    cursor = db["telemetry"].find().sort("created_at", -1).limit(50)
    docs = await cursor.to_list(length=50)
    return [TelemetryResponse(**doc_to_response(d)) for d in docs]


@router.get("/api/sessions/{session_id}/export/csv")
async def export_session_telemetry_csv(
    session_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    """Export benchmark session summaries to CSV format (SRS REQ-13).
    
    Computes and formats global Packet Delivery Ratios (PDR), average RTT,
    and average handoff context-switch overhead across all streams.
    """
    from fastapi.responses import Response
    from ...core.csv_export import generate_telemetry_csv

    # 1. Fetch session record
    session_doc = await db["sessions"].find_one(id_query(session_id))
    if not session_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID '{session_id}' not found",
        )

    # 2. Fetch latest telemetry summary
    telemetry_doc = await db["telemetry"].find_one(
        {"session_id": session_id},
        sort=[("created_at", -1)],
    ) or {}

    # 3. Fetch all attached session nodes
    cursor = db["session_nodes"].find({"session_id": session_id}).sort("priority_rank", 1)
    nodes_docs = await cursor.to_list(length=200)

    # 4. Generate CSV
    csv_content = generate_telemetry_csv(
        session=doc_to_response(session_doc),
        telemetry=doc_to_response(telemetry_doc),
        nodes=[doc_to_response(n) for n in nodes_docs],
    )

    filename = f"btmux_telemetry_{session_id}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Cache-Control": "no-cache",
        },
    )
