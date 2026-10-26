import pytest

from app.services.exceptions.service import ServiceError
from app.services.exceptions.tracked_role import (
    TrackedRoleCompanyError,
    TrackedRoleCreationError,
    TrackedRoleDeletionError,
    TrackedRoleFetchingError,
    TrackedRoleNotFoundError,
    TrackedRoleServiceError,
    TrackedRoleUpdateError,
)


# Each tracked role error must keep its message and belong to its service error family.
@pytest.mark.parametrize(
    "error_class",
    [
        TrackedRoleNotFoundError,
        TrackedRoleFetchingError,
        TrackedRoleCreationError,
        TrackedRoleUpdateError,
        TrackedRoleDeletionError,
        TrackedRoleCompanyError,
    ],
)
def test_tracked_role_errors_preserve_message_and_domain_family(error_class):
    error = error_class("Useful failure details")
    assert str(error) == "Useful failure details"
    assert error.args == ("Useful failure details",)
    assert isinstance(error, TrackedRoleServiceError)
    assert isinstance(error, ServiceError)
