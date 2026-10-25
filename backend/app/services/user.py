from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.engine import ScalarResult
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.exceptions.user import (
    UserCreationError,
    UserDeletionError,
    UserFetchingError,
    UserNotFoundError,
    UserUpdateError,
)


class UserService:
    """Manage stored user records without authentication or access authorization.

    Mutations flush without committing; the caller owns commit and rollback.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db: AsyncSession = db

    async def get_user(self, id: UUID) -> User:
        """Fetch a user by ID; raise UserNotFoundError if absent."""
        try:
            user: User | None = await self.db.get(User, id)
            if user is None:
                raise UserNotFoundError(f"User with id {id} not found.")
            return user
        except SQLAlchemyError as exc:
            raise UserFetchingError(f"Failed to get user: {id}") from exc

    async def get_all_users(self) -> list[User]:
        """List all users ordered by name and ID; the caller must authorize global
        access.
        """
        try:
            stmt: Select[tuple[User]] = select(User).order_by(User.name, User.id)
            users: ScalarResult[User] = await self.db.scalars(stmt)
            return list(users)
        except SQLAlchemyError as exc:
            raise UserFetchingError("Failed to get all users") from exc

    async def create_user(self, new_user: UserCreate) -> User:
        """Create a user record without provisioning authentication credentials."""
        try:
            user: User = User(**new_user.model_dump())
            self.db.add(user)
            await self.db.flush()
            return user
        except SQLAlchemyError as exc:
            raise UserCreationError("Failed to create user") from exc

    async def delete_user(self, id: UUID) -> None:
        """Delete a user after its owned records have been handled separately.

        Remaining companies, contacts, or roles can prevent deletion and raise
        UserDeletionError.
        """
        user: User = await self.get_user(id)
        try:
            await self.db.delete(user)
            await self.db.flush()
        except SQLAlchemyError as exc:
            raise UserDeletionError(f"Failed to delete user: {id}") from exc

    async def update_user(self, id: UUID, updated_user: UserUpdate) -> User:
        """Apply a supplied display name; an omitted name remains unchanged."""
        user: User = await self.get_user(id)
        try:
            for key, value in updated_user.model_dump(exclude_unset=True).items():
                setattr(user, key, value)
            await self.db.flush()
            return user
        except SQLAlchemyError as exc:
            raise UserUpdateError(f"Failed to update user: {id}") from exc
