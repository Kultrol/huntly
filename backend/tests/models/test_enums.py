import pytest
from sqlalchemy import text
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError

from app.enums import (
    EventStatus,
    EventType,
    Priority,
    RelationshipType,
    TrackedRoleStatus,
    TrackedRoleType,
)
from app.models.enums import enum_type


# Enum columns store public string values and reject unknown strings before saving.
@pytest.mark.parametrize(
    "enum_class",
    [
        EventStatus,
        EventType,
        Priority,
        RelationshipType,
        TrackedRoleStatus,
        TrackedRoleType,
    ],
)
def test_enum_type_stores_values_and_rejects_unknown_strings(enum_class):
    column_type = enum_type(enum_class, "test_enum")
    assert column_type.enums == [member.value for member in enum_class]
    assert column_type.native_enum is False
    assert column_type.create_constraint is True
    processor = column_type.bind_processor(postgresql.dialect())
    assert processor is not None
    for member in enum_class:
        assert processor(member) == member.value
    assert processor(None) is None
    with pytest.raises(LookupError):
        processor("unknown")


# Database constraints reject invalid categories when direct SQL bypasses validators.
@pytest.mark.anyio
@pytest.mark.parametrize(
    "field, value",
    [
        ("status", "SAVED"),
        ("status", None),
        ("priority", "urgent"),
        ("role_type", "permanent"),
    ],
)
async def test_database_rejects_invalid_role_enums(sessions, saved_role, field, value):
    async with sessions() as session:
        with pytest.raises(IntegrityError):
            await session.execute(
                text(f"UPDATE tracked_roles SET {field} = :value WHERE id = :id"),
                {"value": value, "id": saved_role.id},
            )
        await session.rollback()
    async with sessions() as session:
        result = (
            await session.execute(
                text(
                    "SELECT status, priority, role_type FROM tracked_roles WHERE id = :id"
                ),
                {"id": saved_role.id},
            )
        ).one()
        assert result == ("saved", None, None)
