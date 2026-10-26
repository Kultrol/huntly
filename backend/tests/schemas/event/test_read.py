from datetime import timedelta
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.enums import EventStatus, EventType
from app.schemas.event import EventRead
from tests.schemas.event.data import (
    CREATED_AT,
    EVENT_DATE,
    EVENT_ID,
    EVENT_TIME,
    READ_DATA,
    ROLE_ID,
    UPDATED_AT,
)


# Stored events support a date alone or an explicitly offset-bearing time.
@pytest.mark.parametrize(
    "optional_data",
    [
        {},
        {"event_time": EVENT_TIME, "notes": "Prepare questions", "location": "Remote"},
    ],
    ids=["nullable-fields-none", "nullable-fields-populated"],
)
def test_valid_event_read(optional_data) -> None:
    event_data = {**READ_DATA, **optional_data}

    event = EventRead(**event_data)

    assert event.model_dump() == event_data


# Nullable event details are still required keys in a complete persisted response.
@pytest.mark.parametrize(
    "missing_field",
    [
        "id",
        "tracked_role_id",
        "title",
        "event_type",
        "custom_type_name",
        "event_date",
        "event_time",
        "status",
        "notes",
        "url",
        "location",
        "created_at",
        "updated_at",
    ],
)
def test_event_read_requires_declared_fields(missing_field) -> None:
    event_data = READ_DATA.copy()
    del event_data[missing_field]

    with pytest.raises(ValidationError) as excinfo:
        EventRead(**event_data)

    assert any(
        error["loc"] == (missing_field,) and error["type"] == "missing"
        for error in excinfo.value.errors()
    )


# Stored response data must keep valid identifiers, text values, and timestamps.
@pytest.mark.parametrize(
    ("field", "value", "expected_error_type"),
    [
        pytest.param("id", "invalid-uuid", "uuid_parsing", id="invalid-id"),
        pytest.param("tracked_role_id", 123, "uuid_type", id="invalid-role-id-type"),
        pytest.param("custom_type_name", 123, "string_type", id="invalid-label-type"),
        pytest.param("url", 123, "string_type", id="invalid-url-type"),
        pytest.param("created_at", {}, "datetime_type", id="invalid-created-at-type"),
        pytest.param(
            "created_at",
            "not-a-date",
            "datetime_from_date_parsing",
            id="invalid-created-at-text",
        ),
        pytest.param("updated_at", None, "datetime_type", id="null-updated-at"),
    ],
)
def test_invalid_event_read(field, value, expected_error_type) -> None:
    with pytest.raises(ValidationError) as excinfo:
        EventRead(**{**READ_DATA, field: value})

    assert any(
        error["loc"] == (field,) and error["type"] == expected_error_type
        for error in excinfo.value.errors()
    )


# An ORM-shaped event must populate the same flat response as a dictionary.
def test_event_read_from_attributes() -> None:
    event = EventRead.model_validate(SimpleNamespace(**READ_DATA))

    assert event.model_dump() == READ_DATA


# Parsing and JSON output must preserve the event date and its explicit time offset.
def test_event_read_parses_and_serializes_request_strings() -> None:
    event = EventRead(
        **{
            **READ_DATA,
            "id": str(EVENT_ID),
            "tracked_role_id": str(ROLE_ID),
            "event_type": "interview",
            "event_date": "2026-10-12",
            "event_time": "14:30:00-04:00",
            "status": "scheduled",
            "created_at": "2026-10-10T12:00:00Z",
            "updated_at": "2026-10-11T12:00:00Z",
        }
    )

    assert event.id == EVENT_ID
    assert event.tracked_role_id == ROLE_ID
    assert event.event_type is EventType.INTERVIEW
    assert event.event_date == EVENT_DATE
    assert event.event_time == EVENT_TIME
    assert event.event_time is not None
    assert event.event_time.utcoffset() == timedelta(hours=-4)
    assert event.status is EventStatus.SCHEDULED
    assert event.created_at == CREATED_AT
    assert event.updated_at == UPDATED_AT
    assert event.model_dump(mode="json") == {
        "id": str(EVENT_ID),
        "tracked_role_id": str(ROLE_ID),
        "title": "Technical interview",
        "event_type": "interview",
        "custom_type_name": None,
        "event_date": "2026-10-12",
        "event_time": "14:30:00-04:00",
        "status": "scheduled",
        "notes": None,
        "url": None,
        "location": None,
        "created_at": "2026-10-10T12:00:00Z",
        "updated_at": "2026-10-11T12:00:00Z",
    }
