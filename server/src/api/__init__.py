"""BT-Mux API Package."""
from fastapi import APIRouter

from .routers.devices import router as devices_router
from .routers.health import router as health_router
from .routers.session_nodes import router as session_nodes_router
from .routers.sessions import router as sessions_router
from .routers.simulation import router as simulation_router
from .routers.telemetry import router as telemetry_router
from .routers.ws import router as ws_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(sessions_router)
api_router.include_router(devices_router)
api_router.include_router(session_nodes_router)
api_router.include_router(telemetry_router)
api_router.include_router(simulation_router)
api_router.include_router(ws_router)

__all__ = ["api_router"]

