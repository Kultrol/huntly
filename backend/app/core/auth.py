"""Resolve cookie sessions and protect browser writes before resource handlers run."""

import hmac
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import APIKeyCookie
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import csrf_token_for_session, digest_token
from app.models import AuthSession, User
from app.services.auth_session import AuthSessionService

SESSION_COOKIE_NAME = settings.session_cookie_name
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
session_cookie = APIKeyCookie(name=SESSION_COOKIE_NAME, auto_error=False)
# Optional in the API schema because GETs and anonymous logout need no CSRF token.
# Authenticated writes enforce its presence below and return 403 when it is missing.
CSRFHeader = Annotated[
    str | None,
    Header(
        alias="X-CSRF-Token",
        description=(
            "Required for authenticated POST, PATCH, PUT, and DELETE requests. "
            "Use csrf_token from registration, login, or GET /auth/me. "
            "Safe requests and logout without an active session do not require it."
        ),
    ),
]


@dataclass
class AuthContext:
    """Verified user and session, with the raw cookie retained only for this request."""

    user: User
    session: AuthSession
    token: str

    @property
    def csrf_token(self) -> str:
        """Recover the session's CSRF token for a response such as GET /auth/me."""
        return csrf_token_for_session(self.token)


def validate_origin(request: Request) -> None:
    """Check where a browser request came from against the configured origins.

    CLI clients can omit Origin; an explicit cross-site browser signal is rejected.
    """
    origin = request.headers.get("origin")
    if origin is not None and origin not in settings.allowed_origins:
        raise HTTPException(status_code=403, detail="Origin is not allowed.")
    if origin is None and request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(
            status_code=403, detail="Cross-site request is not allowed."
        )


def require_json_request(request: Request) -> None:
    """Protect login and registration with origin checks and a JSON-only body.

    A cross-site HTML form cannot submit application/json. Cross-origin browser
    fetches with this content type need CORS approval before sending the request.
    """
    validate_origin(request)
    content_type = (
        request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    )
    if content_type != "application/json":
        raise HTTPException(
            status_code=415, detail="Content-Type must be application/json."
        )


def validate_csrf(request: Request, session: AuthSession, token: str | None) -> None:
    """Require both an approved browser origin and this session's CSRF token.

    The cookie identifies the session; the separate header proves the caller
    obtained its CSRF token rather than relying on an automatically sent cookie.
    """
    validate_origin(request)
    if (
        not token
        or len(token) > 256
        or not hmac.compare_digest(digest_token(token), session.csrf_token_hash)
    ):
        raise HTTPException(status_code=403, detail="Invalid or missing CSRF token.")


async def get_auth_context(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str | None, Depends(session_cookie)],
    csrf_token: CSRFHeader = None,
) -> AuthContext:
    """Resolve an unexpired session from the cookie and guard authenticated writes.

    Routes receive the stored owner identity instead of trusting a supplied user ID.
    """
    if token is None or len(token) > 128:
        raise HTTPException(status_code=401, detail="Authentication required.")
    # Finish this lookup transaction so resource routes can own db.begin().
    async with db.begin():
        result = await AuthSessionService(db).find_active_with_user(token)
    if result is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    session, user = result
    if request.method not in SAFE_METHODS:
        validate_csrf(request, session, csrf_token)
    return AuthContext(user=user, session=session, token=token)


async def get_current_user(
    context: Annotated[AuthContext, Depends(get_auth_context)],
) -> User:
    """Provide the verified owner identity to resource routes."""
    return context.user
