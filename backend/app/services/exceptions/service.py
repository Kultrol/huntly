"""Common base for domain-service errors; HTTP translation belongs to API routes."""


class ServiceError(Exception):
    """Base exception for service failures and unmet domain preconditions."""
