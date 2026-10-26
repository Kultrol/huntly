from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.tracked_role import (
    TrackedRoleCreate,
    TrackedRoleUpdate,
)
from tests.schemas.tracked_role.data import (
    CREATE_DATA,
)


# When both salary bounds are supplied, the minimum cannot exceed the maximum.
@pytest.mark.parametrize(
    "schema,base_data",
    [(TrackedRoleCreate, CREATE_DATA), (TrackedRoleUpdate, {})],
    ids=["create", "update"],
)
def test_tracked_role_input_rejects_inverted_salary_range(schema, base_data) -> None:
    with pytest.raises(ValidationError) as excinfo:
        schema(**{**base_data, "salary_min": 100, "salary_max": 0})

    assert any(
        error["loc"] == ()
        and error["type"] == "value_error"
        and error["msg"] == "Value error, Minimum salary cannot exceed maximum salary."
        for error in excinfo.value.errors()
    )


# Salary validation allows equal bounds, zero amounts, and either bound on its own.
@pytest.mark.parametrize(
    "schema,base_data",
    [(TrackedRoleCreate, CREATE_DATA), (TrackedRoleUpdate, {})],
    ids=["create", "update"],
)
@pytest.mark.parametrize(
    "salary_data,expected_min,expected_max",
    [
        pytest.param(
            {"salary_min": "100.00", "salary_max": "100.00"},
            Decimal("100.00"),
            Decimal("100.00"),
            id="equal-bounds",
        ),
        pytest.param(
            {"salary_min": 0, "salary_max": 0},
            Decimal(0),
            Decimal(0),
            id="zero-bounds",
        ),
        pytest.param(
            {"salary_min": "100.00"},
            Decimal("100.00"),
            None,
            id="minimum-only",
        ),
        pytest.param(
            {"salary_max": "100.00"},
            None,
            Decimal("100.00"),
            id="maximum-only",
        ),
    ],
)
def test_tracked_role_input_accepts_salary_range(
    schema, base_data, salary_data, expected_min, expected_max
) -> None:
    role = schema(**{**base_data, **salary_data})

    assert role.salary_min == expected_min
    assert role.salary_max == expected_max
