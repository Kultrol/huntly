import pytest

from app.services.exceptions.event import (
    EventCreationError,
    EventDeletionError,
    EventFetchingError,
    EventNotFoundError,
    EventServiceError,
    EventUpdateError,
)
from app.services.exceptions.service import ServiceError


# Each event error must keep its message and belong to its service error family.
@pytest.mark.parametrize(
    "error_class",
    [
        EventNotFoundError,
        EventFetchingError,
        EventCreationError,
        EventUpdateError,
        EventDeletionError,
    ],
)
def test_event_errors_preserve_message_and_domain_family(error_class):
    error = error_class("Useful failure details")
    assert str(error) == "Useful failure details"
    assert error.args == ("Useful failure details",)
    assert isinstance(error, EventServiceError)
    assert isinstance(error, ServiceError)
