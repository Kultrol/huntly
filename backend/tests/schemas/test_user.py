from collections import UserDict
from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schemas.user import UserCreate, UserRead, UserUpdate

USER_ID = UUID("11111111-1111-4111-8111-111111111111")


# UUID text must become an identifier without changing the public display name.
@pytest.mark.parametrize(
    "user_data",
    [
        pytest.param({"id": USER_ID, "name": "Kevin"}, id="uuid-object"),
        pytest.param({"id": str(USER_ID), "name": "Kevin"}, id="uuid-string"),
    ],
)
def test_valid_user_read(user_data) -> None:
    user = UserRead(**user_data)

    assert user.id == USER_ID
    assert user.name == "Kevin"


# A public user response needs a valid identifier and a text name.
@pytest.mark.parametrize(
    "user_data, expected_invalid_field, expected_error_type",
    [
        pytest.param({"name": "Kevin"}, "id", "missing", id="missing-id"),
        pytest.param({"id": USER_ID}, "name", "missing", id="missing-name"),
        pytest.param(
            {"id": "invalid-uuid", "name": "Kevin"},
            "id",
            "uuid_parsing",
            id="invalid-uuid",
        ),
        pytest.param(
            {"id": 123, "name": "Kevin"}, "id", "uuid_type", id="invalid-id-type"
        ),
        pytest.param(
            {"id": USER_ID, "name": 123},
            "name",
            "string_type",
            id="invalid-name-type",
        ),
    ],
)
def test_invalid_user_read(
    user_data, expected_invalid_field, expected_error_type
) -> None:
    with pytest.raises(ValidationError) as excinfo:
        UserRead(**user_data)

    assert any(
        error["loc"] == (expected_invalid_field,)
        and error["type"] == expected_error_type
        for error in excinfo.value.errors()
    )


# ORM-shaped user data must produce the public fields and a JSON-safe identifier.
def test_user_read_from_attributes_and_json_serialization() -> None:
    saved_user = SimpleNamespace(id=USER_ID, name="Kevin")

    user = UserRead.model_validate(saved_user)

    assert user.model_dump() == {"id": USER_ID, "name": "Kevin"}
    assert user.model_dump(mode="json") == {"id": str(USER_ID), "name": "Kevin"}


# Names retain internal spacing and Unicode text after outside whitespace is removed.
@pytest.mark.parametrize("schema", [UserCreate, UserUpdate], ids=["create", "update"])
@pytest.mark.parametrize(
    "name, expected_name",
    [
        pytest.param("Kevin", "Kevin", id="plain-name"),
        pytest.param("  Kevin  ", "Kevin", id="trim-surrounding-whitespace"),
        pytest.param("Kevin  Smith", "Kevin  Smith", id="preserve-internal-whitespace"),
        pytest.param("Kevin\nSmith", "Kevin\nSmith", id="preserve-internal-newline"),
        pytest.param("É", "É", id="single-character-name"),
    ],
)
def test_valid_user_names(schema, name, expected_name) -> None:
    user = schema(name=name)

    assert user.name == expected_name


# Both write schemas must reject blank names and non-text input.
@pytest.mark.parametrize("schema", [UserCreate, UserUpdate], ids=["create", "update"])
@pytest.mark.parametrize(
    "name, expected_error_type",
    [
        pytest.param("", "string_too_short", id="empty-name"),
        pytest.param(" \t\n ", "string_too_short", id="whitespace-only-name"),
        pytest.param(123, "string_type", id="number-instead-of-name"),
        pytest.param(["Kevin"], "string_type", id="list-instead-of-name"),
        pytest.param(
            "\x00Kevin", "string_pattern_mismatch", id="leading-null-character"
        ),
        pytest.param(
            "Kev\x00in", "string_pattern_mismatch", id="embedded-null-character"
        ),
        pytest.param(
            "Kevin\x00", "string_pattern_mismatch", id="trailing-null-character"
        ),
    ],
)
def test_invalid_user_names(schema, name, expected_error_type) -> None:
    with pytest.raises(ValidationError) as excinfo:
        schema(name=name)

    assert any(
        error["loc"] == ("name",) and error["type"] == expected_error_type
        for error in excinfo.value.errors()
    )


# Creating a user requires an explicit display name rather than a schema default.
def test_user_create_requires_name() -> None:
    with pytest.raises(ValidationError) as excinfo:
        UserCreate.model_validate({})

    assert any(
        error["loc"] == ("name",) and error["type"] == "missing"
        for error in excinfo.value.errors()
    )


# An omitted name stays outside a patch so it cannot erase the saved display name.
@pytest.mark.parametrize(
    "user_data, expected_update",
    [
        pytest.param({}, {}, id="name-omitted"),
        pytest.param({"name": "Kevin"}, {"name": "Kevin"}, id="name-provided"),
    ],
)
def test_user_update_only_dumps_provided_fields(user_data, expected_update) -> None:
    user = UserUpdate(**user_data)

    assert user.name == user_data.get("name")
    assert user.model_dump(exclude_unset=True) == expected_update


# Explicit null must be rejected for every supported update input format.
@pytest.mark.parametrize(
    "user_data",
    [
        pytest.param({"name": None}, id="dictionary"),
        pytest.param(UserDict({"name": None}), id="mapping"),
        pytest.param(SimpleNamespace(name=None), id="attributes"),
    ],
)
def test_user_update_rejects_explicit_null_name(user_data) -> None:
    with pytest.raises(ValidationError) as excinfo:
        UserUpdate.model_validate(user_data)

    assert any(
        error["loc"] == ("name",) and error["type"] == "value_error"
        for error in excinfo.value.errors()
    )


# Omission remains an empty patch for mappings and attribute-based inputs alike.
@pytest.mark.parametrize(
    "user_data",
    [
        pytest.param({}, id="dictionary"),
        pytest.param(UserDict(), id="mapping"),
        pytest.param(SimpleNamespace(), id="attributes"),
    ],
)
def test_user_update_omission_is_allowed_for_supported_inputs(user_data) -> None:
    user = UserUpdate.model_validate(user_data)

    assert user.model_dump(exclude_unset=True) == {}
