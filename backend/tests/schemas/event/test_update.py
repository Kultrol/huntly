from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.enums import EventStatus, EventType
from app.schemas.event import EventUpdate
from tests.schemas.event.data import (
    EVENT_DATE,
    EVENT_TIME,
)


# Event patches contain only supplied fields rather than all optional defaults.
@pytest.mark.parametrize(
    "event_data",
    [
        {},
        {"title": "Follow up"},
        {
            "event_type": EventType.FOLLOW_UP,
            "event_date": EVENT_DATE,
            "event_time": EVENT_TIME,
            "status": EventStatus.PENDING,
            "notes": "Send a thank-you",
            "location": "Remote",
        },
    ],
    ids=["empty-update", "single-field", "several-fields"],
)
def test_valid_event_update(event_data) -> None:
    event = EventUpdate(**event_data)

    assert event.model_dump(exclude_unset=True) == event_data


# Omitting an optional detail preserves it; an explicit null requests clearing it.
@pytest.mark.parametrize("field", ["event_time", "notes", "url", "location"])
def test_event_update_distinguishes_omission_from_explicit_null(field) -> None:
    omitted = EventUpdate()
    cleared = EventUpdate(**{field: None})

    assert omitted.model_dump(exclude_unset=True) == {}
    assert cleared.model_dump(exclude_unset=True) == {field: None}


# Patch serialization retains supplied scheduling values and their explicit time offset.
def test_event_update_parses_request_strings_for_serialization() -> None:
    event = EventUpdate.model_validate(
        {
            "event_type": "follow_up",
            "event_date": "2026-10-12",
            "event_time": "14:30:00-04:00",
            "status": "completed",
        }
    )

    assert event.event_type is EventType.FOLLOW_UP
    assert event.event_date == EVENT_DATE
    assert event.event_time == EVENT_TIME
    assert event.event_time is not None
    assert event.event_time.utcoffset() == timedelta(hours=-4)
    assert event.status is EventStatus.COMPLETED
    assert event.model_dump(mode="json", exclude_unset=True) == {
        "event_type": "follow_up",
        "event_date": "2026-10-12",
        "event_time": "14:30:00-04:00",
        "status": "completed",
    }


# A patch may omit required event fields but cannot explicitly clear them.
@pytest.mark.parametrize("field", ["title", "event_type", "event_date", "status"])
def test_update_reject_null_required_fields_raise_value_error(field):
    with pytest.raises(ValidationError) as excinfo:
        EventUpdate(**{field: None})

    assert any(
        error["loc"] == ()
        and error["type"] == "value_error"
        and error["msg"] == f"Value error, Event {field} cannot be null."
        for error in excinfo.value.errors()
    )
