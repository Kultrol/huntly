from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import csrf_token_for_session, digest_token
from app.models import AuthSession

pytestmark = pytest.mark.anyio


async def test_expired_logout_without_csrf_deletes_session_and_clears_cookie(
    client_factory, sessions, owner_ids
):
    async with client_factory(owner_ids[0]) as client:
        token = client.cookies.get(settings.session_cookie_name)
        client.headers.pop("X-CSRF-Token")
        async with sessions.begin() as session:
            saved_session = await session.scalar(
                select(AuthSession).where(AuthSession.token_hash == digest_token(token))
            )
            session_id = saved_session.id
            saved_session.expires_at = datetime.now(UTC) - timedelta(seconds=1)

        response = await client.post("/auth/logout")

        assert response.status_code == 204
        assert response.content == b""
        cookie = response.headers["set-cookie"].lower()
        assert cookie.startswith(f'{settings.session_cookie_name}="";')
        assert "max-age=0" in cookie
        assert "path=/" in cookie
        async with sessions() as session:
            assert await session.get(AuthSession, session_id) is None
        assert (await client.get("/auth/me")).status_code == 401


async def test_active_logout_without_csrf_preserves_session_and_cookie(
    client_factory, sessions, owner_ids
):
    async with client_factory(owner_ids[0]) as client:
        token = client.cookies.get(settings.session_cookie_name)
        client.headers.pop("X-CSRF-Token")
        async with sessions() as session:
            saved_session = await session.scalar(
                select(AuthSession).where(AuthSession.token_hash == digest_token(token))
            )
            session_id = saved_session.id
            previous_expiry = saved_session.expires_at

        response = await client.post("/auth/logout")

        assert response.status_code == 403
        assert "set-cookie" not in response.headers
        assert client.cookies.get(settings.session_cookie_name) == token
        async with sessions() as session:
            saved_session = await session.get(AuthSession, session_id)
            assert saved_session is not None
            assert saved_session.token_hash == digest_token(token)
            assert saved_session.expires_at == previous_expiry
        assert (await client.get("/auth/me")).status_code == 200


async def test_session_list_excludes_expired_sessions_and_orders_by_created_time_and_id(
    client_factory, sessions, owner_ids
):
    async with client_factory(owner_ids[0]) as client:
        token = client.cookies.get(settings.session_cookie_name)
        now = datetime.now(UTC)
        first_id, second_id = sorted([uuid4(), uuid4()])
        expired_id = uuid4()
        async with sessions.begin() as session:
            current_id = await session.scalar(
                select(AuthSession.id).where(
                    AuthSession.token_hash == digest_token(token)
                )
            )
            for session_id, created_at, expires_at in [
                (second_id, now - timedelta(hours=2), now + timedelta(hours=1)),
                (expired_id, now - timedelta(hours=3), now - timedelta(seconds=1)),
                (first_id, now - timedelta(hours=2), now + timedelta(hours=1)),
            ]:
                other_token = uuid4().hex
                session.add(
                    AuthSession(
                        id=session_id,
                        user_id=owner_ids[0],
                        token_hash=digest_token(other_token),
                        csrf_token_hash=digest_token(
                            csrf_token_for_session(other_token)
                        ),
                        created_at=created_at,
                        expires_at=expires_at,
                    )
                )

        response = await client.get("/auth/sessions")

        assert response.status_code == 200
        data = response.json()
        assert [item["id"] for item in data] == [
            str(first_id),
            str(second_id),
            str(current_id),
        ]
        assert [item["current"] for item in data] == [False, False, True]


async def test_revoking_another_own_device_preserves_current_login(
    client_factory, sessions, owner_ids
):
    async with (
        client_factory(owner_ids[0]) as current_device,
        client_factory(owner_ids[0]) as other_device,
    ):
        current_cookie = current_device.cookies.get(settings.session_cookie_name)
        listed = await other_device.get("/auth/sessions")
        other_id = next(item["id"] for item in listed.json() if item["current"])

        response = await current_device.delete(f"/auth/sessions/{other_id}")

        assert response.status_code == 204
        assert response.content == b""
        assert "set-cookie" not in response.headers
        assert (
            current_device.cookies.get(settings.session_cookie_name) == current_cookie
        )
        assert (await current_device.get("/auth/me")).status_code == 200
        assert (await other_device.get("/auth/me")).status_code == 401
        async with sessions() as session:
            current_session = await session.scalar(
                select(AuthSession).where(
                    AuthSession.token_hash == digest_token(current_cookie)
                )
            )
            assert await session.get(AuthSession, UUID(other_id)) is None
            assert current_session is not None
            assert str(current_session.id) != other_id
