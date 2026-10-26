import pytest
from pydantic import ValidationError

from app.schemas.tracked_role import (
    TrackedRoleCreate,
)
from tests.schemas.tracked_role.data import (
    CREATE_DATA,
    NULL_DETAILS,
    POPULATED_DETAILS,
)


# New opportunities support omitted, null, and fully populated optional details.
@pytest.mark.parametrize(
    "details",
    [{}, NULL_DETAILS, POPULATED_DETAILS],
    ids=["omitted", "null", "populated"],
)
def test_valid_tracked_role_create(details) -> None:
    role = TrackedRoleCreate(**CREATE_DATA, **details)

    assert role.model_dump() == {**CREATE_DATA, **NULL_DETAILS, **details}


# A new opportunity needs an owner, a title, and an explicit lifecycle status.
@pytest.mark.parametrize("missing_field", ["user_id", "title", "status"])
def test_tracked_role_create_requires_owner_title_and_status(missing_field) -> None:
    role_data = CREATE_DATA.copy()
    del role_data[missing_field]

    with pytest.raises(ValidationError) as excinfo:
        TrackedRoleCreate(**role_data)

    assert any(
        error["loc"] == (missing_field,) and error["type"] == "missing"
        for error in excinfo.value.errors()
    )


# Required creation fields must reject nulls and malformed ownership identifiers.
@pytest.mark.parametrize(
    "field,value,error_type",
    [
        pytest.param("user_id", "bad-uuid", "uuid_parsing", id="invalid-owner"),
        pytest.param("user_id", 123, "uuid_type", id="invalid-owner-type"),
        pytest.param("user_id", None, "uuid_type", id="null-owner"),
        pytest.param("title", None, "string_type", id="null-title"),
        pytest.param("status", None, "enum", id="null-status"),
    ],
)
def test_invalid_tracked_role_create_required_fields(field, value, error_type) -> None:
    with pytest.raises(ValidationError) as excinfo:
        TrackedRoleCreate(**{**CREATE_DATA, field: value})

    assert any(
        error["loc"] == (field,) and error["type"] == error_type
        for error in excinfo.value.errors()
    )
