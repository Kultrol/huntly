from datetime import timedelta

import pytest
from pydantic import ValidationError

from app.enums import EventStatus, EventType
from app.schemas.event import EventCreate
from tests.schemas.event.data import (
    CREATE_DATA,
    EVENT_DATE,
    EVENT_TIME,
    ROLE_ID,
)


# Optional scheduling and descriptive details may be omitted, null, or populated.
@pytest.mark.parametrize(
    "optional_data",
    [
        {},
        {"event_time": None, "notes": None, "url": None, "location": None},
        {"event_time": EVENT_TIME, "notes": "Prepare questions", "location": "Remote"},
    ],
    ids=[
        "optional-fields-omitted",
        "optional-fields-null",
        "optional-fields-populated",
    ],
)
def test_valid_event_create(optional_data) -> None:
    event = EventCreate(**{**CREATE_DATA, **optional_data})

    assert event.tracked_role_id == ROLE_ID
    assert event.title == "Technical interview"
    assert event.event_type is EventType.INTERVIEW
    assert event.event_date == EVENT_DATE
    assert event.status is EventStatus.SCHEDULED
    assert event.custom_type_name is None
    assert event.event_time == optional_data.get("event_time")
    assert event.notes == optional_data.get("notes")
    assert event.url is None
    assert event.location == optional_data.get("location")


# Creating an event requires its parent, title, category, date, and status.
@pytest.mark.parametrize(
    "missing_field", ["tracked_role_id", "title", "event_type", "event_date", "status"]
)
def test_event_create_requires_declared_fields(missing_field) -> None:
    event_data = CREATE_DATA.copy()
    del event_data[missing_field]

    with pytest.raises(ValidationError) as excinfo:
        EventCreate(**event_data)

    assert any(
        error["loc"] == (missing_field,) and error["type"] == "missing"
        for error in excinfo.value.errors()
    )


# Required event values must reject nulls and malformed parent identifiers.
@pytest.mark.parametrize(
    ("field", "value", "expected_error_type"),
    [
        pytest.param(
            "tracked_role_id", "invalid-uuid", "uuid_parsing", id="invalid-role-id"
        ),
        pytest.param("tracked_role_id", None, "uuid_type", id="null-role-id"),
        pytest.param("title", None, "string_type", id="null-title"),
        pytest.param("event_type", None, "enum", id="null-event-type"),
        pytest.param("event_date", None, "date_type", id="null-date"),
        pytest.param("status", None, "enum", id="null-status"),
    ],
)
def test_invalid_event_create(field, value, expected_error_type) -> None:
    with pytest.raises(ValidationError) as excinfo:
        EventCreate(**{**CREATE_DATA, field: value})

    assert any(
        error["loc"] == (field,) and error["type"] == expected_error_type
        for error in excinfo.value.errors()
    )


# Request strings must become typed IDs, enums, dates, and offset-preserving times.
def test_event_create_parses_request_strings() -> None:
    event = EventCreate(
        **{
            **CREATE_DATA,
            "tracked_role_id": str(ROLE_ID),
            "event_type": "assessment",
            "event_date": "2026-10-12",
            "event_time": "14:30:00-04:00",
            "status": "pending",
        }
    )

    assert event.tracked_role_id == ROLE_ID
    assert event.event_type is EventType.ASSESSMENT
    assert event.event_date == EVENT_DATE
    assert event.event_time == EVENT_TIME
    assert event.event_time is not None
    assert event.event_time.utcoffset() == timedelta(hours=-4)
    assert event.status is EventStatus.PENDING
