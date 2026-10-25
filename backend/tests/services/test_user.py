from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company, User
from app.schemas.user import UserCreate, UserUpdate
from app.services.exceptions.user import (
    UserCreationError,
    UserDeletionError,
    UserFetchingError,
    UserNotFoundError,
    UserUpdateError,
)
from app.services.user import UserService

pytestmark = pytest.mark.anyio


# User creation, renaming, and deletion must each survive a fresh database read.
async def test_user_crud_persistence(sessions):
    user_id = None
    try:
        async with sessions() as session:
            user = await UserService(session).create_user(
                UserCreate(name="  Jane Doe  ")
            )
            user_id = user.id
            await session.commit()
        async with sessions() as session:
            found = await UserService(session).get_user(user_id)
            assert found.name == "Jane Doe"
            await UserService(session).update_user(user_id, UserUpdate(name="Janet"))
            await session.commit()
        async with sessions() as session:
            found = await session.get(User, user_id)
            assert found is not None
            assert found.name == "Janet"
            await UserService(session).delete_user(user_id)
            await session.commit()
        async with sessions() as session:
            assert await session.get(User, user_id) is None
    finally:
        async with sessions.begin() as session:
            await session.execute(delete(User).where(User.id == user_id))


# User lists must sort names first and break equal-name ties by ID.
async def test_user_list_orders_name_then_id(sessions):
    ids = sorted([uuid4(), uuid4()])
    other_id = uuid4()
    test_ids = (*ids, other_id)
    try:
        async with sessions.begin() as session:
            session.add_all(
                [
                    User(id=ids[1], name="Jane"),
                    User(id=ids[0], name="Jane"),
                    User(id=other_id, name="Aaron"),
                ]
            )
        async with sessions() as session:
            users = await UserService(session).get_all_users()
            assert [user.id for user in users if user.id in test_ids] == [
                other_id,
                *ids,
            ]
    finally:
        async with sessions.begin() as session:
            await session.execute(delete(User).where(User.id.in_(test_ids)))


# An empty user patch must keep the saved name.
async def test_empty_user_patch_preserves_name(sessions, owner_ids):
    async with sessions() as session:
        await UserService(session).update_user(owner_ids[0], UserUpdate())
        await session.commit()
    async with sessions() as session:
        user = await session.get(User, owner_ids[0])
        assert user is not None
        assert user.name == "Example owner"


# Each operation on an unknown user must identify the missing user.
@pytest.mark.parametrize("operation", ["get", "update", "delete"])
async def test_missing_user_raises(sessions, operation):
    missing_id = uuid4()
    async with sessions() as session:
        service = UserService(session)
        with pytest.raises(UserNotFoundError, match=str(missing_id)):
            if operation == "get":
                await service.get_user(missing_id)
            elif operation == "update":
                await service.update_user(missing_id, UserUpdate(name="Jane"))
            else:
                await service.delete_user(missing_id)


# A user who still owns a company must remain after a rejected deletion.
async def test_user_with_company_cannot_be_deleted(sessions, owner_ids, saved_company):
    async with sessions() as session:
        with pytest.raises(UserDeletionError) as exc_info:
            await UserService(session).delete_user(owner_ids[0])
        assert exc_info.value.__cause__ is not None
        await session.rollback()
    async with sessions() as session:
        assert await session.get(User, owner_ids[0]) is not None
        assert await session.get(Company, saved_company.id) is not None


# Uncommitted user changes must stay invisible to other sessions and disappear on close.
@pytest.mark.parametrize("operation", ["create", "update", "delete"])
async def test_user_uncommitted_changes_are_rolled_back_on_close(
    sessions, owner_ids, operation
):
    user_id = owner_ids[0]
    async with sessions() as session:
        service = UserService(session)
        if operation == "create":
            user = await service.create_user(UserCreate(name="Unsaved"))
            user_id = user.id
        elif operation == "update":
            await service.update_user(owner_ids[0], UserUpdate(name="Unsaved"))
        else:
            await service.delete_user(owner_ids[0])
        async with sessions() as other_session:
            found = await other_session.get(User, user_id)
            if operation == "create":
                assert found is None
            else:
                assert found is not None
                assert found.name == "Example owner"
    async with sessions() as session:
        if operation == "create":
            assert await session.get(User, user_id) is None
        else:
            found = await session.get(User, owner_ids[0])
            assert found is not None
            assert found.name == "Example owner"


# User database failures must keep their cause and leave transaction control to the
# caller.
@pytest.mark.parametrize(
    "operation, failed_method, expected_error",
    [
        ("get", "get", UserFetchingError),
        ("list", "scalars", UserFetchingError),
        ("create", "flush", UserCreationError),
        ("update", "flush", UserUpdateError),
        ("delete", "flush", UserDeletionError),
    ],
)
async def test_user_database_failures_preserve_operation_and_cause(
    operation, failed_method, expected_error
):
    record_id = uuid4()
    record = User(id=record_id, name="Jane")
    session = AsyncMock(spec=AsyncSession)
    session.get.return_value = record
    database_error = SQLAlchemyError("Database unavailable")
    getattr(session, failed_method).side_effect = database_error
    service = UserService(session)
    with pytest.raises(expected_error) as exc_info:
        if operation == "get":
            await service.get_user(record_id)
        elif operation == "list":
            await service.get_all_users()
        elif operation == "create":
            await service.create_user(UserCreate(name="Jane"))
        elif operation == "update":
            await service.update_user(record_id, UserUpdate(name="Janet"))
        else:
            await service.delete_user(record_id)
    assert exc_info.value.__cause__ is database_error
    session.commit.assert_not_awaited()
    session.rollback.assert_not_awaited()


# Unexpected coding errors must escape without becoming user service errors.
async def test_user_service_does_not_wrap_programming_errors():
    session = AsyncMock(spec=AsyncSession)
    session.get.side_effect = TypeError("Unexpected programming error")
    with pytest.raises(TypeError, match="Unexpected programming error"):
        await UserService(session).get_user(uuid4())
