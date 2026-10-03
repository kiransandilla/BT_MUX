"""Motor async MongoDB driver configuration and connection management.

Authoritative source: BT-Mux_Agent_Instructions.md & mongodb-motor-pydantic skill.
"""
import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages AsyncIOMotorClient lifecycle and database references."""
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None


db_manager = DatabaseManager()


def get_motor_client() -> AsyncIOMotorClient:
    """Get active AsyncIOMotorClient instance, creating one if not yet initialized."""
    if db_manager.client is None:
        settings = get_settings()
        logger.info("Initializing AsyncIOMotorClient at %s", settings.MONGODB_URI)
        db_manager.client = AsyncIOMotorClient(settings.MONGODB_URI)
    return db_manager.client


async def get_db() -> AsyncIOMotorDatabase:
    """FastAPI dependency and utility to obtain the active database instance."""
    if db_manager.db is None:
        client = get_motor_client()
        settings = get_settings()
        db_manager.db = client[settings.MONGODB_DB_NAME]
    return db_manager.db


async def connect_to_mongo() -> AsyncIOMotorDatabase:
    """Explicitly establish database connection and initialize collections/indexes."""
    database = await get_db()
    logger.info("Connected to MongoDB database: %s", database.name)
    await init_db_indexes(database)
    return database


async def close_mongo_connection() -> None:
    """Gracefully close AsyncIOMotorClient connection."""
    if db_manager.client is not None:
        logger.info("Closing AsyncIOMotorClient connection...")
        db_manager.client.close()
        db_manager.client = None
        db_manager.db = None


async def init_db_indexes(database: AsyncIOMotorDatabase) -> None:
    """Ensure required indexes on MongoDB collections."""
    try:
        # Index on session_nodes by session_id and device_id
        await database["session_nodes"].create_index(
            [("session_id", ASCENDING), ("device_id", ASCENDING)],
            unique=True,
            name="idx_session_device_unique"
        )
        await database["session_nodes"].create_index(
            [("session_id", ASCENDING), ("priority_rank", ASCENDING)],
            name="idx_session_priority"
        )
        
        # Index on devices by mac_address
        await database["devices"].create_index(
            [("mac_address", ASCENDING)],
            unique=True,
            name="idx_device_mac_unique"
        )
        
        # Index on telemetry by session_id
        await database["telemetry"].create_index(
            [("session_id", ASCENDING)],
            name="idx_telemetry_session"
        )
        logger.info("Database indexes successfully verified/created.")
    except Exception as exc:
        logger.warning("Index creation deferred or failed (check MongoDB connection): %s", exc)
