from unittest.mock import AsyncMock

import pytest
from httpx2 import ASGITransport, AsyncClient

from app.core.database import get_db
from app.main import app


# The basic health endpoint works without opening a database session.
@pytest.mark.anyio
async def test_liveness_does_not_open_database_session():
    get_session = AsyncMock(
        side_effect=AssertionError("Liveness should not need the database")
    )
    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = get_session
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        get_session.assert_not_awaited()
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override
