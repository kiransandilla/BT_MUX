"""System health check and diagnostic status router."""
from typing import Any, Dict
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from ...config.settings import get_settings
from ...db.motor import get_db

router = APIRouter(tags=["Health"])


@router.get("/health")
@router.get("/api/health")
async def health_check(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> Dict[str, Any]:
    """Return health status, active database connectivity, and runtime settings."""
    settings = get_settings()
    db_status = "connected"
    try:
        # Ping mongo
        await db.command("ping")
    except Exception as exc:
        db_status = f"unreachable: {exc}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "service": "bt-mux-server",
        "environment": settings.ENVIRONMENT,
        "database": {
            "name": db.name,
            "status": db_status,
        },
        "ble_transport": settings.BLE_TRANSPORT,
    }
