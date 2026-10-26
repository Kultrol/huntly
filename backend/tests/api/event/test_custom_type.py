import pytest
from sqlalchemy import select

from app.models import EventStatusHistory, TrackedRoleEvent

pytestmark = pytest.mark.anyio


# Selecting a custom event type without a label leaves the event and history unchanged.
async def test_event_patch_rejects_incomplete_custom_pair_without_changes(
    api_client, sessions, saved_event
):
    response = await api_client.patch(
        f"/events/{saved_event.id}",
        json={"event_type": "custom", "status": "completed"},
    )
    assert response.status_code == 400
    async with sessions() as session:
        event = await session.get(TrackedRoleEvent, saved_event.id)
        assert event is not None
        assert event.event_type == "recruiter_screen"
        assert event.status == "scheduled"
        history = list(
            await session.scalars(
                select(EventStatusHistory).where(
                    EventStatusHistory.event_id == event.id
                )
            )
        )
        assert len(history) == 1


# An event can receive a custom type and label while explicitly clearing its notes.
async def test_event_patch_sets_custom_pair_and_clears_notes(
    api_client, sessions, saved_event
):
    response = await api_client.patch(
        f"/events/{saved_event.id}",
        json={
            "event_type": "custom",
            "custom_type_name": "Portfolio review",
            "notes": None,
        },
    )
    assert response.status_code == 200
    assert response.json()["custom_type_name"] == "Portfolio review"
    assert response.json()["notes"] is None
    assert response.json()["title"] == "Phone screen"
    async with sessions() as session:
        event = await session.get(TrackedRoleEvent, saved_event.id)
        assert event is not None
        assert event.event_type == "custom"
        assert event.custom_type_name == "Portfolio review"
        assert event.notes is None
        assert event.title == "Phone screen"


# Switching to a built-in event type must also clear the previously saved custom label.
async def test_event_patch_rejects_canonical_type_with_existing_custom_label(
    api_client, sessions, custom_event
):
    assert custom_event.event_type == "custom"
    assert custom_event.custom_type_name == "Portfolio review"
    response = await api_client.patch(
        f"/events/{custom_event.id}", json={"event_type": "interview"}
    )
    assert response.status_code == 400
    async with sessions() as session:
        event = await session.get(TrackedRoleEvent, custom_event.id)
        assert event is not None
        assert event.event_type == "custom"
        assert event.custom_type_name == "Portfolio review"


# Returning an event to a built-in type succeeds when its custom label is cleared.
async def test_event_patch_clears_custom_label_when_returning_to_canonical_type(
    api_client, sessions, custom_event
):
    response = await api_client.patch(
        f"/events/{custom_event.id}",
        json={"event_type": "interview", "custom_type_name": None},
    )
    assert response.status_code == 200
    assert response.json()["custom_type_name"] is None
    async with sessions() as session:
        event = await session.get(TrackedRoleEvent, custom_event.id)
        assert event is not None
        assert event.event_type == "interview"
        assert event.custom_type_name is None
