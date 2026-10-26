import pytest
from pydantic import ValidationError

from app.schemas.contact import ContactUpdate
from tests.schemas.contact.data import (
    COMPANY_ID,
    NULL_DETAILS,
)


# A patch includes explicit clearing requests but leaves omitted details untouched.
@pytest.mark.parametrize(
    "contact_data",
    [
        pytest.param({}, id="all-fields-omitted"),
        pytest.param({"name": "Kevin"}, id="name-provided"),
        pytest.param({"company_id": COMPANY_ID}, id="company-provided"),
        pytest.param({"company_id": None}, id="clear-company"),
        pytest.param({"phone_number": None}, id="clear-phone-number"),
        pytest.param({"role": None}, id="clear-role"),
        pytest.param({"email": None}, id="clear-email"),
        pytest.param({"linkedin_url": None}, id="clear-linkedin-url"),
        pytest.param({"notes": None}, id="clear-notes"),
    ],
)
def test_contact_update_only_dumps_provided_fields(contact_data) -> None:
    contact = ContactUpdate(**contact_data)

    assert contact.model_dump(exclude_unset=True) == contact_data


# An empty patch has null internal defaults even though none are supplied fields.
def test_contact_update_optional_fields_default_to_none() -> None:
    contact = ContactUpdate()

    assert contact.model_dump() == {"name": None, **NULL_DETAILS}


# A patch can omit the name but cannot explicitly erase it.
def test_contact_update_rejects_null_name() -> None:
    with pytest.raises(ValidationError) as excinfo:
        ContactUpdate(name=None)

    assert any(
        error["loc"] == ("name",)
        and error["type"] == "value_error"
        and "Contact name cannot be null." in error["msg"]
        for error in excinfo.value.errors()
    )
