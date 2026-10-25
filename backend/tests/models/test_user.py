from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.models import Company, Contact, TrackedRole, User

pytestmark = pytest.mark.anyio


# An owner can load its companies, contacts, and opportunities through relationships.
async def test_user_identity_and_owned_relationships(
    sessions, owner_ids, saved_company, saved_contact, saved_role
):
    async with sessions() as session:
        user = await session.scalar(
            select(User)
            .where(User.id == owner_ids[0])
            .options(
                selectinload(User.companies),
                selectinload(User.contacts),
                selectinload(User.tracked_roles),
            )
        )
        assert user is not None
        assert isinstance(user.id, UUID)
        assert user.name == "Example owner"
        assert [company.id for company in user.companies] == [saved_company.id]
        assert [contact.id for contact in user.contacts] == [saved_contact.id]
        assert [role.id for role in user.tracked_roles] == [saved_role.id]


# Deleting an owner with dependent records fails and rollback preserves both sides.
@pytest.mark.parametrize("owned_model", [Company, Contact, TrackedRole])
async def test_user_deletion_with_owned_records_fails_without_data_loss(
    sessions, owner_ids, owned_model
):
    fields = (
        {"title": "Developer", "status": "saved"}
        if owned_model is TrackedRole
        else {"name": "Example"}
    )
    async with sessions.begin() as session:
        owned = owned_model(user_id=owner_ids[0], **fields)
        session.add(owned)
    async with sessions() as session:
        user = await session.get(User, owner_ids[0])
        await session.delete(user)
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()
    async with sessions() as session:
        assert await session.get(User, owner_ids[0]) is not None
        assert await session.get(owned_model, owned.id) is not None
