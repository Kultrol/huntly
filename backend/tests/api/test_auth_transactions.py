from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, event, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AuthSession, User

pytestmark = pytest.mark.anyio
PASSWORD = "A strong transaction test password 42!"


def reject_commit(session):
    """Fail after the handler's work but before any success cookie can be issued."""
    raise RuntimeError("Simulated commit failure")


def reject_session_insert(session, flush_context, instances):
    """Reject only new login rows, leaving existing account/session setup usable."""
    if any(isinstance(record, AuthSession) for record in session.new):
        raise RuntimeError("Simulated session insertion failure")


@pytest.fixture
async def transaction_account(client_factory, sessions):
    async with client_factory(raise_app_exceptions=False) as client:
        email = f"auth-transaction-{uuid4().hex}@example.com"
        response = await client.post(
            "/auth/register",
            json={"name": "Transaction owner", "email": email, "password": PASSWORD},
        )
        assert response.status_code == 201
        user_id = UUID(response.json()["user"]["id"])
        try:
            yield client, email, user_id
        finally:
            async with sessions.begin() as session:
                await session.execute(delete(User).where(User.id == user_id))


async def test_registration_commit_failure_rolls_back_user_and_session_without_cookie(
    client_factory, sessions
):
    email = f"failed-register-{uuid4().hex}@example.com"
    async with sessions() as session:
        sessions_before = set(await session.scalars(select(AuthSession.id)))
    async with client_factory(raise_app_exceptions=False) as client:
        # The hook affects all ORM sessions; remove it before persistence checks
        # and cleanup so the simulated failure stays inside this one request.
        event.listen(Session, "before_commit", reject_commit)
        try:
            response = await client.post(
                "/auth/register",
                json={"name": "Rejected", "email": email, "password": PASSWORD},
            )
        finally:
            event.remove(Session, "before_commit", reject_commit)
        assert response.status_code == 500
        assert "set-cookie" not in response.headers
        assert client.cookies.get(settings.session_cookie_name) is None
    async with sessions() as session:
        assert await session.scalar(select(User.id).where(User.email == email)) is None
        assert set(await session.scalars(select(AuthSession.id))) == sessions_before


@pytest.mark.parametrize("failure", ["insert", "commit"])
async def test_failed_login_preserves_previous_session_and_cookie(
    transaction_account, sessions, failure
):
    client, email, user_id = transaction_account
    previous_cookie = client.cookies.get(settings.session_cookie_name)
    query = select(
        AuthSession.id,
        AuthSession.token_hash,
        AuthSession.csrf_token_hash,
        AuthSession.created_at,
        AuthSession.expires_at,
    ).where(AuthSession.user_id == user_id)
    async with sessions() as session:
        sessions_before = (await session.execute(query)).all()
    event_name, handler = (
        ("before_flush", reject_session_insert)
        if failure == "insert"
        else ("before_commit", reject_commit)
    )
    event.listen(Session, event_name, handler)
    try:
        response = await client.post(
            "/auth/login", json={"email": email, "password": PASSWORD}
        )
    finally:
        event.remove(Session, event_name, handler)
    assert response.status_code == 500
    assert "set-cookie" not in response.headers
    assert client.cookies.get(settings.session_cookie_name) == previous_cookie
    async with sessions() as session:
        assert (await session.execute(query)).all() == sessions_before
        assert (await session.get(User, user_id)).email == email
    response = await client.get("/auth/me")
    assert response.status_code == 200
    assert response.json()["user"]["id"] == str(user_id)
