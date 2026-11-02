"""Authenticated profile endpoints; user IDs never grant access by themselves.

Routes pass the signed-in user's ID to the shared helpers. Routes accepting an
explicit ID must first check it with require_self.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_responses import clear_session_cookie
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserRead, UserUpdate
from app.services.exceptions.user import UserNotFoundError, UserServiceError
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])
Database = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def require_self(id: UUID, user: User) -> None:
    """Hide another user's profile behind the same 404 used for a missing user."""
    if id != user.id:
        raise HTTPException(status_code=404, detail=f"User with id {id} not found.")


async def read_profile(id: UUID, db: AsyncSession) -> User:
    """Read a profile after the caller has checked that it is the current user's."""
    async with db.begin():
        try:
            return await UserService(db).get_user(id)
        except UserNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except UserServiceError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc


async def edit_profile(id: UUID, data: UserUpdate, db: AsyncSession) -> User:
    """Commit validated profile fields for an ID authorized by the calling route."""
    async with db.begin():
        try:
            return await UserService(db).update_user(id, data)
        except UserNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except UserServiceError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc


async def remove_profile(id: UUID, db: AsyncSession, response: Response) -> None:
    """Delete an authorized profile only after its owned domain records are removed.

    The existing service retains that deletion constraint. Successful deletion
    also cascades to login sessions; clear the browser cookie after commit.
    """
    async with db.begin():
        try:
            await UserService(db).delete_user(id)
        except UserNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except UserServiceError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
    clear_session_cookie(response)


@router.get("/me", response_model=UserRead)
async def me(db: Database, user: CurrentUser) -> User:
    return await read_profile(user.id, db)


@router.patch("/me", response_model=UserRead)
async def update_me(data: UserUpdate, db: Database, user: CurrentUser) -> User:
    return await edit_profile(user.id, data, db)


@router.delete("/me", status_code=204)
async def delete_me(response: Response, db: Database, user: CurrentUser) -> None:
    await remove_profile(user.id, db, response)


@router.get("/{id}", response_model=UserRead)
async def get_user(id: UUID, db: Database, user: CurrentUser) -> User:
    require_self(id, user)
    return await read_profile(id, db)


@router.patch("/{id}", response_model=UserRead)
async def update_user(
    id: UUID, user_data: UserUpdate, db: Database, user: CurrentUser
) -> User:
    require_self(id, user)
    return await edit_profile(id, user_data, db)


@router.delete("/{id}", status_code=204)
async def delete_user(
    id: UUID, response: Response, db: Database, user: CurrentUser
) -> None:
    require_self(id, user)
    await remove_profile(id, db, response)
