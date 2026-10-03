"""BT-Mux FastAPI Application Entrypoint & Factory.

Authoritative source: BT-Mux_Agent_Instructions.md & fastapi-patterns skill.
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import api_router
from .config.settings import get_settings
from .db.motor import close_mongo_connection, connect_to_mongo

# Configure logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("btmux")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan event context manager for application startup and shutdown."""
    logger.info("Starting BT-Mux server in '%s' environment...", settings.ENVIRONMENT)
    try:
        await connect_to_mongo()
    except Exception as exc:
        logger.warning("MongoDB connection error on startup (service starting degraded): %s", exc)

    yield

    logger.info("Shutting down BT-Mux server...")
    await close_mongo_connection()
    logger.info("BT-Mux server shutdown complete.")


def create_app() -> FastAPI:
    """Application factory for BT-Mux FastAPI backend."""
    app = FastAPI(
        title="BT-Mux Control Plane & Diagnostic Backend",
        description=(
            "User-space virtual socket multiplexing middleware for Bluetooth Low Energy (BLE). "
            "Exposes REST endpoints for sessions, devices, and telemetry, alongside real-time IPC."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS Configuration for React Vite Dashboard
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include aggregated API routers
    app.include_router(api_router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
    )
