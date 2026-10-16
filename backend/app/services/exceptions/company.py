"""Domain conditions and database-operation failures for company services."""

from app.services.exceptions.service import ServiceError


class CompanyServiceError(ServiceError):
    """Base error for company operations and their domain preconditions."""


class CompanyNotFoundError(CompanyServiceError):
    """The requested company UUID does not identify a stored company.

    Attributes:
        message: Human-readable explanation passed to the base exception.
    """

    def __init__(self, message: str) -> None:
        """Keep the failure message accessible to service callers.

        Args:
            message: Human-readable explanation of the failed operation or condition.

        Returns:
            None: Initializes the exception and its message attribute.

        Raises:
            None: Initialization performs no domain validation.
        """
        self.message: str = message
        super().__init__(message)


class CompanyFetchingError(CompanyServiceError):
    """A database operation failed while retrieving company records.

    Attributes:
        message: Human-readable explanation passed to the base exception.
    """

    def __init__(self, message: str) -> None:
        """Keep the failure message accessible to service callers.

        Args:
            message: Human-readable explanation of the failed operation or condition.

        Returns:
            None: Initializes the exception and its message attribute.

        Raises:
            None: Initialization performs no domain validation.
        """
        self.message: str = message
        super().__init__(message)


class CompanyCreationError(CompanyServiceError):
    """A database operation failed while creating a company.

    Attributes:
        message: Human-readable explanation passed to the base exception.
    """

    def __init__(self, message: str) -> None:
        """Keep the failure message accessible to service callers.

        Args:
            message: Human-readable explanation of the failed operation or condition.

        Returns:
            None: Initializes the exception and its message attribute.

        Raises:
            None: Initialization performs no domain validation.
        """
        self.message: str = message
        super().__init__(message)


class CompanyUpdateError(CompanyServiceError):
    """A database operation failed while updating a company.

    Attributes:
        message: Human-readable explanation passed to the base exception.
    """

    def __init__(self, message: str) -> None:
        """Keep the failure message accessible to service callers.

        Args:
            message: Human-readable explanation of the failed operation or condition.

        Returns:
            None: Initializes the exception and its message attribute.

        Raises:
            None: Initialization performs no domain validation.
        """
        self.message: str = message
        super().__init__(message)


class CompanyDeletionError(CompanyServiceError):
    """A database operation failed while deleting a company.

    Attributes:
        message: Human-readable explanation passed to the base exception.
    """

    def __init__(self, message: str) -> None:
        """Keep the failure message accessible to service callers.

        Args:
            message: Human-readable explanation of the failed operation or condition.

        Returns:
            None: Initializes the exception and its message attribute.

        Raises:
            None: Initialization performs no domain validation.
        """
        self.message: str = message
        super().__init__(message)


class CompanyAlreadyExistsError(CompanyServiceError):
    """A normalized company name already belongs to this user workspace.

    Attributes:
        message: Human-readable explanation passed to the base exception.
    """

    def __init__(self, message: str) -> None:
        """Keep the failure message accessible to service callers.

        Args:
            message: Human-readable explanation of the failed operation or condition.

        Returns:
            None: Initializes the exception and its message attribute.

        Raises:
            None: Initialization performs no domain validation.
        """
        self.message: str = message
        super().__init__(message)
