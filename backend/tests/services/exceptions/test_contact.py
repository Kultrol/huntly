import pytest

from app.services.exceptions.contact import (
    ContactCompanyError,
    ContactCreationError,
    ContactDeletionError,
    ContactFetchingError,
    ContactNotFoundError,
    ContactServiceError,
    ContactUpdateError,
)
from app.services.exceptions.service import ServiceError


# Each contact error must keep its message and belong to its service error family.
@pytest.mark.parametrize(
    "error_class",
    [
        ContactNotFoundError,
        ContactFetchingError,
        ContactCreationError,
        ContactUpdateError,
        ContactDeletionError,
        ContactCompanyError,
    ],
)
def test_contact_errors_preserve_message_and_domain_family(error_class):
    error = error_class("Useful failure details")
    assert str(error) == "Useful failure details"
    assert error.args == ("Useful failure details",)
    assert isinstance(error, ContactServiceError)
    assert isinstance(error, ServiceError)
    assert error.message == "Useful failure details"
