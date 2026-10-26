"""Domain conditions and database-operation failures for event services."""

from app.services.exceptions.service import ServiceError


class EventServiceError(ServiceError):
    """Base error for operations on events attached to tracked roles."""


class EventNotFoundError(EventServiceError):
    """The requested event UUID does not identify a stored event."""


class EventFetchingError(EventServiceError):
    """A database operation failed while retrieving an event or its parent."""


class EventCreationError(EventServiceError):
    """A database operation failed while creating an event or its history."""


class EventUpdateError(EventServiceError):
    """A database operation failed while updating an event or its history."""


class EventDeletionError(EventServiceError):
    """A database operation failed while deleting an event."""
