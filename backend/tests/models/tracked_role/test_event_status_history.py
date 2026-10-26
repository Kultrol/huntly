from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.enums import EventStatus
from app.models import EventStatusHistory


# Initial history may omit the previous status; valid status strings become enums.
@pytest.mark.parametrize("from_status", [None, "scheduled"])
def test_history_coerces_canonical_statuses(from_status):
    history = EventStatusHistory(from_status=from_status, to_status="scheduled")
    assert history.from_status == (
        None if from_status is None else EventStatus(from_status)
    )
    assert history.to_status is EventStatus("scheduled")


# Invalid statuses are rejected on construction and cannot replace valid statuses.
@pytest.mark.parametrize(
    "field, value",
    [("from_status", "unknown"), ("to_status", "unknown"), ("to_status", None)],
)
def test_history_rejects_invalid_status_on_construction_and_assignment(field, value):
    with pytest.raises(ValueError):
        EventStatusHistory(**{field: value})
    history = EventStatusHistory(from_status=None, to_status="scheduled")
    original_value = getattr(history, field)
    with pytest.raises(ValueError):
        setattr(history, field, value)
    assert getattr(history, field) == original_value


# Backdated transitions retain separate occurrence and database recording times.
@pytest.mark.anyio
async def test_history_round_trip_separates_occurrence_from_recording(
    sessions, saved_event
):
    occurred_at = datetime(2020, 1, 1, tzinfo=UTC)
    async with sessions.begin() as session:
        history = EventStatusHistory(
            event_id=saved_event.id,
            from_status=None,
            to_status="scheduled",
            occurred_at=occurred_at,
        )
        session.add(history)
    async with sessions() as session:
        found = await session.get(EventStatusHistory, history.id)
        assert found is not None
        assert found.event_id == saved_event.id
        assert found.from_status is None
        assert found.to_status == "scheduled"
        assert found.occurred_at == occurred_at
        assert found.created_at > occurred_at


# Transition history requires a reference to an existing parent record.
@pytest.mark.anyio
@pytest.mark.parametrize("parent_id", [None, "missing"])
async def test_history_requires_existing_parent(sessions, parent_id):
    async with sessions() as session:
        session.add(
            EventStatusHistory(
                event_id=uuid4() if parent_id else None,
                to_status="scheduled",
                occurred_at=datetime.now(UTC),
            )
        )
        with pytest.raises(IntegrityError):
            await session.flush()
        await session.rollback()
