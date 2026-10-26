import pytest
from pydantic import ValidationError

from app.schemas.event import EventCreate, EventRead, EventUpdate
from tests.schemas.event.data import (
    CREATE_DATA,
    READ_DATA,
)


# Response, create, and patch schemas must each enforce their declared field types.
@pytest.mark.parametrize(
    "schema, base_data",
    [(EventRead, READ_DATA), (EventCreate, CREATE_DATA), (EventUpdate, {})],
    ids=["read", "create", "update"],
)
@pytest.mark.parametrize(
    ("field", "value", "expected_error_type"),
    [
        pytest.param("title", 123, "string_type", id="invalid-title-type"),
        pytest.param("event_type", "unknown", "enum", id="unknown-event-type"),
        pytest.param("event_date", {}, "date_type", id="invalid-date-type"),
        pytest.param(
            "event_date",
            "2026-13-12",
            "date_from_datetime_parsing",
            id="invalid-calendar-date",
        ),
        pytest.param("event_time", {}, "time_type", id="invalid-time-type"),
        pytest.param("event_time", "25:00:00", "time_parsing", id="invalid-clock-time"),
        pytest.param("status", "unknown", "enum", id="unknown-status"),
        pytest.param("notes", 123, "string_type", id="invalid-notes-type"),
        pytest.param("location", 123, "string_type", id="invalid-location-type"),
    ],
)
def test_event_field_types(
    schema, base_data, field, value, expected_error_type
) -> None:
    with pytest.raises(ValidationError) as excinfo:
        schema(**{**base_data, field: value})

    assert any(
        error["loc"] == (field,) and error["type"] == expected_error_type
        for error in excinfo.value.errors()
    )


# Write schemas strip surrounding whitespace before accepting an event title.
@pytest.mark.parametrize(
    "schema, base_data",
    [(EventCreate, CREATE_DATA), (EventUpdate, {})],
    ids=["create", "update"],
)
def test_event_title_string_constraints(schema, base_data) -> None:
    event = schema(**{**base_data, "title": "  Interview  "})

    assert event.title == "Interview"


# A title containing no visible text must not pass either write schema.
@pytest.mark.parametrize(
    "schema, base_data",
    [(EventCreate, CREATE_DATA), (EventUpdate, {})],
    ids=["create", "update"],
)
@pytest.mark.parametrize(
    "title", ["", "   ", "\t\n"], ids=["empty", "spaces", "whitespace"]
)
def test_event_title_cannot_be_blank(schema, base_data, title) -> None:
    with pytest.raises(ValidationError) as excinfo:
        schema(**{**base_data, "title": title})

    assert any(
        error["loc"] == ("title",) and error["type"] == "string_too_short"
        for error in excinfo.value.errors()
    )


# Event URLs require HTTP(S), a scheme, a host, and a supported input type.
@pytest.mark.parametrize(
    ("schema", "base_data"),
    [(EventCreate, CREATE_DATA), (EventUpdate, {})],
    ids=["create", "update"],
)
@pytest.mark.parametrize(
    ("url", "expected_error_type"),
    [
        ("example.com", "url_parsing"),
        ("ftp://example.com", "url_scheme"),
        (2, "url_type"),
        ("https://", "url_parsing"),
    ],
)
def test_event_validate_url_invalid_url(schema, base_data, url, expected_error_type):
    with pytest.raises(ValidationError) as excinfo:
        schema(**{**base_data, "url": url})

    assert any(
        error["loc"] == ("url",) and error["type"] == expected_error_type
        for error in excinfo.value.errors()
    )


# Normalized event URLs stay plain text, and null continues to mean no URL.
@pytest.mark.parametrize(
    ("schema", "base_data"),
    [(EventCreate, CREATE_DATA), (EventUpdate, {})],
    ids=["create", "update"],
)
@pytest.mark.parametrize(
    ("url", "expected_url"),
    [("https://example.com", "https://example.com/"), (None, None)],
    ids=["normalized-url", "null-url"],
)
def test_event_validate_url_returns_string_or_none(
    schema, base_data, url, expected_url
):
    event = schema(**{**base_data, "url": url})

    assert event.url == expected_url
    if expected_url is not None:
        assert isinstance(event.url, str)
