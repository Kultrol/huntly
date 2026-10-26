from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.enums import EventStatus
from app.models import EventStatusHistory, TrackedRoleEvent
from app.schemas.event import EventCreate, EventUpdate
from app.services.event import EventService

pytestmark = pytest.mark.anyio


# Creating an event must save its details and initial status at the supplied time.
async def test_event_creation_persists_initial_history(sessions, saved_role):
    occurred_at = datetime(2026, 1, 1, tzinfo=UTC)
    data = EventCreate.model_validate(
        {
            "tracked_role_id": saved_role.id,
            "title": "  Phone   screen ",
            "event_type": "recruiter_screen",
            "event_date": "2026-10-20",
            "event_time": "09:30:00",
            "status": "scheduled",
            "url": "https://example.com/meeting",
            "location": "Remote",
        }
    )
    async with sessions() as session:
        event = await EventService(session).create_event(data, occurred_at=occurred_at)
        await session.commit()
    async with sessions() as session:
        found = await EventService(session).get_event(event.id)
        assert found.title == "Phone screen"
        assert found.tracked_role_id == saved_role.id
        assert found.event_date.isoformat() == "2026-10-20"
        assert found.event_time is not None
        assert found.event_time.isoformat() == "09:30:00"
        assert found.url == "https://example.com/meeting"
        assert found.location == "Remote"
        history = list(
            await session.scalars(
                select(EventStatusHistory).where(
                    EventStatusHistory.event_id == event.id
                )
            )
        )
        assert len(history) == 1
        assert history[0].from_status is None
        assert history[0].to_status == EventStatus.SCHEDULED
        assert history[0].occurred_at == occurred_at
        assert history[0].created_at > occurred_at


# Only an actual event status change must append a history row.
@pytest.mark.parametrize(
    "patch, expected_status, count",
    [
        ({"status": "completed"}, "completed", 2),
        ({"status": "scheduled"}, "scheduled", 1),
        ({"title": "Renamed"}, "scheduled", 1),
        ({"notes": None}, "scheduled", 1),
        ({}, "scheduled", 1),
    ],
)
async def test_event_update_only_records_changed_status(
    sessions, saved_event, patch, expected_status, count
):
    occurred_at = datetime(2026, 2, 1, tzinfo=UTC)
    async with sessions() as session:
        await EventService(session).update_event(
            saved_event.id, EventUpdate.model_validate(patch), occurred_at=occurred_at
        )
        await session.commit()
    async with sessions() as session:
        found = await session.get(TrackedRoleEvent, saved_event.id)
        assert found is not None
        assert found.title == patch.get("title", "Phone screen")
        assert found.notes == patch.get("notes", "Original notes")
        assert found.status == expected_status
        history = list(
            await session.scalars(
                select(EventStatusHistory).where(
                    EventStatusHistory.event_id == found.id
                )
            )
        )
        assert len(history) == count
        if count == 2:
            changed = next(row for row in history if row.from_status is not None)
            assert changed.from_status == EventStatus.SCHEDULED
            assert changed.to_status == EventStatus.COMPLETED
            assert changed.occurred_at == occurred_at
