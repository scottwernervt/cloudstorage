"""Exceptions for Cloud Storage errors."""

from http import HTTPStatus


class CloudStorageError(Exception):
    """Base class for exceptions."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(CloudStorageError):
    """Raised when a container or blob does not exist."""

    code = HTTPStatus.NOT_FOUND


class IsNotEmptyError(CloudStorageError):
    """Raised when the container is not empty."""

    code = HTTPStatus.CONFLICT


class CredentialsError(CloudStorageError):
    """Raised when driver credentials are invalid."""

    code = HTTPStatus.UNAUTHORIZED


class SignatureExpiredError(CloudStorageError):
    """Raised when signature timestamp is older than required maximum age."""

    code = HTTPStatus.UNAUTHORIZED

    def __init__(self) -> None:
        super().__init__(message="The signature has expired.")
