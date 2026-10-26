from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    TrackedRole,
    User,
)
from app.schemas.tracked_role import TrackedRoleCreate, TrackedRoleUpdate
from app.services.exceptions.tracked_role import (
    TrackedRoleCreationError,
    TrackedRoleDeletionError,
    TrackedRoleFetchingError,
    TrackedRoleUpdateError,
)
from app.services.tracked_role import TrackedRoleService

pytestmark = pytest.mark.anyio


# Role database failures must keep their cause and leave transaction control to the
# caller.
@pytest.mark.parametrize(
    "operation, failed_method, expected_error",
    [
        ("get", "get", TrackedRoleFetchingError),
        ("list", "scalars", TrackedRoleFetchingError),
        ("create", "flush", TrackedRoleCreationError),
        ("update", "flush", TrackedRoleUpdateError),
        ("delete", "flush", TrackedRoleDeletionError),
        ("update", "refresh", TrackedRoleUpdateError),
    ],
)
async def test_tracked_role_database_failures_preserve_operation_and_cause(
    operation, failed_method, expected_error
):
    user_id = uuid4()
    record_id = uuid4()
    record = TrackedRole(
        id=record_id, user_id=user_id, title="Developer", status="saved"
    )
    session = AsyncMock(spec=AsyncSession)
    parent = User(id=user_id, name="Owner")
    session.get.side_effect = lambda model, id: parent if model is User else record
    database_error = SQLAlchemyError("Database unavailable")
    getattr(session, failed_method).side_effect = database_error
    service = TrackedRoleService(session)
    with pytest.raises(expected_error) as exc_info:
        if operation == "get":
            await service.get_tracked_role_by_id(record_id)
        elif operation == "list":
            await service.get_all_tracked_roles(user_id)
        elif operation == "create":
            await service.create_tracked_role(
                TrackedRoleCreate.model_validate(
                    {"user_id": user_id, "title": "Developer", "status": "saved"}
                )
            )
        elif operation == "update":
            await service.update_tracked_role(
                record_id, TrackedRoleUpdate(title="Engineer")
            )
        else:
            await service.delete_tracked_role(record_id)
    assert exc_info.value.__cause__ is database_error
    session.commit.assert_not_awaited()
    session.rollback.assert_not_awaited()


# Unexpected coding errors must escape without becoming role service errors.
async def test_tracked_role_service_does_not_wrap_programming_errors():
    session = AsyncMock(spec=AsyncSession)
    session.get.side_effect = TypeError("Unexpected programming error")
    with pytest.raises(TypeError, match="Unexpected programming error"):
        await TrackedRoleService(session).get_tracked_role_by_id(uuid4())
