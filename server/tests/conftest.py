"""Pytest fixtures for BT-Mux server tests."""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.db.motor import get_db
from src.main import create_app
from tests.mock_db import MockDatabase


@pytest.fixture
def mock_db() -> MockDatabase:
    """Provide a fresh in-memory mock database."""
    return MockDatabase()


@pytest_asyncio.fixture
async def client(mock_db: MockDatabase) -> AsyncClient:
    """Provide an AsyncClient wired with dependency overrides for MongoDB."""
    app = create_app()
    app.dependency_overrides[get_db] = lambda: mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
