import pytest
from pydantic import ValidationError

from app.schemas.company import CompanyCreate, CompanyUpdate
from tests.schemas.company.data import (
    CREATE_DATA,
)


# Write schemas must reject numeric names instead of converting them to text.
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


# Both URL fields enforce HTTP(S), a scheme, a host, and the correct input type.
@pytest.mark.parametrize(
    "schema, base_data",
    [(CompanyCreate, CREATE_DATA), (CompanyUpdate, {})],
    ids=["create", "update"],
)
@pytest.mark.parametrize("field", ["website", "linkedin_url"])
@pytest.mark.parametrize(
    "url, expected_error_type",
    [
        pytest.param("example.com", "url_parsing", id="missing-scheme"),
        pytest.param("ftp://example.com", "url_scheme", id="non-http-scheme"),
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


# Validated URLs stay plain strings so they can be stored in text columns.
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


# Names lose surrounding whitespace while retaining internal spacing and valid lengths.
@pytest.mark.parametrize(
    "schema, base_data",
    [(CompanyCreate, CREATE_DATA), (CompanyUpdate, {})],
    ids=["create", "update"],
)
@pytest.mark.parametrize(
    "name, expected_name",
    [("  Acme   Labs  ", "Acme   Labs"), ("A", "A"), ("A" * 255, "A" * 255)],
)
def test_company_name_trimming_and_length_boundaries(
    schema, base_data, name, expected_name
):
    company = schema.model_validate({**base_data, "name": name})
    assert company.name == expected_name


# Name validation must reject blank text and values beyond the storage limit.
@pytest.mark.parametrize(
    "schema, base_data",
    [(CompanyCreate, CREATE_DATA), (CompanyUpdate, {})],
    ids=["create", "update"],
)
@pytest.mark.parametrize(
    "name, error_type",
    [
        ("", "string_too_short"),
        (" ", "string_too_short"),
        ("A" * 256, "string_too_long"),
    ],
)
def test_company_rejects_blank_and_oversized_name(schema, base_data, name, error_type):
    with pytest.raises(ValidationError) as exc_info:
        schema.model_validate({**base_data, "name": name})
    assert any(
        error["loc"] == ("name",) and error["type"] == error_type
        for error in exc_info.value.errors()
    )


# Optional text accepts the storage boundary and rejects the next character.
@pytest.mark.parametrize(
    "schema, base_data",
    [(CompanyCreate, CREATE_DATA), (CompanyUpdate, {})],
    ids=["create", "update"],
)
@pytest.mark.parametrize("field", ["website", "linkedin_url", "location"])
def test_company_optional_text_length_limits(schema, base_data, field):
    value = (
        "https://example.com/" + "a" * (255 - len("https://example.com/"))
        if field != "location"
        else "a" * 255
    )
    company = schema.model_validate({**base_data, field: value})
    assert getattr(company, field) == value
    with pytest.raises(ValidationError) as exc_info:
        schema.model_validate({**base_data, field: value + "a"})
    assert any(
        error["loc"] == (field,) and error["type"] == "string_too_long"
        for error in exc_info.value.errors()
    )
