"""Test company schema fields, URL validation, and partial updates."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate

COMPANY_ID = UUID("11111111-1111-4111-8111-111111111111")
USER_ID = UUID("22222222-2222-4222-8222-222222222222")
CREATED_AT = datetime(2026, 10, 12, 12, tzinfo=UTC)
UPDATED_AT = datetime(2026, 10, 12, 13, tzinfo=UTC)
CREATE_DATA = {"user_id": USER_ID, "name": "Kevin"}
NULL_DETAILS = {
    "website": None,
    "linkedin_url": None,
    "location": None,
    "notes": None,
}
READ_DATA = {
    "id": COMPANY_ID,
    **CREATE_DATA,
    "normalized_name": "kevin",
    **NULL_DETAILS,
    "created_at": CREATED_AT,
    "updated_at": UPDATED_AT,
}


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


@pytest.mark.parametrize("missing_field", ["name", "website"])
def test_company_read_requires_declared_fields(missing_field) -> None:
    company_data = READ_DATA.copy()
    del company_data[missing_field]

    with pytest.raises(ValidationError) as excinfo:
        CompanyRead(**company_data)

    assert any(
        error["loc"] == (missing_field,) and error["type"] == "missing"
        for error in excinfo.value.errors()
    )


def test_company_read_rejects_invalid_location_type() -> None:
    with pytest.raises(ValidationError) as excinfo:
        CompanyRead(**{**READ_DATA, "location": (32.4, 88.2)})

    assert any(
        error["loc"] == ("location",) and error["type"] == "string_type"
        for error in excinfo.value.errors()
    )


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


def test_company_create_rejects_invalid_owner_type() -> None:
    with pytest.raises(ValidationError) as excinfo:
        CompanyCreate(**{**CREATE_DATA, "user_id": 1234})

    assert any(
        error["loc"] == ("user_id",) and error["type"] == "uuid_type"
        for error in excinfo.value.errors()
    )


@pytest.mark.parametrize(
    "schema, base_data",
    [(CompanyCreate, CREATE_DATA), (CompanyUpdate, {})],
    ids=["create", "update"],
)
def test_company_rejects_invalid_name_type(schema, base_data) -> None:
    with pytest.raises(ValidationError) as excinfo:
        schema(**{**base_data, "name": 2})

    assert any(
        error["loc"] == ("name",) and error["type"] == "string_type"
        for error in excinfo.value.errors()
    )


@pytest.mark.parametrize(
    "schema, base_data",
    [(CompanyCreate, CREATE_DATA), (CompanyUpdate, {})],
    ids=["create", "update"],
)
@pytest.mark.parametrize("field", ["website", "linkedin_url"])
@pytest.mark.parametrize(
    "url, expected_error_type",
    [
        pytest.param("something", "url_parsing", id="plain-text"),
        pytest.param(
            "docs.python.org/3/library/unittest.mock.html",
            "url_parsing",
            id="path-without-scheme",
        ),
        pytest.param("youtube.com", "url_parsing", id="missing-scheme"),
        pytest.param("www.example.com", "url_parsing", id="www-without-scheme"),
        pytest.param(2, "url_type", id="invalid-type"),
        pytest.param("https://", "url_parsing", id="missing-host"),
    ],
)
def test_company_rejects_invalid_url(
    schema, base_data, field, url, expected_error_type
) -> None:
    with pytest.raises(ValidationError) as excinfo:
        schema(**{**base_data, field: url})

    assert any(
        error["loc"] == (field,) and error["type"] == expected_error_type
        for error in excinfo.value.errors()
    )


@pytest.mark.parametrize(
    "schema, base_data",
    [(CompanyCreate, CREATE_DATA), (CompanyUpdate, {})],
    ids=["create", "update"],
)
@pytest.mark.parametrize("field", ["website", "linkedin_url"])
@pytest.mark.parametrize(
    "url, expected_url",
    [
        pytest.param(
            "https://docs.python.org/3/library/unittest.mock.html",
            "https://docs.python.org/3/library/unittest.mock.html",
            id="url-with-path",
        ),
        pytest.param(
            "https://youtube.com", "https://youtube.com/", id="normalized-url"
        ),
        pytest.param(None, None, id="null-url"),
    ],
)
def test_company_normalizes_url(schema, base_data, field, url, expected_url) -> None:
    company = schema(**{**base_data, field: url})

    assert getattr(company, field) == expected_url
    if expected_url is not None:
        assert isinstance(getattr(company, field), str)


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


@pytest.mark.parametrize("field", ["website", "linkedin_url", "location", "notes"])
def test_company_update_distinguishes_omission_from_explicit_null(field) -> None:
    omitted = CompanyUpdate()
    cleared = CompanyUpdate(**{field: None})

    assert omitted.model_dump(exclude_unset=True) == {}
    assert cleared.model_dump(exclude_unset=True) == {field: None}


def test_company_update_rejects_null_name() -> None:
    with pytest.raises(ValidationError) as excinfo:
        CompanyUpdate(name=None)

    assert any(
        error["loc"] == ("name",)
        and error["type"] == "value_error"
        and "Company name cannot be null." in error["msg"]
        for error in excinfo.value.errors()
    )
