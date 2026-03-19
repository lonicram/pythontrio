"""Custom exceptions for the application."""


class AssetNotFoundError(Exception):
    """Raised when an attempt is made to operate on a non-existent asset."""

    pass
