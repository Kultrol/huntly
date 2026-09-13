import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_db() -> None:
    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {"database": "ok"}


def test_health_db_when_db_unavailable(mocker: MockerFixture) -> None:

    database_error = OperationalError(
        statement="SELECT 1",
        params=None,
        orig=ConnectionError("Connection refused"),
    )

    mock_session_failure = mocker.patch.object(
        target=Session, attribute="execute", side_effect=database_error
    )

    response = client.get("/health/db")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database connection failure."}

    mock_session_failure.assert_called_once()
