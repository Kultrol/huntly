from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.contact import ContactRead
from tests.schemas.contact.data import (
    COMPANY_ID,
    CONTACT_ID,
    POPULATED_DETAILS,
    READ_CONTACT_DATA,
    USER_ID,
)


# A stored contact can have unknown details or a fully populated profile.
@pytest.mark.parametrize(
    "contact_details",
    [
        pytest.param({}, id="nullable-fields-are-none"),
        pytest.param(POPULATED_DETAILS, id="nullable-fields-populated"),
    ],
)
def test_valid_contact_read(contact_details) -> None:
    contact_data = {**READ_CONTACT_DATA, **contact_details}

    contact = ContactRead(**contact_data)

    assert contact.model_dump() == contact_data


# Nullable details remain required keys in a complete persisted-contact response.
@pytest.mark.parametrize(
    "missing_field",
    [
        "id",
        "user_id",
        "company_id",
        "name",
        "phone_number",
        "role",
        "email",
        "linkedin_url",
        "notes",
        "created_at",
        "updated_at",
    ],
)
def test_contact_read_requires_all_fields(missing_field) -> None:
    contact_data = READ_CONTACT_DATA.copy()
    del contact_data[missing_field]

    with pytest.raises(ValidationError) as excinfo:
        ContactRead(**contact_data)

    assert any(
        error["loc"] == (missing_field,) and error["type"] == "missing"
        for error in excinfo.value.errors()
    )


# Response fields must retain their declared identifier, text, and timestamp types.
@pytest.mark.parametrize(
    "field, invalid_value, expected_error_type",
    [
        pytest.param("id", "invalid-uuid", "uuid_parsing", id="invalid-id"),
        pytest.param("user_id", 123, "uuid_type", id="invalid-owner-type"),
        pytest.param(
            "company_id", "invalid-uuid", "uuid_parsing", id="invalid-company-id"
        ),
        pytest.param("name", None, "string_type", id="null-name"),
        pytest.param("phone_number", 123, "string_type", id="invalid-phone-type"),
        pytest.param("role", ["Recruiter"], "string_type", id="invalid-role-type"),
        pytest.param("email", 123, "string_type", id="invalid-email-type"),
        pytest.param("linkedin_url", 123, "string_type", id="invalid-linkedin-type"),
        pytest.param("notes", ["Note"], "string_type", id="invalid-notes-type"),
        pytest.param("created_at", [], "datetime_type", id="invalid-created-at-type"),
        pytest.param("updated_at", {}, "datetime_type", id="invalid-updated-at-type"),
    ],
)
def test_invalid_contact_read(field, invalid_value, expected_error_type) -> None:
    contact_data = {**READ_CONTACT_DATA, field: invalid_value}

    with pytest.raises(ValidationError) as excinfo:
        ContactRead(**contact_data)

    assert any(
        error["loc"] == (field,) and error["type"] == expected_error_type
        for error in excinfo.value.errors()
    )


# ORM-shaped data must serialize to the public fields without exposing extra attributes.
def test_contact_read_from_attributes_and_json_serialization() -> None:
    contact_data = {**READ_CONTACT_DATA, "company_id": COMPANY_ID}
    saved_contact = SimpleNamespace(**contact_data, extra_attribute="not exposed")

    contact = ContactRead.model_validate(saved_contact)

    assert contact.model_dump() == contact_data
    assert contact.model_dump(mode="json") == {
        **READ_CONTACT_DATA,
        "id": str(CONTACT_ID),
        "user_id": str(USER_ID),
        "company_id": str(COMPANY_ID),
        "created_at": "2026-10-12T12:00:00Z",
        "updated_at": "2026-10-12T13:00:00Z",
    }
