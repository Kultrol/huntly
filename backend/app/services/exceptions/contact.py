"""Domain conditions and database-operation failures for contact services."""

from app.services.exceptions.service import ServiceError


class ContactServiceError(ServiceError):
    """Base error for contact operations and their domain preconditions."""

    def __init__(self, message: str) -> None:
        self.message: str = message
        super().__init__(message)


class ContactNotFoundError(ContactServiceError):
    """The requested contact UUID does not identify a stored contact."""


class ContactFetchingError(ContactServiceError):
    """A database operation failed while retrieving contact records."""


class ContactCreationError(ContactServiceError):
    """A database operation failed while creating a contact."""


class ContactUpdateError(ContactServiceError):
    """A database operation failed while updating a contact."""


class ContactDeletionError(ContactServiceError):
    """A database operation failed while deleting a contact."""


class ContactCompanyError(ContactServiceError):
    """A proposed company affiliation is absent or belongs to another user."""
