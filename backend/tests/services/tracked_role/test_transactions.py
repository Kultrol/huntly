import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.enums import TrackedRoleStatus
from app.models import (
    StatusHistory,
    TrackedRole,
)
from app.schemas.tracked_role import TrackedRoleCreate, TrackedRoleUpdate
from app.services.exceptions.tracked_role import (
    TrackedRoleCreationError,
)
from app.services.tracked_role import TrackedRoleService

pytestmark = pytest.mark.anyio


# Caller rollback must restore the role and its status history together.
@pytest.mark.parametrize("operation", ["create", "update", "delete"])
async def test_role_rollback_preserves_role_and_history(
    sessions, owner_ids, saved_role, operation
):
    created_id = None
    async with sessions() as session:
        service = TrackedRoleService(session)
        if operation == "create":
            role = await service.create_tracked_role(
                TrackedRoleCreate(
                    user_id=owner_ids[0],
                    title="Unsaved",
                    status=TrackedRoleStatus.SAVED,
                )
            )
            created_id = role.id
        elif operation == "update":
            await service.update_tracked_role(
                saved_role.id, TrackedRoleUpdate(status=TrackedRoleStatus.APPLIED)
            )
        else:
            await service.delete_tracked_role(saved_role.id)
        await session.rollback()
    async with sessions() as session:
        found = await session.get(TrackedRole, saved_role.id)
        assert found is not None
        assert found.status == TrackedRoleStatus.SAVED
        history = list(
            await session.scalars(
                select(StatusHistory).where(
                    StatusHistory.tracked_role_id == saved_role.id
                )
            )
        )
        assert len(history) == 1
        if operation == "create":
            assert created_id is not None
            assert await session.get(TrackedRole, created_id) is None
            role_history = list(
                await session.scalars(
                    select(StatusHistory).where(
                        StatusHistory.tracked_role_id == created_id
                    )
                )
            )
            assert role_history == []


# Caller rollback after a history failure must remove the already flushed role.
async def test_tracked_role_history_failure_rolls_back_inserted_parent(
    sessions, owner_ids, monkeypatch
):
    async with sessions() as session:
        original_flush = session.flush
        inserted_ids = []
        database_error = SQLAlchemyError("History insert failed")

        async def fail_history_flush(*args, **kwargs):
            if any(isinstance(row, StatusHistory) for row in session.new):
                raise database_error
            await original_flush(*args, **kwargs)
            inserted_ids.extend(
                row.id
                for row in session.identity_map.values()
                if isinstance(row, TrackedRole)
            )

        monkeypatch.setattr(session, "flush", fail_history_flush)
        with pytest.raises(TrackedRoleCreationError) as exc_info:
            await TrackedRoleService(session).create_tracked_role(
                TrackedRoleCreate(
                    user_id=owner_ids[0],
                    title="Rejected",
                    status=TrackedRoleStatus.SAVED,
                )
            )
        assert exc_info.value.__cause__ is database_error
        assert len(inserted_ids) == 1
        await session.rollback()
    async with sessions() as session:
        assert await session.get(TrackedRole, inserted_ids[0]) is None
        role_history = list(
            await session.scalars(
                select(StatusHistory).where(
                    StatusHistory.tracked_role_id == inserted_ids[0]
                )
            )
        )
        assert role_history == []
