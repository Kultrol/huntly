from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select

from app.models import Company, User
from app.services.exceptions.user import UserServiceError
from app.services.user import UserService

pytestmark = pytest.mark.anyio


# Creating a user trims the name and saves the same name returned in the response.
async def test_user_create_returns_and_saves_trimmed_name(api_client, sessions):
    user_id = None
    try:
        response = await api_client.post("/users/", json={"name": "  Jane Doe  "})
        assert response.status_code == 201
        data = response.json()
        user_id = UUID(data["id"])
        assert data["name"] == "Jane Doe"
        async with sessions() as session:
            user = await session.get(User, user_id)
            assert user is not None
            assert user.name == "Jane Doe"
    finally:
        async with sessions.begin() as session:
            await session.execute(delete(User).where(User.id == user_id))


# Fetching a user returns the saved ID and display name.
async def test_user_get_returns_saved_record(api_client, owner_ids):
    response = await api_client.get(f"/users/{owner_ids[0]}")
    assert response.status_code == 200
    assert response.json() == {"id": str(owner_ids[0]), "name": "Example owner"}


# The user list contains both saved users with their correct display names.
async def test_user_list_includes_saved_users(api_client, owner_ids):
    response = await api_client.get("/users/")
    assert response.status_code == 200
    saved_users = [item for item in response.json() if UUID(item["id"]) in owner_ids]
    assert {item["id"] for item in saved_users} == {str(id) for id in owner_ids}
    assert all(item["name"] == "Example owner" for item in saved_users)


# Changing a user's name returns the new name and commits it to the database.
async def test_user_patch_returns_and_saves_changed_name(
    api_client, sessions, owner_ids
):
    response = await api_client.patch(f"/users/{owner_ids[0]}", json={"name": "Janet"})
    assert response.status_code == 200
    assert response.json() == {"id": str(owner_ids[0]), "name": "Janet"}
    async with sessions() as session:
        user = await session.get(User, owner_ids[0])
        assert user is not None
        assert user.name == "Janet"


# Deleting an empty user returns no response body and removes the saved record.
async def test_user_delete_returns_empty_response_and_removes_record(
    api_client, sessions, owner_ids
):
    response = await api_client.delete(f"/users/{owner_ids[0]}")
    assert response.status_code == 204
    assert response.content == b""
    async with sessions() as session:
        assert await session.get(User, owner_ids[0]) is None


# Deleting a user who owns a company fails and preserves both records.
async def test_user_api_cannot_delete_owner_with_company(
    api_client, sessions, owner_ids, saved_company
):
    response = await api_client.delete(f"/users/{owner_ids[0]}")
    assert response.status_code == 500
    async with sessions() as session:
        assert await session.get(User, owner_ids[0]) is not None
        assert await session.get(Company, saved_company.id) is not None


# An unknown user ID returns 404, while an ID in the wrong format returns 422.
@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
async def test_user_missing_and_invalid_ids(api_client, method):
    payload = {"name": "Jane"} if method == "PATCH" else None
    response = await api_client.request(method, f"/users/{uuid4()}", json=payload)
    assert response.status_code == 404
    response = await api_client.request(
        method,
        "/users/not-a-uuid",
        json=payload,
    )
    assert response.status_code == 422


# A missing, blank, or incorrectly typed display name is rejected by the user endpoint.
@pytest.mark.parametrize("method", ["POST", "PATCH"])
@pytest.mark.parametrize("name", [None, "", " ", 10])
async def test_user_invalid_name_returns_422(api_client, owner_ids, method, name):
    response = await api_client.request(
        method,
        "/users/" if method == "POST" else f"/users/{owner_ids[0]}",
        json={"name": name},
    )
    assert response.status_code == 422


# A NUL-containing name is rejected without creating or changing stored users.
@pytest.mark.parametrize("method", ["POST", "PATCH"])
async def test_user_null_character_name_returns_422_without_changes(
    api_client, sessions, owner_ids, method
):
    users_query = select(User.id, User.name).order_by(User.id)
    async with sessions() as session:
        users_before = (await session.execute(users_query)).all()
    response = await api_client.request(
        method,
        "/users/" if method == "POST" else f"/users/{owner_ids[0]}",
        json={"name": "Jane\x00Doe"},
    )
    assert response.status_code == 422
    async with sessions() as session:
        assert (await session.execute(users_query)).all() == users_before


# Each user endpoint returns a 500 response with the service's failure message.
@pytest.mark.parametrize(
    "method, path, service_method",
    [
        ("GET", "/users/{id}", "get_user"),
        ("GET", "/users/", "get_all_users"),
        ("POST", "/users/", "create_user"),
        ("PATCH", "/users/{id}", "update_user"),
        ("DELETE", "/users/{id}", "delete_user"),
    ],
)
async def test_user_service_failure_returns_500(
    api_client, owner_ids, monkeypatch, method, path, service_method
):
    failure = UserServiceError("Storage unavailable")
    mocked_operation = AsyncMock(side_effect=failure)
    monkeypatch.setattr(UserService, service_method, mocked_operation)
    if method == "POST":
        payload = {"name": "Example"}
    elif method == "PATCH":
        payload = {"name": "Updated"}
    else:
        payload = None
    response = await api_client.request(
        method, path.format(id=uuid4()), params=None, json=payload
    )
    assert response.status_code == 500
    assert response.json() == {"detail": "Storage unavailable"}
    mocked_operation.assert_awaited_once()


# An unexpected programming error remains visible instead of becoming a handled user error.
@pytest.mark.parametrize(
    "method, service_method",
    [("GET", "get_user"), ("POST", "create_user"), ("PATCH", "update_user")],
)
@pytest.mark.parametrize("error_type", [TypeError, ValueError])
async def test_user_api_does_not_swallow_programming_errors(
    api_client, monkeypatch, method, service_method, error_type
):
    mocked_operation = AsyncMock(side_effect=error_type("Unexpected programming error"))
    monkeypatch.setattr(UserService, service_method, mocked_operation)
    payload = {"name": "Jane"} if method in ("POST", "PATCH") else None
    with pytest.raises(error_type, match="Unexpected programming error"):
        await api_client.request(
            method,
            "/users/" if method == "POST" else f"/users/{uuid4()}",
            json=payload,
        )
    mocked_operation.assert_awaited_once()
