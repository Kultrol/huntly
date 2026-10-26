from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.tracked_role import (
    TrackedRoleRead,
)
from tests.schemas.tracked_role.data import (
    COMPANY_ID,
    NULL_DETAILS,
    POPULATED_DETAILS,
    READ_DATA,
    ROLE_ID,
    USER_ID,
)


# Stored opportunities support both unknown details and fully populated records.
@pytest.mark.parametrize(
    "details", [NULL_DETAILS, POPULATED_DETAILS], ids=["null-details", "all-details"]
)
def test_valid_tracked_role_read(details) -> None:
    role_data = {**READ_DATA, **details}

    role = TrackedRoleRead(**role_data)

    assert role.model_dump() == role_data


# Nullable opportunity details remain required keys in a complete stored response.
@pytest.mark.parametrize(
    "missing_field",
    [
        "id",
        "user_id",
        "company_id",
        "title",
        "status",
        "description",
        "role_type",
        "location",
        "source",
        "listing_url",
        "priority",
        "notes",
        "salary_min",
        "salary_max",
        "salary_currency",
        "applied_at",
        "created_at",
        "updated_at",
    ],
)
def test_tracked_role_read_requires_fields_even_when_nullable(missing_field) -> None:
    role_data = READ_DATA.copy()
    del role_data[missing_field]

    with pytest.raises(ValidationError) as excinfo:
        TrackedRoleRead(**role_data)

    assert any(
        error["loc"] == (missing_field,) and error["type"] == "missing"
        for error in excinfo.value.errors()
    )


# Response values must retain their declared ID, text, amount, and timestamp types.
@pytest.mark.parametrize(
    "field,value,error_type",
    [
        pytest.param("id", "bad-uuid", "uuid_parsing", id="invalid-id"),
        pytest.param("user_id", 123, "uuid_type", id="invalid-owner-type"),
        pytest.param("company_id", "bad-uuid", "uuid_parsing", id="invalid-company"),
        pytest.param("title", None, "string_type", id="null-title"),
        pytest.param("description", 123, "string_type", id="invalid-description"),
        pytest.param("location", [], "string_type", id="invalid-location"),
        pytest.param("source", 123, "string_type", id="invalid-source"),
        pytest.param("listing_url", [], "string_type", id="invalid-url-text-type"),
        pytest.param("notes", [], "string_type", id="invalid-notes"),
        pytest.param("salary_currency", 123, "string_type", id="invalid-currency"),
        pytest.param("salary_min", "salary", "decimal_parsing", id="invalid-salary"),
        pytest.param("applied_at", [], "datetime_type", id="invalid-applied-time"),
        pytest.param("created_at", None, "datetime_type", id="null-created-time"),
        pytest.param("updated_at", {}, "datetime_type", id="invalid-updated-time"),
    ],
)
def test_invalid_tracked_role_read_fields(field, value, error_type) -> None:
    role_data = {**READ_DATA, field: value}

    with pytest.raises(ValidationError) as excinfo:
        TrackedRoleRead(**role_data)

    assert any(
        error["loc"] == (field,) and error["type"] == error_type
        for error in excinfo.value.errors()
    )


# ORM-shaped opportunity data must populate the same flat response as a dictionary.
def test_tracked_role_read_from_attributes() -> None:
    stored_role = SimpleNamespace(**READ_DATA)

    role = TrackedRoleRead.model_validate(stored_role)

    assert role.model_dump() == READ_DATA


# JSON output must preserve decimal precision and expose scalar IDs, enums, and dates.
def test_tracked_role_read_json_serialization() -> None:
    role = TrackedRoleRead(**READ_DATA)

    serialized = role.model_dump(mode="json")

    assert serialized["id"] == str(ROLE_ID)
    assert serialized["user_id"] == str(USER_ID)
    assert serialized["company_id"] == str(COMPANY_ID)
    assert serialized["status"] == "saved"
    assert serialized["role_type"] == "full_time"
    assert serialized["priority"] == "high"
    assert serialized["salary_min"] == "80000.50"
    assert serialized["salary_max"] == "100000.00"
    assert serialized["applied_at"] == "2026-10-12T14:30:00Z"
    assert serialized["created_at"] == "2026-10-12T14:30:00Z"
    assert serialized["updated_at"] == "2026-10-12T14:30:00Z"
