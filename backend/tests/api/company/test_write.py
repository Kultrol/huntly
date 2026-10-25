from uuid import UUID

import pytest
from sqlalchemy import select

from app.models import Company, Contact, TrackedRole

pytestmark = pytest.mark.anyio


# Creating a company returns its cleaned name and saves the same values in the database.
async def test_company_create_returns_and_saves_normalized_fields(
    api_client, sessions, owner_ids
):
    response = await api_client.post(
        "/companies/",
        json={
            "user_id": str(owner_ids[0]),
            "name": "  Acme  ",
            "notes": "Original notes",
        },
    )
    assert response.status_code == 201
    data = response.json()
    company_id = UUID(data["id"])
    assert data["name"] == "Acme"
    assert data["user_id"] == str(owner_ids[0])
    assert data["normalized_name"] == "acme"
    assert data["notes"] == "Original notes"
    async with sessions() as session:
        found = await session.get(Company, company_id)
        assert found is not None
        assert found.name == "Acme"
        assert found.normalized_name == "acme"
        assert found.user_id == owner_ids[0]
        assert found.notes == "Original notes"


# Creating the same company with different spacing or case is rejected without adding a row.
async def test_company_duplicate_create_returns_400_without_extra_row(
    api_client, sessions, owner_ids, saved_company
):
    response = await api_client.post(
        "/companies/", json={"user_id": str(owner_ids[0]), "name": " AMAZON "}
    )
    assert response.status_code == 400
    async with sessions() as session:
        companies = list(
            await session.scalars(
                select(Company).where(Company.user_id == owner_ids[0])
            )
        )
        assert [company.id for company in companies] == [saved_company.id]
        assert companies[0].name == "Amazon"


# Updating a company keeps its omitted name and clears notes when null is supplied.
async def test_company_patch_preserves_name_and_clears_notes(
    api_client, sessions, saved_company
):
    async with sessions.begin() as session:
        company = await session.get(Company, saved_company.id)
        assert company is not None
        company.notes = "Original notes"
    response = await api_client.patch(
        f"/companies/{saved_company.id}", json={"location": "Seattle", "notes": None}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Amazon"
    assert response.json()["notes"] is None
    async with sessions() as session:
        found = await session.get(Company, saved_company.id)
        assert found is not None
        assert found.location == "Seattle"
        assert found.notes is None
        assert found.name == "Amazon"


# Renaming a company to an existing name is rejected without changing either record.
async def test_company_duplicate_patch_returns_400_without_changes(
    api_client, sessions, owner_ids, saved_company
):
    async with sessions.begin() as session:
        other_company = Company(user_id=owner_ids[0], name="Google")
        session.add(other_company)
    response = await api_client.patch(
        f"/companies/{saved_company.id}", json={"name": " google "}
    )
    assert response.status_code == 400
    async with sessions() as session:
        found = await session.get(Company, saved_company.id)
        other = await session.get(Company, other_company.id)
        assert found is not None
        assert other is not None
        assert found.name == "Amazon"
        assert other.name == "Google"


# Deleting a company keeps its contacts and opportunities but clears their company links.
async def test_company_delete_clears_links_and_preserves_contacts_and_roles(
    api_client, sessions, saved_company, saved_contact, saved_role
):
    response = await api_client.delete(f"/companies/{saved_company.id}")
    assert response.status_code == 204
    assert response.content == b""
    async with sessions() as session:
        assert await session.get(Company, saved_company.id) is None
        contact = await session.get(Contact, saved_contact.id)
        role = await session.get(TrackedRole, saved_role.id)
        assert contact is not None
        assert role is not None
        assert contact.company_id is None
        assert role.company_id is None
