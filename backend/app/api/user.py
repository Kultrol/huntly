"""User-record endpoints with request-owned transactions.

These routes do not provide authentication or authorize access to user records.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import (
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.core.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.exceptions.user import UserNotFoundError, UserServiceError
from app.services.user import UserService

router: APIRouter = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserRead])
async def get_all_users(db: AsyncSession = Depends(get_db)) -> list[User]:
    """List stored users, ordered by name and UUID."""
    async with db.begin():
        user_service: UserService = UserService(db)
        try:
            return await user_service.get_all_users()
        except UserServiceError as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            )


@router.get("/{id}", response_model=UserRead)
async def get_user(id: UUID, db: AsyncSession = Depends(get_db)) -> User:
    """Retrieve a stored user by UUID."""
    async with db.begin():
        user_service: UserService = UserService(db)
        try:
            return await user_service.get_user(id)
        except UserNotFoundError as exc:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc))
        except UserServiceError as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            )


@router.post("/", response_model=UserRead, status_code=HTTP_201_CREATED)
async def create_user(new_user: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    """Create a user record with a display name."""
    async with db.begin():
        user_service: UserService = UserService(db)
        try:
            return await user_service.create_user(new_user)
        except UserServiceError as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            )


@router.patch("/{id}", response_model=UserRead)
async def update_user(
    id: UUID, user_data: UserUpdate, db: AsyncSession = Depends(get_db)
) -> User:
    """Apply a supplied display name; an omitted name remains unchanged."""
    async with db.begin():
        user_service: UserService = UserService(db)
        try:
            return await user_service.update_user(id, user_data)
        except UserNotFoundError as exc:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc))
        except UserServiceError as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            )


@router.delete("/{id}", status_code=HTTP_204_NO_CONTENT)
async def delete_user(id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    """Delete a user record.

    Deletion can fail while the user still owns companies, contacts, or roles.
    """
    async with db.begin():
        user_service: UserService = UserService(db)
        try:
            await user_service.delete_user(id)
        except UserNotFoundError as exc:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc))
        except UserServiceError as exc:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
            )
