from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID, uuid4

import pytest
from fastapi import Depends, Request
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_auth_context, session_cookie
from app.core.database import get_db
from app.core.security import digest_token, hash_password, verify_password
from app.main import app
from app.models import AuthSession, User

pytestmark = pytest.mark.anyio
PASSWORD = "A strong race test password 42!"
CHANGED_PASSWORD = "A previously changed password 55!"
ATTEMPTED_PASSWORD = "A later attempted password 99!"


@pytest.fixture
async def auth_account(anonymous_client, sessions):
    email = f"auth-race-{uuid4().hex}@example.com"
    response = await anonymous_client.post(
        "/auth/register",
        json={"name": "Race test owner", "email": email, "password": PASSWORD},
    )
    assert response.status_code == 201
    account = response.json()
    anonymous_client.headers["X-CSRF-Token"] = account["csrf_token"]
    user_id = UUID(account["user"]["id"])
    try:
        yield user_id
    finally:
        async with sessions.begin() as session:
            await session.execute(delete(User).where(User.id == user_id))


async def test_password_change_reads_current_hash_after_authentication(
    anonymous_client, sessions, auth_account, monkeypatch
):
    changed_hash = hash_password(CHANGED_PASSWORD)

    async def context_before_password_change(
        request: Request,
        db: Annotated[AsyncSession, Depends(get_db)],
        token: Annotated[str | None, Depends(session_cookie)],
    ):
        context = await get_auth_context(
            request, db, token, request.headers.get("x-csrf-token")
        )
        # Another request commits after authentication loaded the user, before
        # this request acquires its password-change lock.
        async with sessions.begin() as other_session:
            await other_session.execute(
                update(User)
                .where(User.id == auth_account)
                .values(password_hash=changed_hash)
            )
        return context

    monkeypatch.setitem(
        app.dependency_overrides, get_auth_context, context_before_password_change
    )
    response = await anonymous_client.patch(
        "/auth/password",
        json={"current_password": PASSWORD, "new_password": ATTEMPTED_PASSWORD},
    )

    assert response.status_code == 401
    async with sessions() as session:
        user = await session.get(User, auth_account)
        assert user.password_hash == changed_hash
        assert verify_password(CHANGED_PASSWORD, user.password_hash)
        assert not verify_password(ATTEMPTED_PASSWORD, user.password_hash)
        assert (
            await session.scalar(
                select(AuthSession.id).where(AuthSession.user_id == auth_account)
            )
            is not None
        )


@pytest.mark.parametrize("session_change", ["revoke", "expire"])
async def test_password_change_rechecks_session_after_authentication(
    anonymous_client, sessions, auth_account, monkeypatch, session_change
):
    async def context_before_session_change(
        request: Request,
        db: Annotated[AsyncSession, Depends(get_db)],
        token: Annotated[str | None, Depends(session_cookie)],
    ):
        context = await get_auth_context(
            request, db, token, request.headers.get("x-csrf-token")
        )
        async with sessions.begin() as other_session:
            if session_change == "revoke":
                await other_session.execute(
                    delete(AuthSession).where(
                        AuthSession.token_hash == digest_token(token)
                    )
                )
            else:
                await other_session.execute(
                    update(AuthSession)
                    .where(AuthSession.token_hash == digest_token(token))
                    .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
                )
        return context

    monkeypatch.setitem(
        app.dependency_overrides, get_auth_context, context_before_session_change
    )
    response = await anonymous_client.patch(
        "/auth/password",
        json={"current_password": PASSWORD, "new_password": ATTEMPTED_PASSWORD},
    )

    assert response.status_code == 401
    async with sessions() as session:
        user = await session.get(User, auth_account)
        assert verify_password(PASSWORD, user.password_hash)
        assert not verify_password(ATTEMPTED_PASSWORD, user.password_hash)
