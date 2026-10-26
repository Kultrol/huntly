import pytest
from pydantic import ValidationError

from app.schemas.contact import ContactCreate, ContactUpdate
from tests.schemas.contact.data import (
    CREATE_CONTACT_DATA,
)


# The normalized profile URL must fit within the 255-character storage limit.
@pytest.mark.parametrize(
    "schema, base_data",
    [(ContactCreate, CREATE_CONTACT_DATA), (ContactUpdate, {})],
    ids=["create", "update"],
)
@pytest.mark.parametrize(
    "url_length, expected_error_type",
    [
        pytest.param(255, None, id="maximum-length-url"),
        pytest.param(256, "string_too_long", id="url-exceeds-maximum-length"),
    ],
)
def test_contact_linkedin_url_length_limit(
    schema, base_data, url_length, expected_error_type
) -> None:
    url_prefix = "https://example.com/"
    url = url_prefix + "x" * (url_length - len(url_prefix))
    contact_data = {**base_data, "linkedin_url": url}

    if expected_error_type is None:
        contact = schema(**contact_data)
        assert contact.linkedin_url is not None
        assert len(contact.linkedin_url) == url_length
    else:
        with pytest.raises(ValidationError) as excinfo:
            schema(**contact_data)

        assert any(
            error["loc"] == ("linkedin_url",) and error["type"] == expected_error_type
            for error in excinfo.value.errors()
        )


# Profile URLs require HTTP(S), a scheme, a host, and a supported input type.
@pytest.mark.parametrize(
    "schema, base_data",
    [(ContactCreate, CREATE_CONTACT_DATA), (ContactUpdate, {})],
    ids=["create", "update"],
)
@pytest.mark.parametrize(
    "url, expected_error_type",
    [
        pytest.param("example.com", "url_parsing", id="missing-scheme"),
        pytest.param("ftp://example.com", "url_scheme", id="non-http-scheme"),
        pytest.param(2, "url_type", id="invalid-type"),
        pytest.param("https://", "url_parsing", id="missing-host"),
    ],
)
def test_contact_rejects_invalid_url(
    schema, base_data, url, expected_error_type
) -> None:
    with pytest.raises(ValidationError) as excinfo:
        schema(**{**base_data, "linkedin_url": url})

    assert any(
        error["loc"] == ("linkedin_url",) and error["type"] == expected_error_type
        for error in excinfo.value.errors()
    )


# A profile URL becomes normalized text while an explicit null remains null.
@pytest.mark.parametrize(
    "schema, base_data",
    [(ContactCreate, CREATE_CONTACT_DATA), (ContactUpdate, {})],
    ids=["create", "update"],
)
@pytest.mark.parametrize(
    "url, expected_url",
    [
        pytest.param(
            "https://youtube.com", "https://youtube.com/", id="normalized-url"
        ),
        pytest.param(None, None, id="null-url"),
    ],
)
def test_contact_normalizes_url(schema, base_data, url, expected_url) -> None:
    contact = schema(**{**base_data, "linkedin_url": url})

    assert contact.linkedin_url == expected_url
    if expected_url is not None:
        assert isinstance(contact.linkedin_url, str)
