from datetime import date, time, timedelta

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


async def test_upcoming_events_returns_five_ordered_eligible_events_for_owner(
    api_client, sessions, owner_ids, saved_role
):
    today = date(2026, 10, 20)
    tomorrow = today + timedelta(days=1)
    async with sessions.begin() as session:
        second_role = TrackedRole(
            user_id=owner_ids[0], title="Second role", status="saved"
        )
        foreign_role = TrackedRole(
            user_id=owner_ids[1], title="Foreign role", status="saved"
        )
        session.add_all([second_role, foreign_role])
        await session.flush()

        def event(
            title,
            *,
            role_id=saved_role.id,
            day=today,
            at=None,
            event_type="interview",
            status="scheduled",
        ):
            return TrackedRoleEvent(
                tracked_role_id=role_id,
                title=title,
                event_date=day,
                event_time=at,
                event_type=event_type,
                status=status,
            )

        interview_a = event("Interview A", at=time(9))
        interview_b = event("Interview B", at=time(9))
        follow_up = event(
            "Follow up", at=time(14), event_type="follow_up", status="pending"
        )
        application = event("Application deadline", event_type="application_deadline")
        offer = event(
            "Offer deadline",
            role_id=second_role.id,
            day=tomorrow,
            event_type="offer_deadline",
        )
        session.add_all(
            [
                offer,
                application,
                follow_up,
                interview_b,
                interview_a,
                event("Sixth qualifying event", day=tomorrow + timedelta(days=1)),
                event("Past interview", day=today - timedelta(days=1)),
                event("Foreign interview", role_id=foreign_role.id, at=time(8)),
                event("Assessment", at=time(8), event_type="assessment"),
                event("Completed interview", at=time(8), status="completed"),
                event("Cancelled interview", at=time(8), status="cancelled"),
                event("Missed interview", at=time(8), status="missed"),
            ]
        )

    response = await api_client.get(
        "/events/upcoming", params={"from_date": today.isoformat()}
    )
    assert response.status_code == 200
    interviews = sorted((interview_a, interview_b), key=lambda item: item.id)
    expected = [*interviews, follow_up, application, offer]
    data = response.json()
    assert data["user_id"] == str(owner_ids[0])
    assert [item["id"] for item in data["events"]] == [
        str(item.id) for item in expected
    ]


async def test_upcoming_events_identifies_owner_when_the_list_is_empty(
    api_client, owner_ids
):
    response = await api_client.get(
        "/events/upcoming", params={"from_date": "2026-10-20"}
    )
    assert response.status_code == 200
    assert response.json() == {"user_id": str(owner_ids[0]), "events": []}
