from datetime import date, time

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.enums import EventStatus, EventType
from app.models import EventStatusHistory, TrackedRole, TrackedRoleEvent


# Events normalize titles and convert valid category and status strings into enums.
def test_event_normalizes_title_and_canonical_values():
    event = TrackedRoleEvent(
        title="  Phone   Screen ", event_type="interview", status="scheduled"
    )
    assert event.title == "Phone Screen"
    assert event.event_type is EventType.INTERVIEW
    assert event.status is EventStatus.SCHEDULED
    event.title = "  Technical Interview "
    assert event.title == "Technical Interview"


# Invalid event fields are rejected on construction and cannot replace valid values.
@pytest.mark.parametrize(
    "field, value",
    [
        ("title", " "),
        ("title", None),
        ("status", "unknown"),
        ("event_type", "unknown"),
        ("custom_type_name", "interview"),
        ("custom_type_name", "RECRUITER-SCREEN"),
        ("custom_type_name", " "),
    ],
)
def test_event_rejects_invalid_values_on_construction_and_assignment(field, value):
    with pytest.raises(ValueError):
        TrackedRoleEvent(**{field: value})
    event = TrackedRoleEvent(
        title="Interview", event_type="interview", status="scheduled"
    )
    original_value = getattr(event, field)
    with pytest.raises(ValueError):
        setattr(event, field, value)
    assert getattr(event, field) == original_value


# A custom category and label can be supplied in either order before the event is saved.
@pytest.mark.anyio
@pytest.mark.parametrize("label_first", [True, False])
async def test_custom_event_pair_persists_independent_of_assignment_order(
    sessions, saved_role, label_first
):
    fields = (
        {"custom_type_name": "  Portfolio   Review ", "event_type": "custom"}
        if label_first
        else {"event_type": "custom", "custom_type_name": "  Portfolio   Review "}
    )
    async with sessions.begin() as session:
        event = TrackedRoleEvent(
            title="Review",
            tracked_role_id=saved_role.id,
            status="pending",
            event_date=date(2026, 1, 1),
            **fields,
        )
        session.add(event)
    async with sessions() as session:
        found = await session.get(TrackedRoleEvent, event.id)
        assert found is not None
        assert found.event_type is EventType.CUSTOM
        assert found.custom_type_name == "Portfolio Review"


# Saving requires a custom label exactly when the event uses the custom category.
@pytest.mark.anyio
@pytest.mark.parametrize(
    "event_type, custom_type_name",
    [("custom", None), ("interview", "Portfolio review")],
)
async def test_event_rejects_incomplete_custom_pair_on_flush(
    sessions, saved_role, event_type, custom_type_name
):
    async with sessions() as session:
        session.add(
            TrackedRoleEvent(
                title="Review",
                tracked_role_id=saved_role.id,
                status="pending",
                event_date=date(2026, 1, 1),
                event_type=event_type,
                custom_type_name=custom_type_name,
            )
        )
        with pytest.raises(ValueError):
            await session.flush()
        await session.rollback()


# The current time column preserves wall-clock time and discards the UTC offset.
@pytest.mark.anyio
async def test_event_time_round_trip_retains_wall_clock_time(sessions, saved_event):
    async with sessions() as session:
        event = await session.get(TrackedRoleEvent, saved_event.id)
        event.event_time = time.fromisoformat("09:30:00-04:00")
        await session.commit()
    async with sessions() as session:
        found = await session.get(TrackedRoleEvent, saved_event.id)
        assert found is not None
        assert found.event_time == time(9, 30)
        assert found.event_time.tzinfo is None


# Deleting an event removes its history while preserving the parent opportunity.
@pytest.mark.anyio
async def test_event_delete_removes_history_but_keeps_role(
    sessions, saved_event, saved_role
):
    async with sessions() as session:
        await session.delete(await session.get(TrackedRoleEvent, saved_event.id))
        await session.commit()
    async with sessions() as session:
        assert await session.get(TrackedRoleEvent, saved_event.id) is None
        assert await session.get(TrackedRole, saved_role.id) is not None
        assert (
            list(
                await session.scalars(
                    select(EventStatusHistory).where(
                        EventStatusHistory.event_id == saved_event.id
                    )
                )
            )
            == []
        )


# The database enforces category-label pairing when direct SQL bypasses the ORM hook.
@pytest.mark.anyio
async def test_database_rejects_noncustom_event_with_label(sessions, saved_event):
    async with sessions() as session:
        with pytest.raises(IntegrityError):
            await session.execute(
                text(
                    "UPDATE tracked_role_events SET custom_type_name = 'Portfolio' WHERE id = :id"
                ),
                {"id": saved_event.id},
            )
        await session.rollback()
