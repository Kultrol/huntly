import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.enums import Priority, TrackedRoleStatus, TrackedRoleType
from app.models import TrackedRole


# Opportunities normalize titles and convert initial category strings into enums.
def test_role_normalizes_title_and_coerces_initial_enum_values():
    role = TrackedRole(
        title="  Backend   Developer ",
        status="saved",
        priority="high",
        role_type="full_time",
    )
    assert role.title == "Backend Developer"
    assert role.status is TrackedRoleStatus.SAVED
    assert role.priority is Priority.HIGH
    assert role.role_type is TrackedRoleType.FULL_TIME
    role.title = "  Software Engineer "
    assert role.title == "Software Engineer"
    role.priority = None
    role.role_type = None
    assert role.priority is None
    assert role.role_type is None


# Opportunity titles must be strings containing meaningful text.
@pytest.mark.parametrize(
    "title, error",
    [(None, TypeError), (10, TypeError), ("", ValueError), (" \t", ValueError)],
)
def test_role_rejects_invalid_title(title, error):
    with pytest.raises(error):
        TrackedRole(title=title)


# Invalid categories cannot replace an opportunity status or optional classification.
@pytest.mark.parametrize(
    "field, value",
    [
        ("status", None),
        ("status", "unknown"),
        ("priority", "urgent"),
        ("role_type", "permanent"),
    ],
)
def test_role_rejects_invalid_enum_assignment(field, value):
    role = TrackedRole(title="Developer", status="saved")
    with pytest.raises(ValueError):
        setattr(role, field, value)


# Direct database writes cannot save negative salaries or a minimum above the maximum.
@pytest.mark.anyio
@pytest.mark.parametrize("salary_min, salary_max", [(-1, 100), (None, -1), (200, 100)])
async def test_database_rejects_invalid_salary_ranges(
    sessions, saved_role, salary_min, salary_max
):
    async with sessions() as session:
        with pytest.raises(IntegrityError):
            await session.execute(
                text(
                    "UPDATE tracked_roles SET salary_min = :minimum, salary_max = :maximum WHERE id = :id"
                ),
                {"minimum": salary_min, "maximum": salary_max, "id": saved_role.id},
            )
        await session.rollback()
    async with sessions() as session:
        found = await session.get(TrackedRole, saved_role.id)
        assert found is not None
        assert found.salary_min == 80000
        assert found.salary_max == 100000


# The database rejects a blank opportunity title even when ORM validation is bypassed.
@pytest.mark.anyio
async def test_database_rejects_blank_title_even_when_bypassing_orm(
    sessions, saved_role
):
    async with sessions() as session:
        with pytest.raises(IntegrityError):
            await session.execute(
                text("UPDATE tracked_roles SET title = ' ' WHERE id = :id"),
                {"id": saved_role.id},
            )
        await session.rollback()
