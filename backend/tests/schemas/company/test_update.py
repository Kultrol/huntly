import pytest
from pydantic import ValidationError

from app.schemas.company import CompanyUpdate


# A patch contains only supplied fields, with URL normalization already applied.
@pytest.mark.parametrize(
    "company_data, expected_update",
    [
        pytest.param(
            {
                "name": "Amazon",
                "website": "https://youtube.com",
                "linkedin_url": "https://linkedin.com",
                "location": "Miami, FL",
                "notes": "Some notes",
            },
            {
                "name": "Amazon",
                "website": "https://youtube.com/",
                "linkedin_url": "https://linkedin.com/",
                "location": "Miami, FL",
                "notes": "Some notes",
            },
            id="all-fields-populated",
        ),
        pytest.param(
            {
                "name": "Amazon",
                "website": "https://amazon.com",
                "location": "Miami, FL",
                "notes": "Some notes",
            },
            {
                "name": "Amazon",
                "website": "https://amazon.com/",
                "location": "Miami, FL",
                "notes": "Some notes",
            },
            id="linkedin-url-omitted",
        ),
        pytest.param({}, {}, id="all-fields-omitted"),
    ],
)
def test_valid_company_update(company_data, expected_update) -> None:
    company = CompanyUpdate(**company_data)

    assert company.model_dump(exclude_unset=True) == expected_update


# Omitting a detail preserves it; explicitly sending null requests clearing it.
@pytest.mark.parametrize("field", ["website", "linkedin_url", "location", "notes"])
def test_company_update_distinguishes_omission_from_explicit_null(field) -> None:
    omitted = CompanyUpdate()
    cleared = CompanyUpdate(**{field: None})

    assert omitted.model_dump(exclude_unset=True) == {}
    assert cleared.model_dump(exclude_unset=True) == {field: None}


# Optional patch input must not permit clearing the required company name.
def test_company_update_rejects_null_name() -> None:
    with pytest.raises(ValidationError) as excinfo:
        CompanyUpdate(name=None)

    assert any(
        error["loc"] == ("name",)
        and error["type"] == "value_error"
        and "Company name cannot be null." in error["msg"]
        for error in excinfo.value.errors()
    )
