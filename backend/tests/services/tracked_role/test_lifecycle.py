from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models import (
    Company,
    Contact,
    EventStatusHistory,
    StatusHistory,
    TrackedRole,
    TrackedRoleContact,
    TrackedRoleEvent,
)
from app.schemas.tracked_role import TrackedRoleUpdate
from app.services.exceptions.tracked_role import (
    TrackedRoleNotFoundError,
)
from app.services.tracked_role import TrackedRoleService

pytestmark = pytest.mark.anyio


# Listing roles for one owner must exclude another owner's roles.
async def test_role_list_filters_owner(sessions, owner_ids, saved_role):
    async with sessions.begin() as session:
        session.add(
            TrackedRole(user_id=owner_ids[1], title="Other role", status="saved")
        )
    async with sessions() as session:
        roles = await TrackedRoleService(session).get_all_tracked_roles(owner_ids[0])
        assert [role.id for role in roles] == [saved_role.id]
        assert roles[0].user_id == owner_ids[0]


# Each operation on an unknown role must identify the missing role.
@pytest.mark.parametrize("operation", ["get", "update", "delete"])
async def test_missing_role_raises(sessions, operation):
    missing_id = uuid4()
    async with sessions() as session:
        service = TrackedRoleService(session)
        with pytest.raises(TrackedRoleNotFoundError, match=str(missing_id)):
            if operation == "get":
                await service.get_tracked_role_by_id(missing_id)
            elif operation == "update":
                await service.update_tracked_role(
                    missing_id, TrackedRoleUpdate(title="Missing")
                )
            else:
                await service.delete_tracked_role(missing_id)


# Deleting a role must remove its activity while keeping independent companies and
# contacts.
async def test_role_delete_cascades_activity_and_preserves_company_and_contact(
    sessions, saved_role, saved_event, saved_contact, saved_company
):
    async with sessions.begin() as session:
        link = TrackedRoleContact(
            tracked_role_id=saved_role.id, contact_id=saved_contact.id
        )
        session.add(link)
    async with sessions() as session:
        await TrackedRoleService(session).delete_tracked_role(saved_role.id)
        await session.commit()
    async with sessions() as session:
        assert await session.get(TrackedRole, saved_role.id) is None
        assert await session.get(TrackedRoleEvent, saved_event.id) is None
        assert await session.get(TrackedRoleContact, link.id) is None
        role_history = list(
            await session.scalars(
                select(StatusHistory).where(
                    StatusHistory.tracked_role_id == saved_role.id
                )
            )
        )
        assert role_history == []
        event_history = list(
            await session.scalars(
                select(EventStatusHistory).where(
                    EventStatusHistory.event_id == saved_event.id
                )
            )
        )
        assert event_history == []
        assert await session.get(Company, saved_company.id) is not None
        assert await session.get(Contact, saved_contact.id) is not None
