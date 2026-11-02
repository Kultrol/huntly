"""Handle auth requests, committing changes before updating browser cookies."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_responses import (
    auth_response,
    set_session_cookie,
)
from app.core.auth import (
    SESSION_COOKIE_NAME,
    AuthContext,
    get_auth_context,
    require_json_request,
)
from app.core.database import get_db
from app.schemas.auth import (
    AuthRead,
    LoginRequest,
    RegisterRequest,
)
from app.services.auth import AuthService

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
