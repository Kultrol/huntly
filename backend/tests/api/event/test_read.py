from datetime import date

import pytest

from app.models import TrackedRole, TrackedRoleEvent

pytestmark = pytest.mark.anyio


# Fetching an event returns the saved activity and the opportunity it belongs to.
async def test_event_get_returns_saved_record(api_client, saved_event):
    response = await api_client.get(f"/events/{saved_event.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(saved_event.id)
    assert data["tracked_role_id"] == str(saved_event.tracked_role_id)
    assert data["title"] == "Phone screen"
    assert data["event_type"] == "recruiter_screen"
    assert data["status"] == "scheduled"
    assert data["event_date"] == "2026-10-20"


# An event list includes only activities belonging to the requested opportunity.
async def test_event_list_excludes_other_roles_events(
    api_client, sessions, owner_ids, saved_role, saved_event
):
    async with sessions.begin() as session:
        other_role = TrackedRole(
            user_id=owner_ids[0], title="Other role", status="saved"
        )
        session.add(other_role)
        await session.flush()
        session.add(
            TrackedRoleEvent(
                tracked_role_id=other_role.id,
                title="Other event",
                event_date=date(2026, 10, 20),
                event_type="interview",
                status="pending",
            )
        )
    response = await api_client.get(
        "/events/", params={"tracked_role_id": str(saved_role.id)}
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(saved_event.id)]
    assert response.json()[0]["tracked_role_id"] == str(saved_role.id)


# An existing opportunity with no events receives an empty activity list.
async def test_event_list_for_existing_role_without_events_is_empty(
    api_client, saved_role
):
    response = await api_client.get(
        "/events/", params={"tracked_role_id": str(saved_role.id)}
    )
    assert response.status_code == 200
    assert response.json() == []
