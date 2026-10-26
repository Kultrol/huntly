"""Domain conditions and database-operation failures for tracked role services."""

from app.services.exceptions.service import ServiceError


class TrackedRoleServiceError(ServiceError):
    """Base error for tracked-role operations and their domain preconditions."""


class TrackedRoleNotFoundError(TrackedRoleServiceError):
    """The requested role UUID does not identify a stored tracked role."""


class TrackedRoleFetchingError(TrackedRoleServiceError):
    """A database operation failed while retrieving tracked-role records."""


class TrackedRoleCreationError(TrackedRoleServiceError):
    """A database operation failed while creating a role or its history."""


class TrackedRoleUpdateError(TrackedRoleServiceError):
    """A database operation failed while updating a role or its history."""


class TrackedRoleDeletionError(TrackedRoleServiceError):
    """A database operation failed while deleting a tracked role."""


class TrackedRoleCompanyError(TrackedRoleServiceError):
    """A proposed company affiliation is absent or belongs to another user."""
