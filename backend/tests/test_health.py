from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app

client = TestClient(app)


# The basic health endpoint reports that the application is running.
def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# The database health endpoint reports success when the database responds.
def test_health_db() -> None:
    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {"database": "ok"}


# The database health endpoint returns 503 with a clear message when its database query fails.
def test_health_db_when_db_unavailable(mocker: MockerFixture) -> None:

    database_error = OperationalError(
        statement="SELECT 1",
        params=None,
        orig=ConnectionError("Connection refused"),
    )

    mock_session_failure = mocker.patch.object(
        target=AsyncSession,
        attribute="execute",
        new_callable=AsyncMock,
        side_effect=database_error,
    )

    response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database connection failure."}

    mock_session_failure.assert_awaited_once()
