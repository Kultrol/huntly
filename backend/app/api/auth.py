"""Handle auth requests, committing changes before updating browser cookies."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_responses import (
    auth_response,
    clear_session_cookie,
    session_response,
    set_session_cookie,
)
from app.core.auth import (
    SESSION_COOKIE_NAME,
    AuthContext,
    CSRFHeader,
    get_auth_context,
    require_json_request,
    validate_csrf,
    validate_origin,
)
from app.core.database import get_db
from app.schemas.auth import (
    AuthRead,
    LoginRequest,
    RegisterRequest,
    SessionRead,
)
from app.services.auth import AuthService
from app.services.auth_session import AuthSessionService

router = APIRouter(prefix="/auth", tags=["auth"])
Database = Annotated[AsyncSession, Depends(get_db)]
Authenticated = Annotated[AuthContext, Depends(get_auth_context)]


@router.post(
    "/register",
    response_model=AuthRead,
    status_code=201,
    dependencies=[Depends(require_json_request)],
)
async def register(
    data: RegisterRequest, request: Request, response: Response, db: Database
) -> AuthRead:
    """Create an account and its first session in one transaction."""
    try:
        async with db.begin():
            user, token = await AuthService(db).register(
                data, request.cookies.get(SESSION_COOKIE_NAME)
            )
    except IntegrityError as exc:
        # Only duplicate emails are conflicts; unrelated storage errors stay errors.
        diagnostic = getattr(exc.orig, "diag", None)
        if diagnostic is not None and diagnostic.constraint_name == "uq_users_email":
            raise HTTPException(
                status_code=409, detail="Email is already registered."
            ) from exc
        raise
    # Never issue a login cookie unless its session row committed successfully.
    set_session_cookie(response, token)
    return auth_response(user, token)


@router.post(
    "/login", response_model=AuthRead, dependencies=[Depends(require_json_request)]
)
async def login(
    data: LoginRequest, request: Request, response: Response, db: Database
) -> AuthRead:
    """Verify credentials and replace this browser's session with a fresh one."""
    async with db.begin():
        user, token = await AuthService(db).login(
            data, request.cookies.get(SESSION_COOKIE_NAME)
        )
    set_session_cookie(response, token)
    return auth_response(user, token)


@router.get("/me", response_model=AuthRead)
async def me(response: Response, context: Authenticated) -> AuthRead:
    """Restore the current profile and CSRF token, for example after a page reload."""
    response.headers["Cache-Control"] = "no-store"
    return auth_response(context.user, context.token)


@router.post("/logout", status_code=204)
async def logout(
    request: Request, response: Response, db: Database, csrf_token: CSRFHeader = None
) -> None:
    """Revoke the current login and clear its cookie, even if it already expired."""
    validate_origin(request)
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token and len(token) <= 128:
        session_service = AuthSessionService(db)
        async with db.begin():
            session = await session_service.find_by_token(token)
            if session is not None:
                # Expired logins grant no access and can be removed without CSRF.
                if session.expires_at > datetime.now(UTC):
                    validate_csrf(request, session, csrf_token)
                await session_service.revoke_owned(session.id, session.user_id)
    clear_session_cookie(response)


@router.post("/logout-all", status_code=204)
async def logout_all(response: Response, db: Database, context: Authenticated) -> None:
    """Revoke all of this user's sessions, including the current one."""
    async with db.begin():
        await AuthService(db).logout_all(context.user.id)
    clear_session_cookie(response)


@router.get("/sessions", response_model=list[SessionRead])
async def sessions(
    response: Response, db: Database, context: Authenticated
) -> list[SessionRead]:
    """List this user's active logins without exposing secret token hashes."""
    async with db.begin():
        active_sessions = await AuthSessionService(db).list_active(context.user.id)
    response.headers["Cache-Control"] = "no-store"
    return [
        session_response(session, context.session.id) for session in active_sessions
    ]


@router.delete("/sessions/{id}", status_code=204)
async def revoke_session(
    id: UUID, response: Response, db: Database, context: Authenticated
) -> None:
    """Revoke one owned session; foreign and missing IDs both return 404."""
    async with db.begin():
        revoked = await AuthSessionService(db).revoke_owned(id, context.user.id)
        if not revoked:
            raise HTTPException(status_code=404, detail="Session not found.")
    if id == context.session.id:
        clear_session_cookie(response)
