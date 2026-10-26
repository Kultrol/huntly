import pytest
from pydantic import ValidationError

from app.schemas.contact import ContactCreate
from tests.schemas.contact.data import (
    CREATE_CONTACT_DATA,
    NULL_DETAILS,
    POPULATED_DETAILS,
)


# New contacts support omitted, explicitly null, and populated optional details.
@pytest.mark.parametrize(
    "contact_details",
    [
        pytest.param({}, id="optional-fields-omitted"),
        pytest.param(NULL_DETAILS, id="optional-fields-explicitly-none"),
        pytest.param(POPULATED_DETAILS, id="optional-fields-populated"),
    ],
)
def test_valid_contact_create(contact_details) -> None:
    contact = ContactCreate(**CREATE_CONTACT_DATA, **contact_details)

    assert contact.model_dump() == {
        **CREATE_CONTACT_DATA,
        **NULL_DETAILS,
        **contact_details,
    }


# A contact cannot be created without its owner and display name.
@pytest.mark.parametrize("missing_field", ["user_id", "name"])
def test_contact_create_requires_owner_and_name(missing_field) -> None:
    contact_data = CREATE_CONTACT_DATA.copy()
    del contact_data[missing_field]

    with pytest.raises(ValidationError) as excinfo:
        ContactCreate(**contact_data)

    assert any(
        error["loc"] == (missing_field,) and error["type"] == "missing"
        for error in excinfo.value.errors()
    )


# Owner IDs must parse as UUIDs and reject unrelated input types.
@pytest.mark.parametrize(
    "user_id, expected_error_type",
    [
        pytest.param("invalid-uuid", "uuid_parsing", id="invalid-owner-uuid"),
        pytest.param(123, "uuid_type", id="invalid-owner-type"),
    ],
)
def test_contact_create_rejects_invalid_owner(user_id, expected_error_type) -> None:
    with pytest.raises(ValidationError) as excinfo:
        ContactCreate(user_id=user_id, name="Kevin")

    assert any(
        error["loc"] == ("user_id",) and error["type"] == expected_error_type
        for error in excinfo.value.errors()
    )
