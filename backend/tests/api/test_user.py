from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models import Company, User
from app.services.exceptions.user import UserServiceError
from app.services.user import UserService

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize("path", ["/users/me", "/users/{id}"])
async def test_user_get_returns_current_record(api_client, owner_ids, path):
    response = await api_client.get(path.format(id=owner_ids[0]))
    assert response.status_code == 200
    assert response.json() == {"id": str(owner_ids[0]), "name": "Example owner"}


@pytest.mark.parametrize("method", ["GET", "POST"])
async def test_user_collection_is_not_publicly_available(api_client, method):
    response = await api_client.request(method, "/users/", json={"name": "Bypass"})
    assert response.status_code in (404, 405)


@pytest.mark.parametrize("path", ["/users/me", "/users/{id}"])
async def test_user_patch_returns_and_saves_changed_name(
    api_client, sessions, owner_ids, path
):
    response = await api_client.patch(
        path.format(id=owner_ids[0]), json={"name": "Janet"}
    )
    assert response.status_code == 200
    assert response.json() == {"id": str(owner_ids[0]), "name": "Janet"}
    async with sessions() as session:
        assert (await session.get(User, owner_ids[0])).name == "Janet"


async def test_user_delete_removes_record_and_invalidates_session(
    api_client, sessions, owner_ids
):
    response = await api_client.delete(f"/users/{owner_ids[0]}")
    assert response.status_code == 204
    assert response.content == b""
    async with sessions() as session:
        assert await session.get(User, owner_ids[0]) is None
    assert (await api_client.get("/auth/me")).status_code == 401


async def test_user_api_cannot_delete_owner_with_company(
    api_client, sessions, owner_ids, saved_company
):
    response = await api_client.delete(f"/users/{owner_ids[0]}")
    assert response.status_code == 500
    async with sessions() as session:
        assert await session.get(User, owner_ids[0]) is not None
        assert await session.get(Company, saved_company.id) is not None


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
async def test_user_cannot_access_another_user(api_client, sessions, owner_ids, method):
    payload = {"name": "Changed"} if method == "PATCH" else None
    response = await api_client.request(method, f"/users/{owner_ids[1]}", json=payload)
    assert response.status_code == 404
    async with sessions() as session:
        assert (await session.get(User, owner_ids[1])).name == "Example owner"


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
async def test_user_missing_and_invalid_ids(api_client, method):
    payload = {"name": "Jane"} if method == "PATCH" else None
    response = await api_client.request(method, f"/users/{uuid4()}", json=payload)
    assert response.status_code == 404
    response = await api_client.request(method, "/users/not-a-uuid", json=payload)
    assert response.status_code == 422


@pytest.mark.parametrize("name", [None, "", " ", 10, "Jane\x00Doe"])
async def test_user_invalid_name_returns_422_without_changes(
    api_client, sessions, owner_ids, name
):
    users_query = select(User.id, User.name).order_by(User.id)
    async with sessions() as session:
        users_before = (await session.execute(users_query)).all()
    response = await api_client.patch(f"/users/{owner_ids[0]}", json={"name": name})
    assert response.status_code == 422
    async with sessions() as session:
        assert (await session.execute(users_query)).all() == users_before


@pytest.mark.parametrize(
    "method, service_method",
    [("GET", "get_user"), ("PATCH", "update_user"), ("DELETE", "delete_user")],
)
async def test_user_service_failure_returns_500(
    api_client, owner_ids, monkeypatch, method, service_method
):
    mocked_operation = AsyncMock(side_effect=UserServiceError("Storage unavailable"))
    monkeypatch.setattr(UserService, service_method, mocked_operation)
    response = await api_client.request(
        method,
        f"/users/{owner_ids[0]}",
        json={"name": "Updated"} if method == "PATCH" else None,
    )
    assert response.status_code == 500
    assert response.json() == {"detail": "Storage unavailable"}
    mocked_operation.assert_awaited_once()


@pytest.mark.parametrize(
    "method, service_method", [("GET", "get_user"), ("PATCH", "update_user")]
)
@pytest.mark.parametrize("error_type", [TypeError, ValueError])
async def test_user_api_does_not_swallow_programming_errors(
    api_client, owner_ids, monkeypatch, method, service_method, error_type
):
    mocked_operation = AsyncMock(side_effect=error_type("Unexpected programming error"))
    monkeypatch.setattr(UserService, service_method, mocked_operation)
    with pytest.raises(error_type, match="Unexpected programming error"):
        await api_client.request(
            method,
            f"/users/{owner_ids[0]}",
            json={"name": "Jane"} if method == "PATCH" else None,
        )
    mocked_operation.assert_awaited_once()
