from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select

from app.core.config import settings
from app.core.security import digest_token, verify_password
from app.models import AuthSession, User

pytestmark = pytest.mark.anyio
PASSWORD = "A strong test password 42!"


@pytest.fixture
async def auth_account(anonymous_client, sessions):
    email = f"auth-{uuid4().hex}@example.com"
    response = await anonymous_client.post(
        "/auth/register",
        json={"name": "  Jane Doe  ", "email": email, "password": PASSWORD},
    )
    assert response.status_code == 201
    data = response.json()
    anonymous_client.headers["X-CSRF-Token"] = data["csrf_token"]
    try:
        yield {**data, "email": email, "password": PASSWORD}
    finally:
        async with sessions.begin() as session:
            await session.execute(
                delete(User).where(User.id == UUID(data["user"]["id"]))
            )


async def test_registration_persists_hashed_credentials_and_session(
    anonymous_client, sessions, auth_account
):
    user_id = UUID(auth_account["user"]["id"])
    assert auth_account["user"] == {
        "id": str(user_id),
        "name": "Jane Doe",
        "email": auth_account["email"],
    }
    cookie = anonymous_client.cookies.get(settings.session_cookie_name)
    assert cookie
    async with sessions() as session:
        user = await session.get(User, user_id)
        assert user.password_hash != PASSWORD
        assert user.password_hash.startswith("$argon2id$")
        assert verify_password(PASSWORD, user.password_hash)
        auth_session = await session.scalar(
            select(AuthSession).where(AuthSession.user_id == user_id)
        )
        assert auth_session.token_hash == digest_token(cookie)
        assert auth_session.csrf_token_hash == digest_token(auth_account["csrf_token"])
        assert auth_session.expires_at > datetime.now(UTC)
        assert cookie not in auth_session.token_hash
    response = await anonymous_client.get("/auth/me")
    assert response.status_code == 200
    assert response.json() == {
        "user": auth_account["user"],
        "csrf_token": auth_account["csrf_token"],
    }
    assert "password" not in response.text
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("secure", [False, True])
async def test_registration_cookie_is_httponly_and_same_site(
    anonymous_client, sessions, monkeypatch, secure
):
    monkeypatch.setattr(settings, "session_cookie_secure", secure)
    email = f"auth-{uuid4().hex}@example.com"
    try:
        response = await anonymous_client.post(
            "/auth/register",
            json={"name": "Jane", "email": email, "password": PASSWORD},
        )
        assert response.status_code == 201
        cookie = response.headers["set-cookie"].lower()
        assert "httponly" in cookie
        assert "samesite=lax" in cookie
        assert "path=/" in cookie
        assert "max-age=" in cookie
        assert ("; secure" in cookie) is settings.session_cookie_secure
    finally:
        async with sessions.begin() as session:
            await session.execute(delete(User).where(User.email == email))


async def test_duplicate_registration_is_case_insensitive(
    anonymous_client, sessions, auth_account
):
    response = await anonymous_client.post(
        "/auth/register",
        json={
            "name": "Other",
            "email": auth_account["email"].upper(),
            "password": PASSWORD,
        },
    )
    assert response.status_code == 409
    async with sessions() as session:
        users = list(
            await session.scalars(
                select(User).where(User.email == auth_account["email"])
            )
        )
        assert len(users) == 1
        assert users[0].name == "Jane Doe"


async def test_login_normalizes_email_and_rotates_current_session(
    anonymous_client, sessions, auth_account
):
    old_token = anonymous_client.cookies.get(settings.session_cookie_name)
    response = await anonymous_client.post(
        "/auth/login",
        json={"email": auth_account["email"].upper(), "password": PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["user"] == auth_account["user"]
    new_token = anonymous_client.cookies.get(settings.session_cookie_name)
    assert new_token != old_token
    async with sessions() as session:
        assert (
            await session.scalar(
                select(AuthSession).where(
                    AuthSession.token_hash == digest_token(old_token)
                )
            )
            is None
        )
        assert (
            await session.scalar(
                select(AuthSession).where(
                    AuthSession.token_hash == digest_token(new_token)
                )
            )
            is not None
        )


@pytest.mark.parametrize("known_email", [True, False])
async def test_failed_login_uses_same_generic_error(
    anonymous_client, sessions, auth_account, known_email
):
    response = await anonymous_client.post(
        "/auth/login",
        json={
            "email": auth_account["email"] if known_email else "missing@example.com",
            "password": "Wrong password 42!",
        },
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password."}
    assert "set-cookie" not in response.headers
    async with sessions() as session:
        assert (
            len(
                list(
                    await session.scalars(
                        select(AuthSession).where(
                            AuthSession.user_id == UUID(auth_account["user"]["id"])
                        )
                    )
                )
            )
            == 1
        )


@pytest.mark.parametrize(
    "path",
    [
        "/auth/me",
        "/auth/sessions",
        "/users/me",
    ],
)
async def test_private_routes_require_authentication(anonymous_client, path):
    response = await anonymous_client.get(path)
    assert response.status_code == 401


async def test_random_session_token_is_rejected(anonymous_client):
    anonymous_client.cookies.set(settings.session_cookie_name, "not-a-session")
    assert (await anonymous_client.get("/auth/me")).status_code == 401


async def test_expired_session_is_rejected(anonymous_client, sessions, auth_account):
    token = anonymous_client.cookies.get(settings.session_cookie_name)
    async with sessions.begin() as session:
        auth_session = await session.scalar(
            select(AuthSession).where(AuthSession.token_hash == digest_token(token))
        )
        auth_session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert (await anonymous_client.get("/auth/me")).status_code == 401


@pytest.mark.parametrize("token", [None, "wrong-csrf-token"])
async def test_authenticated_writes_require_valid_csrf(
    anonymous_client, sessions, auth_account, token
):
    anonymous_client.headers.pop("X-CSRF-Token", None)
    if token is not None:
        anonymous_client.headers["X-CSRF-Token"] = token
    response = await anonymous_client.patch("/users/me", json={"name": "Changed"})
    assert response.status_code == 403
    async with sessions() as session:
        assert (
            await session.get(User, UUID(auth_account["user"]["id"]))
        ).name == "Jane Doe"


async def test_foreign_origin_is_rejected_even_with_csrf(
    anonymous_client, auth_account
):
    response = await anonymous_client.patch(
        "/users/me",
        headers={"Origin": "https://evil.example"},
        json={"name": "Changed"},
    )
    assert response.status_code == 403


@pytest.mark.parametrize("path", ["/auth/register", "/auth/login"])
async def test_authentication_rejects_foreign_origin(anonymous_client, path):
    response = await anonymous_client.post(
        path,
        headers={"Origin": "https://evil.example"},
        json={"name": "Jane", "email": "jane@example.com", "password": PASSWORD},
    )
    assert response.status_code == 403


@pytest.mark.parametrize("path", ["/auth/register", "/auth/login"])
async def test_authentication_rejects_simple_content_type(anonymous_client, path):
    response = await anonymous_client.post(
        path,
        headers={"Content-Type": "text/plain"},
        content='{"name":"Jane","email":"jane@example.com","password":"'
        + PASSWORD
        + '"}',
    )
    assert response.status_code in (403, 415)


async def test_logout_revokes_session_and_is_idempotent(
    anonymous_client, sessions, auth_account
):
    token = anonymous_client.cookies.get(settings.session_cookie_name)
    response = await anonymous_client.post("/auth/logout")
    assert response.status_code == 204
    assert "max-age=0" in response.headers["set-cookie"].lower()
    async with sessions() as session:
        assert (
            await session.scalar(
                select(AuthSession).where(AuthSession.token_hash == digest_token(token))
            )
            is None
        )
    assert (await anonymous_client.get("/auth/me")).status_code == 401
    assert (await anonymous_client.post("/auth/logout")).status_code == 204


async def test_list_and_revoke_only_own_sessions(
    anonymous_client, api_client, auth_account
):
    response = await anonymous_client.get("/auth/sessions")
    assert response.status_code == 200
    own_sessions = response.json()
    assert len(own_sessions) == 1
    current = own_sessions[0]
    assert current["current"] is True
    assert set(current) == {"id", "created_at", "expires_at", "current"}
    foreign = (await api_client.get("/auth/sessions")).json()[0]
    assert (
        await anonymous_client.delete(f"/auth/sessions/{foreign['id']}")
    ).status_code == 404
    assert (await api_client.get("/auth/me")).status_code == 200
    assert (
        await anonymous_client.delete(f"/auth/sessions/{current['id']}")
    ).status_code == 204
    assert (await anonymous_client.get("/auth/me")).status_code == 401


async def test_logout_all_revokes_every_device(
    anonymous_client, client_factory, auth_account
):
    async with client_factory() as other_device:
        response = await other_device.post(
            "/auth/login", json={"email": auth_account["email"], "password": PASSWORD}
        )
        assert response.status_code == 200
        assert len((await anonymous_client.get("/auth/sessions")).json()) == 2
        assert (await anonymous_client.post("/auth/logout-all")).status_code == 204
        assert (await anonymous_client.get("/auth/me")).status_code == 401
        assert (await other_device.get("/auth/me")).status_code == 401


@pytest.mark.parametrize("password", ["tiny-pass", "x" * 129])
async def test_password_validation_does_not_expose_password(anonymous_client, password):
    response = await anonymous_client.post(
        "/auth/register",
        json={"name": "Jane", "email": "jane@example.com", "password": password},
    )
    assert response.status_code == 422
    assert password not in response.text
    assert "input" not in response.json()["detail"][0]


async def test_legacy_user_cannot_login_without_credentials(
    anonymous_client, owner_ids
):
    response = await anonymous_client.post(
        "/auth/login", json={"email": "legacy@example.com", "password": PASSWORD}
    )
    assert response.status_code == 401


async def test_csrf_token_from_another_session_is_rejected(
    anonymous_client, client_factory, auth_account
):
    async with client_factory() as other_device:
        response = await other_device.post(
            "/auth/login", json={"email": auth_account["email"], "password": PASSWORD}
        )
        assert response.status_code == 200
        other_device.headers["X-CSRF-Token"] = auth_account["csrf_token"]
        response = await other_device.patch("/users/me", json={"name": "Changed"})
        assert response.status_code == 403
        assert (await anonymous_client.get("/auth/me")).json()["user"][
            "name"
        ] == "Jane Doe"


async def test_allowed_origin_can_write_with_valid_csrf(
    anonymous_client, auth_account, monkeypatch
):
    monkeypatch.setattr(settings, "allowed_origins", ["https://app.example.com"])
    response = await anonymous_client.patch(
        "/users/me",
        headers={"Origin": "https://app.example.com"},
        json={"name": "Changed"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Changed"
