from datetime import datetime
from uuid import UUID

import pytest
from sqlalchemy import select

from app.models import EventStatusHistory, TrackedRole, TrackedRoleEvent

pytestmark = pytest.mark.anyio


# Creating an event saves its schedule and records its starting status at the supplied time.
async def test_event_create_saves_schedule_and_initial_history(
    api_client, sessions, saved_role
):
    occurred_at = datetime.fromisoformat("2026-01-01T10:00:00+00:00")
    response = await api_client.post(
        "/events/",
        params={"occurred_at": occurred_at.isoformat()},
        json={
            "tracked_role_id": str(saved_role.id),
            "title": "Interview",
            "event_type": "interview",
            "event_date": "2026-10-20",
            "event_time": "09:30:00",
            "status": "scheduled",
        },
    )
    assert response.status_code == 201
    data = response.json()
    event_id = UUID(data["id"])
    assert data["title"] == "Interview"
    assert data["event_type"] == "interview"
    assert data["event_date"] == "2026-10-20"
    assert data["event_time"] == "09:30:00"
    assert data["status"] == "scheduled"
    async with sessions() as session:
        event = await session.get(TrackedRoleEvent, event_id)
        assert event is not None
        assert event.title == "Interview"
        assert event.tracked_role_id == saved_role.id
        assert event.event_date.isoformat() == "2026-10-20"
        assert event.event_time is not None
        assert event.event_time.isoformat() == "09:30:00"
        history = list(
            await session.scalars(
                select(EventStatusHistory).where(
                    EventStatusHistory.event_id == event_id
                )
            )
        )
        assert len(history) == 1
        assert history[0].from_status is None
        assert history[0].to_status == "scheduled"
        assert history[0].occurred_at == occurred_at


# Changing an event's status saves it and records one transition at the supplied time.
async def test_event_patch_saves_changed_status_and_history(
    api_client, sessions, saved_event
):
    occurred_at = datetime.fromisoformat("2026-02-01T10:00:00+00:00")
    response = await api_client.patch(
        f"/events/{saved_event.id}",
        params={"occurred_at": occurred_at.isoformat()},
        json={"status": "completed"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    async with sessions() as session:
        event = await session.get(TrackedRoleEvent, saved_event.id)
        assert event is not None
        assert event.status == "completed"
        assert event.title == "Phone screen"
        history = list(
            await session.scalars(
                select(EventStatusHistory).where(
                    EventStatusHistory.event_id == event.id
                )
            )
        )
        assert len(history) == 2
        initial = next(row for row in history if row.from_status is None)
        changed = next(row for row in history if row.from_status is not None)
        assert initial.to_status == "scheduled"
        assert changed.from_status == "scheduled"
        assert changed.to_status == "completed"
        assert changed.occurred_at == occurred_at


# Deleting an event removes its status history while keeping its parent opportunity.
async def test_event_delete_removes_history_and_preserves_role(
    api_client, sessions, saved_event, saved_role
):
    response = await api_client.delete(f"/events/{saved_event.id}")
    assert response.status_code == 204
    assert response.content == b""
    async with sessions() as session:
        assert await session.get(TrackedRoleEvent, saved_event.id) is None
        assert await session.get(TrackedRole, saved_role.id) is not None
        history = list(
            await session.scalars(
                select(EventStatusHistory).where(
                    EventStatusHistory.event_id == saved_event.id
                )
            )
        )
        assert history == []
