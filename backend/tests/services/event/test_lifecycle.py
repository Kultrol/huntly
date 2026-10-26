from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.models import EventStatusHistory, TrackedRole, TrackedRoleEvent
from app.schemas.event import EventCreate, EventUpdate
from app.services.event import EventService
from app.services.exceptions.event import (
    EventNotFoundError,
)
from app.services.exceptions.tracked_role import TrackedRoleNotFoundError

pytestmark = pytest.mark.anyio


# Event patches must keep the saved category and custom label compatible.
async def test_event_custom_type_pair_is_validated_against_stored_values(
    sessions, saved_event
):
    async with sessions() as session:
        with pytest.raises(ValidationError):
            await EventService(session).update_event(
                saved_event.id, EventUpdate.model_validate({"event_type": "custom"})
            )
        await session.rollback()
    async with sessions() as session:
        await EventService(session).update_event(
            saved_event.id,
            EventUpdate.model_validate(
                {"event_type": "custom", "custom_type_name": "Portfolio review"}
            ),
        )
        await session.commit()
    async with sessions() as session:
        with pytest.raises(ValidationError):
            await EventService(session).update_event(
                saved_event.id, EventUpdate.model_validate({"event_type": "interview"})
            )
        await session.rollback()
    async with sessions() as session:
        found = await session.get(TrackedRoleEvent, saved_event.id)
        assert found is not None
        assert found.event_type == "custom"
        assert found.custom_type_name == "Portfolio review"
        await EventService(session).update_event(
            saved_event.id,
            EventUpdate.model_validate(
                {"event_type": "interview", "custom_type_name": None}
            ),
        )
        await session.commit()
    async with sessions() as session:
        found = await session.get(TrackedRoleEvent, saved_event.id)
        assert found is not None
        assert found.event_type == "interview"
        assert found.custom_type_name is None


# Listing events must filter by role and distinguish an empty role from a missing one.
async def test_event_list_filters_parent_and_distinguishes_empty_from_missing(
    sessions, owner_ids, saved_role, saved_event
):
    async with sessions.begin() as session:
        other_role = TrackedRole(user_id=owner_ids[1], title="Other", status="saved")
        session.add(other_role)
    async with sessions() as session:
        service = EventService(session)
        events = await service.get_all_events(saved_role.id)
        assert [event.id for event in events] == [saved_event.id]
        assert await service.get_all_events(other_role.id) == []
        with pytest.raises(TrackedRoleNotFoundError):
            await service.get_all_events(uuid4())


# An unknown parent role must reject event creation before adding any row.
async def test_event_create_requires_existing_parent(sessions):
    data = EventCreate.model_validate(
        {
            "tracked_role_id": uuid4(),
            "title": "Missing parent",
            "event_type": "interview",
            "event_date": "2026-10-20",
            "status": "pending",
        }
    )
    async with sessions() as session:
        with pytest.raises(TrackedRoleNotFoundError, match=str(data.tracked_role_id)):
            await EventService(session).create_event(data)
        assert not session.new
        assert session.is_active


# Each operation on an unknown event must identify the missing event.
@pytest.mark.parametrize("operation", ["get", "update", "delete"])
async def test_missing_event_raises(sessions, operation):
    missing_id = uuid4()
    async with sessions() as session:
        service = EventService(session)
        with pytest.raises(EventNotFoundError, match=str(missing_id)):
            if operation == "get":
                await service.get_event(missing_id)
            elif operation == "update":
                await service.update_event(missing_id, EventUpdate(title="Missing"))
            else:
                await service.delete_event(missing_id)


# Deleting an event must remove its history while keeping the parent role.
async def test_event_delete_removes_history_and_preserves_parent(
    sessions, saved_event, saved_role
):
    async with sessions() as session:
        await EventService(session).delete_event(saved_event.id)
        await session.commit()
    async with sessions() as session:
        assert await session.get(TrackedRoleEvent, saved_event.id) is None
        event_history = list(
            await session.scalars(
                select(EventStatusHistory).where(
                    EventStatusHistory.event_id == saved_event.id
                )
            )
        )
        assert event_history == []
        assert await session.get(TrackedRole, saved_role.id) is not None
