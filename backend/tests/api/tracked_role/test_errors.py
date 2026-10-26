from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models import (
    StatusHistory,
    TrackedRole,
)
from app.services.exceptions.tracked_role import TrackedRoleServiceError
from app.services.tracked_role import TrackedRoleService

pytestmark = pytest.mark.anyio


# A salary update that conflicts with the saved range leaves the role and its history
# unchanged.
async def test_role_api_invalid_merged_salary_returns_400_and_rolls_back(
    api_client, sessions, saved_role
):
    response = await api_client.patch(
        f"/tracked-roles/{saved_role.id}",
        json={"salary_min": 110000, "status": "applied"},
    )
    assert response.status_code == 400
    async with sessions() as session:
        role = await session.get(TrackedRole, saved_role.id)
        assert role is not None
        assert role.salary_min == 80000
        assert role.status == "saved"
        history = list(
            await session.scalars(
                select(StatusHistory).where(StatusHistory.tracked_role_id == role.id)
            )
        )
        assert len(history) == 1


# An opportunity cannot be created with a company belonging to another user.
async def test_role_api_rejects_other_owners_company(
    api_client, owner_ids, saved_company
):
    response = await api_client.post(
        "/tracked-roles/",
        json={
            "user_id": str(owner_ids[1]),
            "title": "Rejected",
            "status": "saved",
            "company_id": str(saved_company.id),
        },
    )
    assert response.status_code == 400


# An unknown opportunity ID returns 404, while an ID in the wrong format returns 422.
@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
async def test_role_missing_and_invalid_ids(api_client, method):
    payload = {"title": "Missing"} if method == "PATCH" else None
    response = await api_client.request(
        method, f"/tracked-roles/{uuid4()}", json=payload
    )
    assert response.status_code == 404
    response = await api_client.request(
        method,
        "/tracked-roles/not-a-uuid",
        json=payload,
    )
    assert response.status_code == 422


# Invalid opportunity fields are rejected before the saved role is changed.
@pytest.mark.parametrize(
    "patch",
    [
        {"status": None},
        {"title": " "},
        {"salary_min": -1},
        {"salary_min": 200, "salary_max": 100},
    ],
)
async def test_role_invalid_patch_returns_422(api_client, saved_role, patch):
    response = await api_client.patch(f"/tracked-roles/{saved_role.id}", json=patch)
    assert response.status_code == 422


# An invalid status-change date is rejected without changing the opportunity's status.
async def test_role_occurred_at_must_be_valid_query_datetime(
    api_client, sessions, saved_role
):
    response = await api_client.patch(
        f"/tracked-roles/{saved_role.id}",
        params={"occurred_at": "invalid"},
        json={"status": "applied"},
    )
    assert response.status_code == 422
    async with sessions() as session:
        role = await session.get(TrackedRole, saved_role.id)
        assert role is not None
        assert role.status == "saved"


# Each opportunity endpoint returns a 500 response with the service's failure message.
@pytest.mark.parametrize(
    "method, path, service_method",
    [
        ("GET", "/tracked-roles/{id}", "get_tracked_role_by_id"),
        ("GET", "/tracked-roles/", "get_all_tracked_roles"),
        ("POST", "/tracked-roles/", "create_tracked_role"),
        ("PATCH", "/tracked-roles/{id}", "update_tracked_role"),
        ("DELETE", "/tracked-roles/{id}", "delete_tracked_role"),
    ],
)
async def test_tracked_role_service_failure_returns_500(
    api_client, owner_ids, monkeypatch, method, path, service_method
):
    failure = TrackedRoleServiceError("Storage unavailable")
    mocked_operation = AsyncMock(side_effect=failure)
    monkeypatch.setattr(TrackedRoleService, service_method, mocked_operation)
    if method == "POST":
        payload = {
            "user_id": str(owner_ids[0]),
            "title": "Developer",
            "status": "saved",
        }
    elif method == "PATCH":
        payload = {"title": "Updated"}
    else:
        payload = None
    response = await api_client.request(
        method,
        path.format(id=uuid4()),
        params={"user_id": str(owner_ids[0])},
        json=payload,
    )
    assert response.status_code == 500
    assert response.json() == {"detail": "Storage unavailable"}
    mocked_operation.assert_awaited_once()


# An unexpected programming error remains visible instead of becoming a handled opportunity
# error.
async def test_tracked_role_api_does_not_swallow_programming_errors(
    api_client, monkeypatch
):
    mocked_get = AsyncMock(side_effect=TypeError("Unexpected programming error"))
    monkeypatch.setattr(TrackedRoleService, "get_tracked_role_by_id", mocked_get)
    with pytest.raises(TypeError, match="Unexpected programming error"):
        await api_client.get(f"/tracked-roles/{uuid4()}")
    mocked_get.assert_awaited_once()
