from uuid import uuid4

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.exc import DataError, IntegrityError

from app.enums import TrackedRoleStatus
from app.models import Company, Contact, TrackedRole

pytestmark = pytest.mark.anyio


# Committed companies retain normalized names, ownership, and storage timestamps.
async def test_company_is_saved_and_can_be_reloaded(sessions, owner_ids):
    async with sessions() as session:
        company = Company(user_id=owner_ids[0], name=" Ryder ")
        session.add(company)
        await session.flush()

        company_id = company.id
        assert company_id is not None
        await session.commit()

    async with sessions() as session:
        saved = await session.get(Company, company_id)

        assert saved is not None
        assert saved.user_id == owner_ids[0]
        assert saved.name == "Ryder"
        assert saved.normalized_name == "ryder"
        assert saved.created_at is not None
        assert saved.updated_at is not None


# Company-name uniqueness is scoped to an owner rather than the whole database.
async def test_company_same_company_name_is_allowed_for_different_users(
    sessions, owner_ids
):
    async with sessions() as session:
        user_1_company = Company(user_id=owner_ids[0], name="Amazon")
        user_2_company = Company(user_id=owner_ids[1], name="Amazon")
        session.add(user_1_company)
        session.add(user_2_company)
        await session.flush()

        user_1_company_id = user_1_company.id
        user_2_company_id = user_2_company.id

        assert user_1_company_id is not None
        assert user_2_company_id is not None
        await session.commit()

    async with sessions() as session:
        company_1 = await session.get(Company, user_1_company_id)
        company_2 = await session.get(Company, user_2_company_id)

        assert company_1 is not None
        assert company_2 is not None
        assert company_1.name == "Amazon"
        assert company_2.name == "Amazon"
        assert company_1.id != company_2.id
        assert company_1.user_id != company_2.user_id


# Deleting a company clears its affiliations without deleting contacts or opportunities.
async def test_contact_and_roles_remain_after_deletion_of_company(sessions, owner_ids):
    async with sessions() as session:
        company = Company(user_id=owner_ids[0], name="Google")
        session.add(company)
        await session.flush()
        company_id = company.id
        assert company_id is not None
        await session.commit()

    async with sessions() as session:
        role = TrackedRole(
            user_id=owner_ids[0],
            company_id=company_id,
            title="Some title",
            status=TrackedRoleStatus.APPLIED,
        )
        contact = Contact(user_id=owner_ids[0], company_id=company_id, name="John Doe")

        session.add(role)
        session.add(contact)

        await session.flush()

        role_id = role.id
        contact_id = contact.id

        await session.commit()

    async with sessions() as session:
        role = await session.get(TrackedRole, role_id)
        contact = await session.get(Contact, contact_id)
        company = await session.get(Company, company_id)

        assert role is not None
        assert contact is not None
        assert company is not None

        assert role.company_id is not None
        assert contact.company_id is not None
        assert role.company_id == company.id
        assert contact.company_id == company.id

    async with sessions() as session:
        await session.execute(delete(Company).where(Company.id == company_id))
        await session.flush()
        await session.commit()

    async with sessions() as session:
        assert await session.get(Company, company_id) is None
        role = await session.get(TrackedRole, role_id)
        contact = await session.get(Contact, contact_id)

        assert role is not None
        assert role.company_id is None
        assert contact is not None
        assert contact.company_id is None


# Changing a display name also refreshes the case-folded key used for duplicate checks.
@pytest.mark.parametrize(
    "name, expected_name, normalized_name",
    [
        ("  Acme\t LABS  ", "Acme LABS", "acme labs"),
        ("Straße GmbH", "Straße GmbH", "strasse gmbh"),
    ],
)
def test_company_normalizes_name_and_synchronizes_key_on_assignment(
    name, expected_name, normalized_name
):
    company = Company(name=name)
    assert company.name == expected_name
    assert company.normalized_name == normalized_name
    company.name = "  New   Company "
    assert company.name == "New Company"
    assert company.normalized_name == "new company"


# Invalid names are rejected without replacing the previous valid name and key.
@pytest.mark.parametrize("name", [None, 10, "", " \t"])
def test_company_rejects_invalid_name_on_construction_and_assignment(name):
    with pytest.raises(ValueError):
        Company(name=name)
    company = Company(name="Original")
    with pytest.raises(ValueError):
        company.name = name
    assert company.name == "Original"
    assert company.normalized_name == "original"


# ORM inserts and updates repair a manually altered duplicate-check key before saving.
async def test_company_write_repairs_manually_overridden_normalized_name(
    sessions, owner_ids
):
    async with sessions.begin() as session:
        company = Company(
            user_id=owner_ids[0], name="Acme", normalized_name="incorrect"
        )
        session.add(company)
    async with sessions() as session:
        found = await session.get(Company, company.id)
        assert found is not None
        assert found.normalized_name == "acme"
        found.name = "Renamed"
        found.normalized_name = "incorrect again"
        await session.commit()
    async with sessions() as session:
        found = await session.get(Company, company.id)
        assert found is not None
        assert found.name == "Renamed"
        assert found.normalized_name == "renamed"


# Duplicate company names are rejected for the same owner, preserving the original.
async def test_company_scoped_unique_constraint_rejects_duplicate(
    sessions, owner_ids, saved_company
):
    async with sessions() as session:
        session.add(Company(user_id=owner_ids[0], name=" AMAZON "))
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()
    async with sessions() as session:
        companies = list(
            await session.scalars(
                select(Company).where(Company.user_id == owner_ids[0])
            )
        )
        assert [company.id for company in companies] == [saved_company.id]
        assert companies[0].name == "Amazon"


# A company cannot be saved without an owner or with a reference to a nonexistent owner.
@pytest.mark.parametrize("user_id", [None, "missing"])
async def test_company_requires_existing_owner(sessions, user_id):
    async with sessions() as session:
        session.add(Company(user_id=uuid4() if user_id else None, name="Example"))
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()


# Each name column independently accepts 255 characters and rejects 256 in direct SQL.
@pytest.mark.parametrize("column_name", ["name", "normalized_name"])
async def test_company_database_name_length_limit(sessions, saved_company, column_name):
    async with sessions.begin() as session:
        await session.execute(
            text(f"UPDATE companies SET {column_name} = :value WHERE id = :id"),
            {"value": "a" * 255, "id": saved_company.id},
        )
    async with sessions() as session:
        found = await session.get(Company, saved_company.id)
        assert found is not None
        assert getattr(found, column_name) == "a" * 255

    async with sessions() as session:
        with pytest.raises(DataError):
            await session.execute(
                text(f"UPDATE companies SET {column_name} = :value WHERE id = :id"),
                {"value": "a" * 256, "id": saved_company.id},
            )
        await session.rollback()
    async with sessions() as session:
        found = await session.get(Company, saved_company.id)
        assert found is not None
        assert getattr(found, column_name) == "a" * 255
