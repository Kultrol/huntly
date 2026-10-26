import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.enums import RelationshipType
from app.models import (
    Contact,
    TrackedRole,
    TrackedRoleContact,
)

pytestmark = pytest.mark.anyio


# Links expose both relationship views and keep opportunity notes separate.
async def test_contact_link_preserves_opportunity_context_and_exposes_views(
    sessions, saved_contact, saved_role
):
    async with sessions.begin() as session:
        link = TrackedRoleContact(
            tracked_role_id=saved_role.id,
            contact_id=saved_contact.id,
            relationship_type=RelationshipType.REFERRAL,
            notes="Introduced to hiring manager",
        )
        session.add(link)
    async with sessions() as session:
        found = await session.get(TrackedRoleContact, link.id)
        assert found is not None
        assert found.relationship_type == RelationshipType.REFERRAL
        assert found.notes == "Introduced to hiring manager"
        role = await session.scalar(
            select(TrackedRole)
            .where(TrackedRole.id == saved_role.id)
            .options(selectinload(TrackedRole.contacts))
        )
        contact = await session.scalar(
            select(Contact)
            .where(Contact.id == saved_contact.id)
            .options(selectinload(Contact.tracked_roles))
        )
        assert [person.id for person in role.contacts] == [saved_contact.id]
        assert [item.id for item in contact.tracked_roles] == [saved_role.id]
        assert contact.notes == "Original notes"


# Each opportunity-contact pair is unique, and a rejected duplicate preserves the link.
async def test_contact_link_pair_is_unique(sessions, saved_contact, saved_role):
    async with sessions.begin() as session:
        original = TrackedRoleContact(
            tracked_role_id=saved_role.id, contact_id=saved_contact.id
        )
        session.add(original)
    async with sessions() as session:
        session.add(
            TrackedRoleContact(
                tracked_role_id=saved_role.id, contact_id=saved_contact.id
            )
        )
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()
    async with sessions() as session:
        links = list(
            await session.scalars(
                select(TrackedRoleContact).where(
                    TrackedRoleContact.tracked_role_id == saved_role.id
                )
            )
        )
        assert [link.id for link in links] == [original.id]
        assert links[0].relationship_type is None


# Deleting either linked record removes the association and preserves the other record.
@pytest.mark.parametrize("deleted_parent", ["role", "contact"])
async def test_deleting_either_parent_removes_link_only(
    sessions, saved_role, saved_contact, deleted_parent
):
    async with sessions.begin() as session:
        link = TrackedRoleContact(
            tracked_role_id=saved_role.id, contact_id=saved_contact.id
        )
        session.add(link)
    async with sessions() as session:
        parent = await session.get(
            TrackedRole if deleted_parent == "role" else Contact,
            saved_role.id if deleted_parent == "role" else saved_contact.id,
        )
        await session.delete(parent)
        await session.commit()
    async with sessions() as session:
        assert await session.get(TrackedRoleContact, link.id) is None
        assert (await session.get(TrackedRole, saved_role.id) is None) == (
            deleted_parent == "role"
        )
        assert (await session.get(Contact, saved_contact.id) is None) == (
            deleted_parent == "contact"
        )


# Foreign keys allow cross-owner links; callers must enforce matching ownership.
async def test_foreign_keys_allow_cross_owner_links_so_callers_must_check_ownership(
    sessions, owner_ids, saved_role
):
    async with sessions.begin() as session:
        contact = Contact(user_id=owner_ids[1], name="Other owner contact")
        session.add(contact)
        await session.flush()
        link = TrackedRoleContact(contact_id=contact.id, tracked_role_id=saved_role.id)
        session.add(link)
    async with sessions() as session:
        found = await session.get(TrackedRoleContact, link.id)
        assert found is not None
        assert found.contact_id == contact.id
        assert found.tracked_role_id == saved_role.id
