from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from app.models import Contact, TrackedRole, TrackedRoleContact
from app.services.contact import ContactService
from app.services.exceptions.contact import ContactServiceError

pytestmark = pytest.mark.anyio


# Creating a contact returns and saves its cleaned name, owner, company, and notes.
async def test_contact_create_returns_and_saves_fields(
    api_client, sessions, owner_ids, saved_company
):
    response = await api_client.post(
        "/contacts/",
        json={
            "user_id": str(owner_ids[0]),
            "company_id": str(saved_company.id),
            "name": "  Jane Doe ",
            "notes": "Original notes",
        },
    )
    assert response.status_code == 201
    data = response.json()
    contact_id = UUID(data["id"])
    assert data["name"] == "Jane Doe"
    assert data["company_id"] == str(saved_company.id)
    assert data["notes"] == "Original notes"
    async with sessions() as session:
        found = await session.get(Contact, contact_id)
        assert found is not None
        assert found.name == "Jane Doe"
        assert found.user_id == owner_ids[0]
        assert found.company_id == saved_company.id
        assert found.notes == "Original notes"


# Fetching a contact returns the saved person and their company information.
async def test_contact_get_returns_saved_record(api_client, saved_contact):
    response = await api_client.get(f"/contacts/{saved_contact.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(saved_contact.id)
    assert data["name"] == "Jane Doe"
    assert data["user_id"] == str(saved_contact.user_id)
    assert data["company_id"] == str(saved_contact.company_id)
    assert data["notes"] == "Original notes"


# A contact list includes this user's people and excludes another user's records.
async def test_contact_list_excludes_other_owners_records(
    api_client, sessions, owner_ids, saved_contact
):
    async with sessions.begin() as session:
        session.add(Contact(user_id=owner_ids[1], name="Other contact"))
    response = await api_client.get("/contacts/", params={"user_id": str(owner_ids[0])})
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(saved_contact.id)]
    assert response.json()[0]["user_id"] == str(owner_ids[0])


# A user with no contacts receives an empty list even when another user has contacts.
async def test_contact_list_for_owner_without_contacts_is_empty(
    api_client, owner_ids, saved_contact
):
    response = await api_client.get("/contacts/", params={"user_id": str(owner_ids[1])})
    assert response.status_code == 200
    assert response.json() == []


# A contact update can clear its company and notes while preserving an omitted name.
async def test_contact_patch_clears_nullable_fields_and_preserves_name(
    api_client, sessions, saved_contact
):
    response = await api_client.patch(
        f"/contacts/{saved_contact.id}",
        json={"company_id": None, "email": "jane@example.com", "notes": None},
    )
    assert response.status_code == 200
    assert response.json()["company_id"] is None
    assert response.json()["notes"] is None
    assert response.json()["name"] == "Jane Doe"
    async with sessions() as session:
        found = await session.get(Contact, saved_contact.id)
        assert found is not None
        assert found.company_id is None
        assert found.email == "jane@example.com"
        assert found.notes is None
        assert found.name == "Jane Doe"


# Creating or updating a contact cannot associate it with another user's company.
@pytest.mark.parametrize("method", ["POST", "PATCH"])
async def test_contact_api_rejects_other_owners_company(
    api_client, sessions, owner_ids, saved_contact, saved_company, method
):
    if method == "POST":
        response = await api_client.post(
            "/contacts/",
            json={
                "user_id": str(owner_ids[1]),
                "name": "Rejected",
                "company_id": str(saved_company.id),
            },
        )
    else:
        response = await api_client.post(
            "/companies/", json={"user_id": str(owner_ids[1]), "name": "Other company"}
        )
        assert response.status_code == 201
        response = await api_client.patch(
            f"/contacts/{saved_contact.id}", json={"company_id": response.json()["id"]}
        )
    assert response.status_code == 400
    async with sessions() as session:
        contact = await session.get(Contact, saved_contact.id)
        assert contact is not None
        assert contact.company_id == saved_company.id
        assert contact.name == "Jane Doe"


# Deleting a contact removes its opportunity link without deleting the opportunity.
async def test_contact_api_delete_removes_link_and_preserves_role(
    api_client, sessions, saved_contact, saved_role
):
    async with sessions.begin() as session:
        link = TrackedRoleContact(
            contact_id=saved_contact.id, tracked_role_id=saved_role.id
        )
        session.add(link)
    response = await api_client.delete(f"/contacts/{saved_contact.id}")
    assert response.status_code == 204
    assert response.content == b""
    async with sessions() as session:
        assert await session.get(Contact, saved_contact.id) is None
        assert await session.get(TrackedRoleContact, link.id) is None
        assert await session.get(TrackedRole, saved_role.id) is not None


# An unknown contact ID returns 404, while an ID in the wrong format returns 422.
@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
async def test_contact_missing_and_invalid_ids(api_client, method):
    payload = {"name": "Jane"} if method == "PATCH" else None
    response = await api_client.request(method, f"/contacts/{uuid4()}", json=payload)
    assert response.status_code == 404
    response = await api_client.request(
        method,
        "/contacts/not-a-uuid",
        json=payload,
    )
    assert response.status_code == 422


# Invalid contact updates are rejected before the saved person is changed.
@pytest.mark.parametrize(
    "payload", [{"name": None}, {"name": " "}, {"linkedin_url": "invalid"}]
)
async def test_contact_invalid_patch_returns_422(api_client, saved_contact, payload):
    response = await api_client.patch(f"/contacts/{saved_contact.id}", json=payload)
    assert response.status_code == 422


# Each contact endpoint returns a 500 response with the service's failure message.
@pytest.mark.parametrize(
    "method, path, service_method",
    [
        ("GET", "/contacts/{id}", "get_contact"),
        ("GET", "/contacts/", "get_all_contacts"),
        ("POST", "/contacts/", "create_contact"),
        ("PATCH", "/contacts/{id}", "update_contact"),
        ("DELETE", "/contacts/{id}", "delete_contact"),
    ],
)
async def test_contact_service_failure_returns_500(
    api_client, owner_ids, monkeypatch, method, path, service_method
):
    failure = ContactServiceError("Storage unavailable")
    mocked_operation = AsyncMock(side_effect=failure)
    monkeypatch.setattr(ContactService, service_method, mocked_operation)
    if method == "POST":
        payload = {"user_id": str(owner_ids[0]), "name": "Example"}
    elif method == "PATCH":
        payload = {"name": "Updated"}
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


# An unexpected programming error remains visible instead of becoming a handled contact error.
async def test_contact_api_does_not_swallow_programming_errors(api_client, monkeypatch):
    mocked_get = AsyncMock(side_effect=TypeError("Unexpected programming error"))
    monkeypatch.setattr(ContactService, "get_contact", mocked_get)
    with pytest.raises(TypeError, match="Unexpected programming error"):
        await api_client.get(f"/contacts/{uuid4()}")
    mocked_get.assert_awaited_once()
