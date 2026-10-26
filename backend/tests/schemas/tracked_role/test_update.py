import pytest
from pydantic import ValidationError

from app.enums import TrackedRoleStatus
from app.schemas.tracked_role import (
    TrackedRoleUpdate,
)
from tests.schemas.tracked_role.data import (
    POPULATED_DETAILS,
)


# An opportunity patch contains only the values the caller supplied.
@pytest.mark.parametrize(
    "role_data",
    [
        pytest.param({}, id="empty-update"),
        pytest.param({"title": "API Developer"}, id="title-only"),
        pytest.param(
            {
                "title": "API Developer",
                "status": TrackedRoleStatus.APPLIED,
                **POPULATED_DETAILS,
            },
            id="all-update-fields",
        ),
    ],
)
def test_valid_tracked_role_update(role_data) -> None:
    role = TrackedRoleUpdate(**role_data)

    assert role.model_dump(exclude_unset=True) == role_data


# An omitted detail stays outside the patch; an explicit null requests clearing it.
@pytest.mark.parametrize(
    "field",
    [
        "company_id",
        "description",
        "role_type",
        "location",
        "source",
        "listing_url",
        "priority",
        "notes",
        "salary_min",
        "salary_max",
        "salary_currency",
        "applied_at",
    ],
)
def test_tracked_role_update_distinguishes_omitted_and_cleared_details(field) -> None:
    omitted = TrackedRoleUpdate()
    cleared = TrackedRoleUpdate(**{field: None})

    assert omitted.model_dump(exclude_unset=True) == {}
    assert cleared.model_dump(exclude_unset=True) == {field: None}


# A patch can omit title and status but cannot explicitly erase either value.
@pytest.mark.parametrize("field", ["title", "status"])
def test_tracked_role_update_rejects_null_required_fields(field) -> None:
    with pytest.raises(ValidationError) as excinfo:
        TrackedRoleUpdate(**{field: None})

    assert any(
        error["loc"] == ()
        and error["type"] == "value_error"
        and error["msg"] == f"Value error, Tracked role {field} cannot be null."
        for error in excinfo.value.errors()
    )
