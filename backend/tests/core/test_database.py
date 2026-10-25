from unittest.mock import AsyncMock

import pytest
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.exc import DetachedInstanceError

from app.core import database
from app.main import app
from app.models import Company, User

pytestmark = pytest.mark.anyio


# Finishing or failing a request closes its session and discards changes that were not
# committed.
@pytest.mark.parametrize("failed_request", [False, True])
async def test_get_db_closes_session_and_rolls_back_uncommitted_work(
    sessions, owner_ids, monkeypatch, failed_request
):
    session = database.SessionLocal(bind=sessions.kw["bind"])
    close = AsyncMock(wraps=session.close)
    monkeypatch.setattr(session, "close", close)
    monkeypatch.setattr(database, "SessionLocal", lambda: session)
    dependency = database.get_db()
    request_session = await anext(dependency)
    assert request_session is session
    company = Company(user_id=owner_ids[0], name="Uncommitted")
    request_session.add(company)
    await request_session.flush()
    company_id = company.id
    if failed_request:
        with pytest.raises(RuntimeError, match="request failed"):
            await dependency.athrow(RuntimeError("request failed"))
    else:
        with pytest.raises(StopAsyncIteration):
            await anext(dependency)
    close.assert_awaited_once()
    async with sessions() as other_session:
        assert await other_session.get(Company, company_id) is None


# Closing a request's session keeps changes that the caller already committed.
async def test_get_db_preserves_caller_commit(sessions, owner_ids, monkeypatch):
    production_session = database.SessionLocal(bind=sessions.kw["bind"])
    monkeypatch.setattr(database, "SessionLocal", lambda: production_session)
    dependency = database.get_db()
    session = await anext(dependency)
    async with session.begin():
        company = Company(user_id=owner_ids[0], name="Committed")
        session.add(company)
    await dependency.aclose()
    assert company.name == "Committed"
    async with sessions() as other_session:
        found = await other_session.get(Company, company.id)
        assert found is not None
        assert found.name == "Committed"


# The production session keeps saved fields readable after commit without loading related
# contacts.
async def test_commit_keeps_scalar_fields_but_does_not_load_relationships(
    sessions, saved_company
):
    async with database.SessionLocal(bind=sessions.kw["bind"]) as session:
        company = await session.get(Company, saved_company.id)
        assert company is not None
        await session.commit()
    assert company.name == "Amazon"
    with pytest.raises(DetachedInstanceError):
        _ = company.contacts


# Related companies remain readable after the production session closes when loaded explicitly.
async def test_explicitly_loaded_relationships_remain_available_after_close(
    sessions, owner_ids, saved_company
):
    async with database.SessionLocal(bind=sessions.kw["bind"]) as session:
        user = await session.scalar(
            select(User)
            .where(User.id == owner_ids[0])
            .options(selectinload(User.companies))
        )
    assert user is not None
    assert [company.id for company in user.companies] == [saved_company.id]


# A request using the production session can return updated user fields after committing them.
async def test_production_session_can_serialize_response_after_commit(
    sessions, owner_ids, monkeypatch
):
    production_factory = database.SessionLocal

    def create_session():
        return production_factory(bind=sessions.kw["bind"])

    monkeypatch.setattr(database, "SessionLocal", create_session)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.patch(f"/users/{owner_ids[0]}", json={"name": "Janet"})
    assert response.status_code == 200
    assert response.json() == {"id": str(owner_ids[0]), "name": "Janet"}
    async with sessions() as session:
        user = await session.get(User, owner_ids[0])
        assert user is not None
        assert user.name == "Janet"
