import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.enums import EventStatus
from app.models import EventStatusHistory, TrackedRoleEvent
from app.schemas.event import EventCreate, EventUpdate
from app.services.event import EventService
from app.services.exceptions.event import (
    EventCreationError,
)

pytestmark = pytest.mark.anyio


# Caller rollback must restore the event and its status history together.
@pytest.mark.parametrize("operation", ["create", "update", "delete"])
async def test_event_rollback_preserves_event_and_history(
    sessions, saved_role, saved_event, operation
):
    created_id = None
    async with sessions() as session:
        service = EventService(session)
        if operation == "create":
            created = await service.create_event(
                EventCreate.model_validate(
                    {
                        "tracked_role_id": saved_role.id,
                        "title": "Unsaved",
                        "event_type": "interview",
                        "event_date": "2026-10-20",
                        "status": "pending",
                    }
                )
            )
            created_id = created.id
        elif operation == "update":
            await service.update_event(
                saved_event.id, EventUpdate(status=EventStatus.COMPLETED)
            )
        else:
            await service.delete_event(saved_event.id)
        await session.rollback()
    async with sessions() as session:
        found = await session.get(TrackedRoleEvent, saved_event.id)
        assert found is not None
        assert found.status == EventStatus.SCHEDULED
        event_history = list(
            await session.scalars(
                select(EventStatusHistory).where(
                    EventStatusHistory.event_id == found.id
                )
            )
        )
        assert len(event_history) == 1
        if operation == "create":
            assert created_id is not None
            assert await session.get(TrackedRoleEvent, created_id) is None
            event_history = list(
                await session.scalars(
                    select(EventStatusHistory).where(
                        EventStatusHistory.event_id == created_id
                    )
                )
            )
            assert event_history == []


# Caller rollback after a history failure must remove the already flushed event.
async def test_event_history_failure_rolls_back_inserted_parent(
    sessions, saved_role, monkeypatch
):
    async with sessions() as session:
        original_flush = session.flush
        inserted_ids = []
        database_error = SQLAlchemyError("History insert failed")

        async def fail_history_flush(*args, **kwargs):
            if any(isinstance(row, EventStatusHistory) for row in session.new):
                raise database_error
            await original_flush(*args, **kwargs)
            inserted_ids.extend(
                row.id
                for row in session.identity_map.values()
                if isinstance(row, TrackedRoleEvent)
            )

        monkeypatch.setattr(session, "flush", fail_history_flush)
        with pytest.raises(EventCreationError) as exc_info:
            await EventService(session).create_event(
                EventCreate.model_validate(
                    {
                        "tracked_role_id": saved_role.id,
                        "title": "Rejected",
                        "event_type": "interview",
                        "event_date": "2026-01-01",
                        "status": "pending",
                    }
                )
            )
        assert exc_info.value.__cause__ is database_error
        assert len(inserted_ids) == 1
        await session.rollback()
    async with sessions() as session:
        assert await session.get(TrackedRoleEvent, inserted_ids[0]) is None
        event_history = list(
            await session.scalars(
                select(EventStatusHistory).where(
                    EventStatusHistory.event_id == inserted_ids[0]
                )
            )
        )
        assert event_history == []
