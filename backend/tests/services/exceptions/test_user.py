import pytest

from app.services.exceptions.service import ServiceError
from app.services.exceptions.user import (
    UserCreationError,
    UserDeletionError,
    UserFetchingError,
    UserNotFoundError,
    UserServiceError,
    UserUpdateError,
)


# Each user error must keep its message and belong to its service error family.
@pytest.mark.parametrize(
    "error_class",
    [
        UserNotFoundError,
        UserFetchingError,
        UserCreationError,
        UserUpdateError,
        UserDeletionError,
    ],
)
def test_user_errors_preserve_message_and_domain_family(error_class):
    error = error_class("Useful failure details")
    assert str(error) == "Useful failure details"
    assert error.args == ("Useful failure details",)
    assert isinstance(error, UserServiceError)
    assert isinstance(error, ServiceError)
    assert error.message == "Useful failure details"
