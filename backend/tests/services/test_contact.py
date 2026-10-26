from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, Contact, TrackedRole, TrackedRoleContact, User
from app.schemas.contact import ContactCreate, ContactUpdate
from app.services.contact import ContactService
from app.services.exceptions.contact import (
    ContactCompanyError,
    ContactCreationError,
    ContactDeletionError,
    ContactFetchingError,
    ContactNotFoundError,
    ContactUpdateError,
)

pytestmark = pytest.mark.anyio


# A new contact and all supplied details must survive a fresh database read.
async def test_contact_creation_persistence(sessions, owner_ids, saved_company):
    new_contact = ContactCreate(
        user_id=owner_ids[0],
        company_id=saved_company.id,
        name="  Jane   Doe  ",
        email="jane@example.com",
        phone_number="555-0100",
        role="Recruiter",
        linkedin_url="https://example.com/jane",
        notes="Referral",
    )
    async with sessions() as session:
        contact = await ContactService(session).create_contact(new_contact)
        await session.commit()

    async with sessions() as session:
        found = await ContactService(session).get_contact(contact.id)
        assert found.user_id == owner_ids[0]
        assert found.company_id == saved_company.id
        assert found.name == "Jane Doe"
        assert found.email == "jane@example.com"
        assert found.phone_number == "555-0100"
        assert found.role == "Recruiter"
        assert found.linkedin_url == "https://example.com/jane"
        assert found.notes == "Referral"


# Contact lists must filter by owner and sort equal names by ID.
async def test_contact_list_filters_owner_and_orders_by_name_and_id(
    sessions, owner_ids
):
    ids = sorted([uuid4(), uuid4()])
    async with sessions.begin() as session:
        session.add_all(
            [
                Contact(id=ids[1], user_id=owner_ids[0], name="Jane"),
                Contact(id=ids[0], user_id=owner_ids[0], name="Jane"),
                Contact(user_id=owner_ids[0], name="Zoe"),
                Contact(user_id=owner_ids[1], name="Aaron"),
            ]
        )
    async with sessions() as session:
        contacts = await ContactService(session).get_all_contacts(owner_ids[0])
        assert [contact.name for contact in contacts] == ["Jane", "Jane", "Zoe"]
        assert [contact.id for contact in contacts[:2]] == ids
        assert all(contact.user_id == owner_ids[0] for contact in contacts)


# Contact patches must distinguish omitted fields from explicit nulls.
@pytest.mark.parametrize(
    "patch, expected_company, expected_notes",
    [
        ({"name": "Janet"}, True, "Original notes"),
        ({"company_id": None, "notes": None}, False, None),
        ({}, True, "Original notes"),
    ],
)
async def test_contact_update_preserves_omitted_and_clears_explicit_null(
    sessions, saved_contact, saved_company, patch, expected_company, expected_notes
):
    async with sessions() as session:
        await ContactService(session).update_contact(
            saved_contact.id, ContactUpdate.model_validate(patch)
        )
        await session.commit()
    async with sessions() as session:
        found = await session.get(Contact, saved_contact.id)
        assert found is not None
        assert found.name == patch.get("name", "Jane Doe")
        assert found.company_id == (saved_company.id if expected_company else None)
        assert found.notes == expected_notes


# A contact cannot link to a missing company or another owner's company.
@pytest.mark.parametrize("operation", ["create", "update"])
@pytest.mark.parametrize("company_exists", [True, False])
async def test_contact_rejects_missing_or_other_owners_company(
    sessions, owner_ids, saved_contact, operation, company_exists
):
    company_id = uuid4()
    if company_exists:
        async with sessions.begin() as session:
            session.add(
                Company(id=company_id, user_id=owner_ids[1], name="Other company")
            )
    async with sessions() as session:
        service = ContactService(session)
        with pytest.raises(ContactCompanyError):
            if operation == "create":
                await service.create_contact(
                    ContactCreate(
                        user_id=owner_ids[0], name="Rejected", company_id=company_id
                    )
                )
            else:
                await service.update_contact(
                    saved_contact.id, ContactUpdate(company_id=company_id)
                )
        await session.rollback()
    async with sessions() as session:
        found = await session.get(Contact, saved_contact.id)
        assert found is not None
        assert found.company_id == saved_contact.company_id
        contacts = list(
            await session.scalars(
                select(Contact).where(Contact.user_id == owner_ids[0])
            )
        )
        assert [contact.id for contact in contacts] == [saved_contact.id]


# Deleting a contact must remove its role links while keeping the roles.
async def test_contact_delete_removes_links_and_preserves_role(
    sessions, saved_contact, saved_role
):
    async with sessions.begin() as session:
        link = TrackedRoleContact(
            contact_id=saved_contact.id, tracked_role_id=saved_role.id
        )
        session.add(link)
    async with sessions() as session:
        await ContactService(session).delete_contact(saved_contact.id)
        await session.commit()
    async with sessions() as session:
        assert await session.get(Contact, saved_contact.id) is None
        assert await session.get(TrackedRoleContact, link.id) is None
        assert await session.get(TrackedRole, saved_role.id) is not None


# Each operation on an unknown contact must identify the missing contact.
@pytest.mark.parametrize("operation", ["get", "update", "delete"])
async def test_missing_contact_raises(sessions, operation):
    missing_id = uuid4()
    async with sessions() as session:
        service = ContactService(session)
        with pytest.raises(ContactNotFoundError, match=str(missing_id)):
            if operation == "get":
                await service.get_contact(missing_id)
            elif operation == "update":
                await service.update_contact(missing_id, ContactUpdate(name="Jane"))
            else:
                await service.delete_contact(missing_id)


# Caller rollback must undo contact creation, updates, and deletion.
@pytest.mark.parametrize("operation", ["create", "update", "delete"])
async def test_contact_rollback_preserves_committed_state(
    sessions, owner_ids, saved_contact, operation
):
    created_id = None
    async with sessions() as session:
        service = ContactService(session)
        if operation == "create":
            created = await service.create_contact(
                ContactCreate(user_id=owner_ids[0], name="Unsaved")
            )
            created_id = created.id
        elif operation == "update":
            await service.update_contact(
                saved_contact.id, ContactUpdate(name="Unsaved")
            )
        else:
            await service.delete_contact(saved_contact.id)
        await session.rollback()
    async with sessions() as session:
        found = await session.get(Contact, saved_contact.id)
        assert found is not None
        assert found.name == "Jane Doe"
        if operation == "create":
            assert created_id is not None
            assert await session.get(Contact, created_id) is None


# Contact database failures must keep their cause and leave transaction control to the
# caller.
@pytest.mark.parametrize(
    "operation, failed_method, expected_error",
    [
        ("get", "get", ContactFetchingError),
        ("list", "scalars", ContactFetchingError),
        ("create", "flush", ContactCreationError),
        ("update", "flush", ContactUpdateError),
        ("delete", "flush", ContactDeletionError),
        ("update", "refresh", ContactUpdateError),
    ],
)
async def test_contact_database_failures_preserve_operation_and_cause(
    operation, failed_method, expected_error
):
    user_id = uuid4()
    record_id = uuid4()
    record = Contact(id=record_id, user_id=user_id, name="Jane")
    session = AsyncMock(spec=AsyncSession)
    parent = User(id=user_id, name="Owner")
    session.get.side_effect = lambda model, id: parent if model is User else record
    database_error = SQLAlchemyError("Database unavailable")
    getattr(session, failed_method).side_effect = database_error
    service = ContactService(session)
    with pytest.raises(expected_error) as exc_info:
        if operation == "get":
            await service.get_contact(record_id)
        elif operation == "list":
            await service.get_all_contacts(user_id)
        elif operation == "create":
            await service.create_contact(ContactCreate(user_id=user_id, name="Jane"))
        elif operation == "update":
            await service.update_contact(record_id, ContactUpdate(name="Janet"))
        else:
            await service.delete_contact(record_id)
    assert exc_info.value.__cause__ is database_error
    session.commit.assert_not_awaited()
    session.rollback.assert_not_awaited()


# Unexpected coding errors must escape without becoming contact service errors.
async def test_contact_service_does_not_wrap_programming_errors():
    session = AsyncMock(spec=AsyncSession)
    session.get.side_effect = TypeError("Unexpected programming error")
    with pytest.raises(TypeError, match="Unexpected programming error"):
        await ContactService(session).get_contact(uuid4())
