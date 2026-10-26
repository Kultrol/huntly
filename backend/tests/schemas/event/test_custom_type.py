import pytest
from pydantic import ValidationError

from app.enums import EventType
from app.schemas.event import EventCreate, EventUpdate
from tests.schemas.event.data import (
    CREATE_DATA,
)


# Custom labels cannot disguise built-in categories through case or separators.
# Separator-only labels must also be rejected as empty after normalization.
@pytest.mark.parametrize(
    ("schema", "base_data"),
    [(EventCreate, CREATE_DATA), (EventUpdate, {})],
    ids=["create", "update"],
)
@pytest.mark.parametrize(
    ("invalid_name", "expected_error_type"),
    [
        ("", "string_too_short"),
        ("interview", "value_error"),
        ("recruiter_screen", "value_error"),
        ("assessment", "value_error"),
        ("follow_up", "value_error"),
        ("application_deadline", "value_error"),
        ("offer_deadline", "value_error"),
        ("networking", "value_error"),
        ("custom", "value_error"),
        (" Interview ", "value_error"),
        ("RECRUITER-SCREEN", "value_error"),
        ("  ReCrUiTeR__--\tScReEn  ", "value_error"),
        (" _-_\t ", "value_error"),
    ],
)
def test_event_validate_custom_type_name_invalid_name(
    schema, base_data, invalid_name, expected_error_type
):
    with pytest.raises(ValidationError) as excinfo:
        schema(
            **{
                **base_data,
                "event_type": EventType.CUSTOM,
                "custom_type_name": invalid_name,
            }
        )

    assert any(
        error["loc"] == ("custom_type_name",) and error["type"] == expected_error_type
        for error in excinfo.value.errors()
    )


# Custom display labels collapse whitespace while preserving hyphens and underscores.
@pytest.mark.parametrize(
    ("schema", "base_data"),
    [(EventCreate, CREATE_DATA), (EventUpdate, {})],
    ids=["create", "update"],
)
@pytest.mark.parametrize(
    ("event_type", "custom_type_name", "expected_name"),
    [
        (EventType.CUSTOM, "  Portfolio\t review  ", "Portfolio review"),
        (EventType.CUSTOM, "Portfolio-review_v2", "Portfolio-review_v2"),
        (EventType.INTERVIEW, None, None),
    ],
    ids=[
        "normalized-custom-label",
        "preserved-display-separators",
        "null-custom-label",
    ],
)
def test_event_validate_custom_type_name_normalization(
    schema, base_data, event_type, custom_type_name, expected_name
):
    event = schema(
        **{
            **base_data,
            "event_type": event_type,
            "custom_type_name": custom_type_name,
        }
    )

    assert event.custom_type_name == expected_name


# A custom category requires a label, and other categories must not carry one.
@pytest.mark.parametrize(
    ("failure_modes_data", "expected_message"),
    [
        (
            {"event_type": EventType.CUSTOM, "custom_type_name": None},
            "Custom events require a custom type name.",
        ),
        (
            {"event_type": EventType.INTERVIEW, "custom_type_name": "Something Custom"},
            "Only custom events may have a custom type name.",
        ),
    ],
)
def test_create_validate_custom_type_value_error_raised(
    failure_modes_data, expected_message
):
    with pytest.raises(ValidationError) as excinfo:
        EventCreate(**{**CREATE_DATA, **failure_modes_data})

    assert any(
        error["loc"] == ()
        and error["type"] == "value_error"
        and error["msg"] == f"Value error, {expected_message}"
        for error in excinfo.value.errors()
    )
