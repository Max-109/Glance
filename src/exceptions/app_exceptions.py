class GlanceError(Exception):
    """Base class for application errors."""


class ValidationError(GlanceError):
    """Raised when the user or system provides invalid data."""


class NotFoundError(GlanceError):
    """Raised when an expected entity cannot be found."""


class StorageError(GlanceError):
    """Raised when persistence fails."""


class ProviderError(GlanceError):
    """Raised when an external provider call fails."""


class PermissionDeniedError(GlanceError):
    """Raised when a protected system resource cannot be accessed."""
