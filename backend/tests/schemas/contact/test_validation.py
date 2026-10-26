import pytest
from pydantic import ValidationError

from app.schemas.contact import ContactCreate, ContactUpdate
from tests.schemas.contact.data import (
    CREATE_CONTACT_DATA,
)


# Names are trimmed without collapsing internal spaces or excluding boundary lengths.
@pytest.mark.parametrize(
    "schema, base_data",
    [(ContactCreate, CREATE_CONTACT_DATA), (ContactUpdate, {})],
    ids=["create", "update"],
)
@pytest.mark.parametrize(
    "name, expected_name",
    [
        pytest.param("Kevin", "Kevin", id="plain-name"),
        pytest.param(" \tKevin\n ", "Kevin", id="trim-surrounding-whitespace"),
        pytest.param("Kevin  Smith", "Kevin  Smith", id="preserve-internal-whitespace"),
        pytest.param("k", "k", id="minimum-length-name"),
        pytest.param("K" * 255, "K" * 255, id="maximum-length-name"),
    ],
)
def test_valid_contact_names(schema, base_data, name, expected_name) -> None:
    contact = schema(**{**base_data, "name": name})

    assert contact.name == expected_name


# Blank, oversized, and non-text names must fail before reaching storage.
@pytest.mark.parametrize(
    "schema, base_data",
    [(ContactCreate, CREATE_CONTACT_DATA), (ContactUpdate, {})],
    ids=["create", "update"],
)
@pytest.mark.parametrize(
    "name, expected_error_type",
    [
        pytest.param("", "string_too_short", id="empty-name"),
        pytest.param(" \t\n ", "string_too_short", id="whitespace-only-name"),
        pytest.param("K" * 256, "string_too_long", id="name-exceeds-maximum-length"),
        pytest.param(123, "string_type", id="invalid-name-type"),
    ],
)
def test_invalid_contact_names(schema, base_data, name, expected_error_type) -> None:
    with pytest.raises(ValidationError) as excinfo:
        schema(**{**base_data, "name": name})

    assert any(
        error["loc"] == ("name",) and error["type"] == expected_error_type
        for error in excinfo.value.errors()
    )


# Phone, role, and email text must accept their full declared storage lengths.
@pytest.mark.parametrize(
    "schema, base_data",
    [(ContactCreate, CREATE_CONTACT_DATA), (ContactUpdate, {})],
    ids=["create", "update"],
)
@pytest.mark.parametrize(
    "field, maximum_length",
    [
        pytest.param("phone_number", 32, id="phone-number"),
        pytest.param("role", 255, id="role"),
        pytest.param("email", 255, id="email"),
    ],
)
def test_contact_text_fields_accept_maximum_length(
    schema, base_data, field, maximum_length
) -> None:
    contact = schema(**{**base_data, field: "x" * maximum_length})

    assert getattr(contact, field) == "x" * maximum_length


# Each optional detail must enforce its own type or length restriction.
@pytest.mark.parametrize(
    "schema, base_data",
    [(ContactCreate, CREATE_CONTACT_DATA), (ContactUpdate, {})],
    ids=["create", "update"],
)
@pytest.mark.parametrize(
    "field, invalid_value, expected_error_type",
    [
        pytest.param(
            "company_id", "invalid-uuid", "uuid_parsing", id="invalid-company"
        ),
        pytest.param("phone_number", 123, "string_type", id="invalid-phone-type"),
        pytest.param("phone_number", "x" * 33, "string_too_long", id="phone-too-long"),
        pytest.param("role", 123, "string_type", id="invalid-role-type"),
        pytest.param("role", "x" * 256, "string_too_long", id="role-too-long"),
        pytest.param("email", 123, "string_type", id="invalid-email-type"),
        pytest.param("email", "x" * 256, "string_too_long", id="email-too-long"),
        pytest.param("notes", ["Note"], "string_type", id="invalid-notes-type"),
    ],
)
def test_invalid_contact_details(
    schema, base_data, field, invalid_value, expected_error_type
) -> None:
    with pytest.raises(ValidationError) as excinfo:
        schema(**{**base_data, field: invalid_value})

    assert any(
        error["loc"] == (field,) and error["type"] == expected_error_type
        for error in excinfo.value.errors()
    )
