from __future__ import annotations


class ServiceError(Exception):
    """Base class for service-level errors."""


class NotFoundError(ServiceError):
    """Raised when a requested entity is not found."""


class AlreadyExistsError(ServiceError):
    """Raised when an entity already exists."""


class ValidationError(ServiceError):
    """Raised when input data is invalid."""
