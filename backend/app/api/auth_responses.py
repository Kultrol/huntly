"""Format public authentication responses and manage the browser's session cookie."""

from uuid import UUID

from fastapi import Response

from app.core.auth import SESSION_COOKIE_NAME
from app.core.config import settings
from app.core.security import csrf_token_for_session
from app.models import AuthSession, User
from app.schemas.auth import AuthRead, AuthUserRead, SessionRead


def set_session_cookie(response: Response, token: str) -> None:
    """Send the raw login token in an HttpOnly cookie after its row is committed.

    HttpOnly keeps browser JavaScript from reading the login token. Cookie expiry
    controls browser storage; the session's database deadline controls access.
    """
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=settings.session_lifetime_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"


def clear_session_cookie(response: Response) -> None:
    """Remove the cookie using the same path and security settings used to set it."""
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"


def auth_response(user: User, token: str) -> AuthRead:
    """Return public profile fields and the CSRF token needed for later writes."""
    return AuthRead(
        user=AuthUserRead.model_validate(user), csrf_token=csrf_token_for_session(token)
    )


def session_response(session: AuthSession, current_session_id: UUID) -> SessionRead:
    """Expose a session's ID and dates, marking the login making this request."""
    return SessionRead(
        id=session.id,
        created_at=session.created_at,
        expires_at=session.expires_at,
        current=session.id == current_session_id,
    )
