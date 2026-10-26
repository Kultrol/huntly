from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.enums import Priority, TrackedRoleStatus, TrackedRoleType
from app.schemas.tracked_role import (
    TrackedRoleCreate,
    TrackedRoleRead,
    TrackedRoleUpdate,
)
from tests.schemas.tracked_role.data import (
    COMPANY_ID,
    CREATE_DATA,
    READ_DATA,
    TIMESTAMP,
)


# Listing URLs require HTTP(S), a scheme, a host, and a supported input type.
@pytest.mark.parametrize(
    "schema,base_data",
    [(TrackedRoleCreate, CREATE_DATA), (TrackedRoleUpdate, {})],
    ids=["create", "update"],
)
@pytest.mark.parametrize(
    "invalid_url,error_type",
    [
        pytest.param("example.com", "url_parsing", id="missing-scheme"),
        pytest.param("ftp://example.com", "url_scheme", id="non-http-scheme"),
        pytest.param(2, "url_type", id="invalid-type"),
        pytest.param("https://", "url_parsing", id="missing-host"),
    ],
)
def test_tracked_role_input_rejects_invalid_url(
    schema, base_data, invalid_url, error_type
) -> None:
    with pytest.raises(ValidationError) as excinfo:
        schema(**{**base_data, "listing_url": invalid_url})

    assert any(
        error["loc"] == ("listing_url",) and error["type"] == error_type
        for error in excinfo.value.errors()
    )


# Listing URLs become normalized strings while null continues to mean no listing.
@pytest.mark.parametrize(
    "schema,base_data",
    [(TrackedRoleCreate, CREATE_DATA), (TrackedRoleUpdate, {})],
    ids=["create", "update"],
)
@pytest.mark.parametrize(
    "url,expected",
    [
        pytest.param("http://example.com", "http://example.com/", id="http"),
        pytest.param(
            "https://EXAMPLE.COM/jobs/backend",
            "https://example.com/jobs/backend",
            id="https-normalized-host",
        ),
        pytest.param(None, None, id="null"),
    ],
)
def test_tracked_role_input_normalizes_url_to_text(
    schema, base_data, url, expected
) -> None:
    role = schema(**{**base_data, "listing_url": url})

    assert role.listing_url == expected
    if expected is not None:
        assert isinstance(role.listing_url, str)


# Write schemas enforce meaningful titles, valid detail types, and nonnegative salaries.
@pytest.mark.parametrize(
    "schema,base_data",
    [(TrackedRoleCreate, CREATE_DATA), (TrackedRoleUpdate, {})],
    ids=["create", "update"],
)
@pytest.mark.parametrize(
    "field,value,error_type",
    [
        pytest.param("company_id", "bad-uuid", "uuid_parsing", id="invalid-company"),
        pytest.param("title", 123, "string_type", id="invalid-title-type"),
        pytest.param("title", "", "string_too_short", id="empty-title"),
        pytest.param("title", " \t\n ", "string_too_short", id="blank-title"),
        pytest.param("description", [], "string_type", id="invalid-description"),
        pytest.param("location", [], "string_type", id="invalid-location"),
        pytest.param("source", 123, "string_type", id="invalid-source"),
        pytest.param("notes", 123, "string_type", id="invalid-notes"),
        pytest.param("salary_currency", [], "string_type", id="invalid-currency"),
        pytest.param("applied_at", [], "datetime_type", id="invalid-applied-time"),
        pytest.param(
            "salary_min", "salary", "decimal_parsing", id="invalid-min-salary"
        ),
        pytest.param(
            "salary_max", "salary", "decimal_parsing", id="invalid-max-salary"
        ),
        pytest.param(
            "salary_min", "-0.01", "greater_than_equal", id="negative-min-salary"
        ),
        pytest.param(
            "salary_max", "-0.01", "greater_than_equal", id="negative-max-salary"
        ),
    ],
)
def test_invalid_tracked_role_input_fields(
    schema, base_data, field, value, error_type
) -> None:
    with pytest.raises(ValidationError) as excinfo:
        schema(**{**base_data, field: value})

    assert any(
        error["loc"] == (field,) and error["type"] == error_type
        for error in excinfo.value.errors()
    )


# Request text must become typed IDs, enums, decimal amounts, and application times.
@pytest.mark.parametrize(
    "schema,base_data",
    [(TrackedRoleCreate, CREATE_DATA), (TrackedRoleUpdate, {})],
    ids=["create", "update"],
)
def test_tracked_role_input_parses_field_values(schema, base_data) -> None:
    role = schema(
        **{
            **base_data,
            "company_id": str(COMPANY_ID),
            "title": "  Backend Developer \t",
            "status": "applied",
            "role_type": "full_time",
            "priority": "high",
            "salary_min": "0",
            "salary_max": "100000.25",
            "applied_at": "2026-10-12T14:30:00Z",
        }
    )

    assert role.company_id == COMPANY_ID
    assert role.title == "Backend Developer"
    assert role.status is TrackedRoleStatus.APPLIED
    assert role.role_type is TrackedRoleType.FULL_TIME
    assert role.priority is Priority.HIGH
    assert role.salary_min == Decimal(0)
    assert isinstance(role.salary_min, Decimal)
    assert role.salary_max == Decimal("100000.25")
    assert isinstance(role.salary_max, Decimal)
    assert role.applied_at == TIMESTAMP


# Every schema must reject lifecycle, employment, and priority values outside its enum.
@pytest.mark.parametrize(
    "schema,base_data",
    [
        (TrackedRoleRead, READ_DATA),
        (TrackedRoleCreate, CREATE_DATA),
        (TrackedRoleUpdate, {}),
    ],
    ids=["read", "create", "update"],
)
@pytest.mark.parametrize("field", ["status", "role_type", "priority"])
def test_tracked_role_rejects_unknown_enum_values(schema, base_data, field) -> None:
    with pytest.raises(ValidationError) as excinfo:
        schema(**{**base_data, field: "unknown"})

    assert any(
        error["loc"] == (field,) and error["type"] == "enum"
        for error in excinfo.value.errors()
    )
