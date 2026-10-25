from datetime import datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.company import CompanyRead
from tests.schemas.company.data import (
    COMPANY_ID,
    CREATED_AT,
    READ_DATA,
    UPDATED_AT,
    USER_ID,
)


# Stored details are returned as recorded, including nullable values.
@pytest.mark.parametrize(
    "details",
    [
        pytest.param({}, id="nullable-fields-none"),
        pytest.param(
            {
                "website": "Some site",
                "linkedin_url": "Some Site",
                "location": "Some Location",
            },
            id="nullable-fields-populated",
        ),
    ],
)
def test_valid_company_read(details) -> None:
    company_data = {**READ_DATA, **details}

    company = CompanyRead(**company_data)

    assert company.model_dump() == company_data


# Nullable fields still belong in a complete persisted-company response.
@pytest.mark.parametrize("missing_field", list(READ_DATA))
def test_company_read_requires_declared_fields(missing_field) -> None:
    company_data = READ_DATA.copy()
    del company_data[missing_field]

    with pytest.raises(ValidationError) as excinfo:
        CompanyRead(**company_data)

    assert any(
        error["loc"] == (missing_field,) and error["type"] == "missing"
        for error in excinfo.value.errors()
    )


# Locations are display text rather than geographic coordinate pairs.
def test_company_read_rejects_invalid_location_type() -> None:
    with pytest.raises(ValidationError) as excinfo:
        CompanyRead(**{**READ_DATA, "location": (32.4, 88.2)})

    assert any(
        error["loc"] == ("location",) and error["type"] == "string_type"
        for error in excinfo.value.errors()
    )


# ORM-shaped objects must expose the same data with JSON-safe IDs and timestamps.
def test_company_read_from_attributes_and_json_serialization():
    company = CompanyRead.model_validate(SimpleNamespace(**READ_DATA))
    assert company.model_dump() == READ_DATA
    data = company.model_dump(mode="json")
    assert data["id"] == str(COMPANY_ID)
    assert data["user_id"] == str(USER_ID)
    assert datetime.fromisoformat(data["created_at"]) == CREATED_AT
    assert datetime.fromisoformat(data["updated_at"]) == UPDATED_AT
    assert data["normalized_name"] == "kevin"
