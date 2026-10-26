from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import TrackedRoleStatus
from app.models import StatusHistory, TrackedRole, User
from app.schemas.tracked_role import TrackedRoleCreate
from app.services.exceptions.user import UserFetchingError, UserNotFoundError
from app.services.tracked_role import TrackedRoleService
from app.services.user import UserService

pytestmark = pytest.mark.anyio


# Rejecting a missing tracked role owner must leave the session usable for a valid
# creation.
async def test_missing_tracked_role_owner_create_leaves_session_usable_and_saves_no_failed_row(
    sessions, owner_ids
):
    existing_owner_id = owner_ids[0]
    missing_owner_id = uuid4()
    missing_owner_data = TrackedRoleCreate(
        user_id=missing_owner_id,
        title="Backend developer",
        status=TrackedRoleStatus.SAVED,
    )
    valid_owner_data = TrackedRoleCreate(
        user_id=existing_owner_id,
        title="Backend developer",
        status=TrackedRoleStatus.SAVED,
    )

    async with sessions() as session:
        service = TrackedRoleService(session)
        with pytest.raises(UserNotFoundError, match=str(missing_owner_id)):
            await service.create_tracked_role(missing_owner_data)

        assert not session.new
        assert session.is_active
        new_record = await service.create_tracked_role(valid_owner_data)
        await session.commit()

    async with sessions() as session:
        owner_records = list(
            await session.scalars(
                select(TrackedRole).where(
                    TrackedRole.user_id.in_((existing_owner_id, missing_owner_id))
                )
            )
        )
        assert len(owner_records) == 1
        assert owner_records[0].id == new_record.id
        assert owner_records[0].user_id == existing_owner_id

        listed_records = await TrackedRoleService(session).get_all_tracked_roles(
            existing_owner_id
        )
        assert [record.id for record in listed_records] == [new_record.id]

        history = list(
            await session.scalars(
                select(StatusHistory).where(
                    StatusHistory.tracked_role_id == new_record.id
                )
            )
        )
        assert len(history) == 1
        assert history[0].from_status is None
        assert history[0].to_status == TrackedRoleStatus.SAVED


# A missing tracked role owner must raise while an existing owner with no records
# returns an empty list.
async def test_missing_tracked_role_owner_list_raises_and_leaves_session_usable(
    sessions, owner_ids
):
    missing_owner_id = uuid4()
    async with sessions() as session:
        service = TrackedRoleService(session)
        with pytest.raises(UserNotFoundError, match=str(missing_owner_id)):
            await service.get_all_tracked_roles(missing_owner_id)

        assert session.is_active
        assert await service.get_all_tracked_roles(owner_ids[0]) == []


# The tracked role owner must be checked before its optional company association.
async def test_missing_tracked_role_owner_is_checked_before_company_association(
    sessions,
):
    missing_owner_id = uuid4()
    data = TrackedRoleCreate(
        user_id=missing_owner_id,
        company_id=uuid4(),
        title="Backend developer",
        status=TrackedRoleStatus.SAVED,
    )
    async with sessions() as session:
        with pytest.raises(UserNotFoundError, match=str(missing_owner_id)):
            await TrackedRoleService(session).create_tracked_role(data)

        assert not session.new
        assert session.is_active


# A failed tracked role owner lookup must retain its database cause and stop further
# work.
@pytest.mark.parametrize("operation", ["create", "list"])
async def test_tracked_role_owner_lookup_database_error_preserves_cause(operation):
    user_id = uuid4()
    database_error = SQLAlchemyError("Owner lookup unavailable")
    session = AsyncMock(spec=AsyncSession)
    session.get.side_effect = database_error
    service = TrackedRoleService(session)

    with pytest.raises(UserFetchingError, match=str(user_id)) as exc_info:
        if operation == "create":
            await service.create_tracked_role(
                TrackedRoleCreate(
                    user_id=user_id,
                    title="Backend developer",
                    status=TrackedRoleStatus.SAVED,
                )
            )
        else:
            await service.get_all_tracked_roles(user_id)

    assert exc_info.value.__cause__ is database_error
    session.get.assert_awaited_once_with(User, user_id)
    session.add.assert_not_called()
    session.flush.assert_not_awaited()
    session.scalar.assert_not_awaited()
    session.scalars.assert_not_awaited()


# Both tracked role routes must return 404 for an unknown owner without saving a row.
@pytest.mark.parametrize("method", ["GET", "POST"])
async def test_missing_tracked_role_owner_route_returns_404_without_saving_rows(
    sessions, api_client, method
):
    missing_owner_id = uuid4()
    if method == "POST":
        response = await api_client.post(
            "/tracked-roles/",
            json={
                "user_id": str(missing_owner_id),
                "title": "Backend developer",
                "status": "saved",
            },
        )
    else:
        response = await api_client.get(
            "/tracked-roles/", params={"user_id": str(missing_owner_id)}
        )

    assert response.status_code == 404
    assert response.json() == {"detail": f"User with id {missing_owner_id} not found."}

    async with sessions() as session:
        failed_owner_records = list(
            await session.scalars(
                select(TrackedRole).where(TrackedRole.user_id == missing_owner_id)
            )
        )
        assert failed_owner_records == []


# Both tracked role routes must translate an owner lookup failure to HTTP 500.
@pytest.mark.parametrize("method", ["GET", "POST"])
async def test_tracked_role_owner_lookup_failure_route_returns_500(
    api_client, owner_ids, method, monkeypatch
):
    existing_owner_id = owner_ids[0]
    lookup_failure = UserFetchingError(f"Failed to get user: {existing_owner_id}")
    get_user = AsyncMock(side_effect=lookup_failure)
    monkeypatch.setattr(UserService, "get_user", get_user)

    if method == "POST":
        response = await api_client.post(
            "/tracked-roles/",
            json={
                "user_id": str(existing_owner_id),
                "title": "Backend developer",
                "status": "saved",
            },
        )
    else:
        response = await api_client.get(
            "/tracked-roles/", params={"user_id": str(existing_owner_id)}
        )

    assert response.status_code == 500
    assert response.json() == {"detail": str(lookup_failure)}
    get_user.assert_awaited_once_with(existing_owner_id)
