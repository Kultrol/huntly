import json
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select

from app.core.config import settings
from app.core.security import verify_password
from app.models import AuthSession, User

pytestmark = pytest.mark.anyio
PASSWORD = "  密碼 café 🔐  "
NEW_PASSWORD = "  다른 密碼 cafe\u0301 🔑  "


@pytest.fixture
async def unicode_account(anonymous_client, sessions):
    email = f"auth-unicode-{uuid4().hex}@example.com"
    response = await anonymous_client.post(
        "/auth/register",
        content=json.dumps(
            {"name": "Unicode owner", "email": email, "password": PASSWORD}
        ),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 201
    account = response.json()
    user_id = UUID(account["user"]["id"])
    anonymous_client.headers["X-CSRF-Token"] = account["csrf_token"]
    try:
        yield {"id": user_id, "email": email}
    finally:
        async with sessions.begin() as session:
            await session.execute(delete(User).where(User.id == user_id))


@pytest.mark.parametrize("surrogate", [chr(0xD800), chr(0xDFFF)], ids=["high", "low"])
@pytest.mark.parametrize(
    "operation, field",
    [
        ("register", "password"),
        ("login", "password"),
        ("password", "current_password"),
        ("password", "new_password"),
    ],
)
async def test_invalid_unicode_password_preserves_account_session_and_cookie(
    anonymous_client, sessions, unicode_account, surrogate, operation, field
):
    other_email = f"invalid-unicode-{uuid4().hex}@example.com"
    if operation == "register":
        payload = {"name": "Rejected owner", "email": other_email, "password": PASSWORD}
    elif operation == "login":
        payload = {"email": unicode_account["email"], "password": PASSWORD}
    else:
        payload = {"current_password": PASSWORD, "new_password": NEW_PASSWORD}
    payload[field] = "Malformed password " + surrogate
    # JSON escapes can carry a lone surrogate through decoding even though that
    # character cannot be encoded directly as UTF-8 by the password hasher.
    body = json.dumps(payload, ensure_ascii=True)
    assert f"\\u{ord(surrogate):04x}" in body
    previous_cookie = anonymous_client.cookies.get(settings.session_cookie_name)
    session_query = select(
        AuthSession.id,
        AuthSession.token_hash,
        AuthSession.csrf_token_hash,
        AuthSession.created_at,
        AuthSession.expires_at,
    ).where(AuthSession.user_id == unicode_account["id"])
    async with sessions() as session:
        previous_hash = (await session.get(User, unicode_account["id"])).password_hash
        previous_sessions = (await session.execute(session_query)).all()

    response = await anonymous_client.request(
        "PATCH" if operation == "password" else "POST",
        f"/auth/{operation}",
        content=body,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == [
        {
            "loc": ["body", field],
            "msg": "Value error, Password must contain valid Unicode text.",
            "type": "value_error",
        }
    ]
    assert "Malformed password" not in response.text
    assert "set-cookie" not in response.headers
    assert anonymous_client.cookies.get(settings.session_cookie_name) == previous_cookie
    async with sessions() as session:
        user = await session.get(User, unicode_account["id"])
        assert user.password_hash == previous_hash
        assert verify_password(PASSWORD, user.password_hash)
        assert (await session.execute(session_query)).all() == previous_sessions
        assert (
            await session.scalar(select(User.id).where(User.email == other_email))
            is None
        )
    assert (await anonymous_client.get("/auth/me")).status_code == 200


async def test_valid_unicode_passwords_survive_registration_login_and_password_change(
    anonymous_client, sessions, unicode_account
):
    async with sessions() as session:
        user = await session.get(User, unicode_account["id"])
        assert verify_password(PASSWORD, user.password_hash)
        assert not verify_password(PASSWORD.strip(), user.password_hash)

    login = await anonymous_client.post(
        "/auth/login",
        content=json.dumps({"email": unicode_account["email"], "password": PASSWORD}),
        headers={"Content-Type": "application/json"},
    )
    assert login.status_code == 200
    anonymous_client.headers["X-CSRF-Token"] = login.json()["csrf_token"]
    change = await anonymous_client.patch(
        "/auth/password",
        content=json.dumps(
            {"current_password": PASSWORD, "new_password": NEW_PASSWORD}
        ),
        headers={"Content-Type": "application/json"},
    )
    assert change.status_code == 204
    assert (await anonymous_client.get("/auth/me")).status_code == 401
    async with sessions() as session:
        user = await session.get(User, unicode_account["id"])
        assert verify_password(NEW_PASSWORD, user.password_hash)
        assert not verify_password(PASSWORD, user.password_hash)

    login = await anonymous_client.post(
        "/auth/login",
        content=json.dumps(
            {"email": unicode_account["email"], "password": NEW_PASSWORD}
        ),
        headers={"Content-Type": "application/json"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["id"] == str(unicode_account["id"])
    assert NEW_PASSWORD not in login.text
    assert (await anonymous_client.get("/auth/me")).status_code == 200
