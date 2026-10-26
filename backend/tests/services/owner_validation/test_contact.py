from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Contact, User
from app.schemas.contact import ContactCreate
from app.services.contact import ContactService
from app.services.exceptions.user import UserFetchingError, UserNotFoundError
from app.services.user import UserService

pytestmark = pytest.mark.anyio


# Rejecting a missing contact owner must leave the session usable for a valid creation.
async def test_missing_contact_owner_create_leaves_session_usable_and_saves_no_failed_row(
    sessions, owner_ids
):
    existing_owner_id = owner_ids[0]
    missing_owner_id = uuid4()
    missing_owner_data = ContactCreate(user_id=missing_owner_id, name="Example contact")
    valid_owner_data = ContactCreate(user_id=existing_owner_id, name="Example contact")

    async with sessions() as session:
        service = ContactService(session)
        with pytest.raises(UserNotFoundError, match=str(missing_owner_id)):
            await service.create_contact(missing_owner_data)

        assert not session.new
        assert session.is_active
        new_record = await service.create_contact(valid_owner_data)
        await session.commit()

    async with sessions() as session:
        owner_records = list(
            await session.scalars(
                select(Contact).where(
                    Contact.user_id.in_((existing_owner_id, missing_owner_id))
                )
            )
        )
        assert len(owner_records) == 1
        assert owner_records[0].id == new_record.id
        assert owner_records[0].user_id == existing_owner_id

        listed_records = await ContactService(session).get_all_contacts(
            existing_owner_id
        )
        assert [record.id for record in listed_records] == [new_record.id]


# A missing contact owner must raise while an existing owner with no records returns
# an empty list.
async def test_missing_contact_owner_list_raises_and_leaves_session_usable(
    sessions, owner_ids
):
    missing_owner_id = uuid4()
    async with sessions() as session:
        service = ContactService(session)
        with pytest.raises(UserNotFoundError, match=str(missing_owner_id)):
            await service.get_all_contacts(missing_owner_id)

        assert session.is_active
        assert await service.get_all_contacts(owner_ids[0]) == []


# The contact owner must be checked before its optional company association.
async def test_missing_contact_owner_is_checked_before_company_association(sessions):
    missing_owner_id = uuid4()
    data = ContactCreate(
        user_id=missing_owner_id, company_id=uuid4(), name="Example contact"
    )
    async with sessions() as session:
        with pytest.raises(UserNotFoundError, match=str(missing_owner_id)):
            await ContactService(session).create_contact(data)

        assert not session.new
        assert session.is_active


# A failed contact owner lookup must retain its database cause and stop further work.
@pytest.mark.parametrize("operation", ["create", "list"])
async def test_contact_owner_lookup_database_error_preserves_cause(operation):
    user_id = uuid4()
    database_error = SQLAlchemyError("Owner lookup unavailable")
    session = AsyncMock(spec=AsyncSession)
    session.get.side_effect = database_error
    service = ContactService(session)

    with pytest.raises(UserFetchingError, match=str(user_id)) as exc_info:
        if operation == "create":
            await service.create_contact(
                ContactCreate(user_id=user_id, name="Example contact")
            )
        else:
            await service.get_all_contacts(user_id)

    assert exc_info.value.__cause__ is database_error
    session.get.assert_awaited_once_with(User, user_id)
    session.add.assert_not_called()
    session.flush.assert_not_awaited()
    session.scalar.assert_not_awaited()
    session.scalars.assert_not_awaited()


# Both contact routes must return 404 for an unknown owner without saving a row.
@pytest.mark.parametrize("method", ["GET", "POST"])
async def test_missing_contact_owner_route_returns_404_without_saving_rows(
    sessions, api_client, method
):
    missing_owner_id = uuid4()
    if method == "POST":
        response = await api_client.post(
            "/contacts/",
            json={"user_id": str(missing_owner_id), "name": "Example contact"},
        )
    else:
        response = await api_client.get(
            "/contacts/", params={"user_id": str(missing_owner_id)}
        )

    assert response.status_code == 404
    assert response.json() == {"detail": f"User with id {missing_owner_id} not found."}

    async with sessions() as session:
        failed_owner_records = list(
            await session.scalars(
                select(Contact).where(Contact.user_id == missing_owner_id)
            )
        )
        assert failed_owner_records == []


# Both contact routes must translate an owner lookup failure to HTTP 500.
@pytest.mark.parametrize("method", ["GET", "POST"])
async def test_contact_owner_lookup_failure_route_returns_500(
    api_client, owner_ids, method, monkeypatch
):
    existing_owner_id = owner_ids[0]
    lookup_failure = UserFetchingError(f"Failed to get user: {existing_owner_id}")
    get_user = AsyncMock(side_effect=lookup_failure)
    monkeypatch.setattr(UserService, "get_user", get_user)

    if method == "POST":
        response = await api_client.post(
            "/contacts/",
            json={"user_id": str(existing_owner_id), "name": "Example contact"},
        )
    else:
        response = await api_client.get(
            "/contacts/", params={"user_id": str(existing_owner_id)}
        )

    assert response.status_code == 500
    assert response.json() == {"detail": str(lookup_failure)}
    get_user.assert_awaited_once_with(existing_owner_id)
