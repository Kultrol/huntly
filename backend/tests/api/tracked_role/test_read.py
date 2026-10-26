import pytest

from app.models import (
    TrackedRole,
)

pytestmark = pytest.mark.anyio


# Fetching an opportunity returns its saved owner, title, company, and status.
async def test_role_get_returns_saved_record(api_client, saved_role):
    response = await api_client.get(f"/tracked-roles/{saved_role.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(saved_role.id)
    assert data["title"] == "Backend Developer"
    assert data["status"] == "saved"
    assert data["user_id"] == str(saved_role.user_id)
    assert data["company_id"] == str(saved_role.company_id)


# An opportunity list includes this user's records and excludes another user's opportunities.
async def test_role_list_excludes_other_owners_records(
    api_client, sessions, owner_ids, saved_role
):
    async with sessions.begin() as session:
        session.add(
            TrackedRole(user_id=owner_ids[1], title="Other role", status="saved")
        )
    response = await api_client.get(
        "/tracked-roles/", params={"user_id": str(owner_ids[0])}
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(saved_role.id)]
    assert response.json()[0]["user_id"] == str(owner_ids[0])


# A user with no opportunities receives an empty list even when another user has records.
async def test_role_list_for_owner_without_roles_is_empty(
    api_client, owner_ids, saved_role
):
    response = await api_client.get(
        "/tracked-roles/", params={"user_id": str(owner_ids[1])}
    )
    assert response.status_code == 200
    assert response.json() == []
