"""Domain conditions and database-operation failures for user services."""

from app.services.exceptions.service import ServiceError


class UserServiceError(ServiceError):
    """Base error for operations on stored user records."""

    def __init__(self, message: str) -> None:
        self.message: str = message
        super().__init__(message)


class UserNotFoundError(UserServiceError):
    """The requested user UUID does not identify a stored user."""


class UserFetchingError(UserServiceError):
    """A database operation failed while retrieving user records."""


class UserCreationError(UserServiceError):
    """A database operation failed while creating a user."""


class UserUpdateError(UserServiceError):
    """A database operation failed while updating a user."""


class UserDeletionError(UserServiceError):
    """A database operation failed while deleting a user."""
