import pytest
from pydantic import ValidationError

from app.schemas.company import CompanyCreate
from tests.schemas.company.data import (
    CREATE_DATA,
    NULL_DETAILS,
)


# Optional details can be omitted, cleared, or populated on a new company.
@pytest.mark.parametrize(
    "details",
    [
        pytest.param(NULL_DETAILS, id="optional-fields-null"),
        pytest.param(
            {**NULL_DETAILS, "website": "http://www.example.com/"},
            id="website-populated",
        ),
        pytest.param(
            {
                "website": "http://www.example.com/",
                "linkedin_url": "http://www.linkedin.com/",
                "location": "Some Location",
                "notes": "Some notes",
            },
            id="all-fields-populated",
        ),
        pytest.param({}, id="optional-fields-omitted"),
    ],
)
def test_valid_company_create(details) -> None:
    company = CompanyCreate(**CREATE_DATA, **details)

    assert company.model_dump() == {**CREATE_DATA, **NULL_DETAILS, **details}


# A new company needs both an owner and a display name.
@pytest.mark.parametrize("missing_field", ["user_id", "name"])
def test_company_create_requires_owner_and_name(missing_field) -> None:
    company_data = CREATE_DATA.copy()
    del company_data[missing_field]

    with pytest.raises(ValidationError) as excinfo:
        CompanyCreate(**company_data)

    assert any(
        error["loc"] == (missing_field,) and error["type"] == "missing"
        for error in excinfo.value.errors()
    )


# Ownership identifiers must be UUIDs rather than numeric values.
def test_company_create_rejects_invalid_owner_type() -> None:
    with pytest.raises(ValidationError) as excinfo:
        CompanyCreate(**{**CREATE_DATA, "user_id": 1234})

    assert any(
        error["loc"] == ("user_id",) and error["type"] == "uuid_type"
        for error in excinfo.value.errors()
    )
