"""Unit tests for Motor async database connection and helper methods."""
import pytest
from src.db.motor import db_manager, get_motor_client, get_db, close_mongo_connection
from src.config.settings import get_settings


@pytest.mark.asyncio
async def test_motor_client_singleton():
    """Verify that get_motor_client returns a consistent AsyncIOMotorClient instance."""
    client1 = get_motor_client()
    client2 = get_motor_client()
    assert client1 is client2
    assert client1 is db_manager.client


@pytest.mark.asyncio
async def test_get_db_name():
    """Verify that get_db targets the configured database name."""
    settings = get_settings()
    db = await get_db()
    assert db.name == settings.MONGODB_DB_NAME


@pytest.mark.asyncio
async def test_close_mongo_connection():
    """Verify that close_mongo_connection cleanly resets client references."""
    _ = get_motor_client()
    assert db_manager.client is not None
    await close_mongo_connection()
    assert db_manager.client is None
    assert db_manager.db is None
