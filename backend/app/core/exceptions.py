"""
Custom application exceptions.

All exceptions inherit from AppError so the global handler can catch them
and return consistent JSON error responses.
"""

from fastapi import HTTPException, status


class AppError(HTTPException):
    """Base application exception."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "An unexpected error occurred."

    def __init__(self, detail: str | None = None):
        super().__init__(
            status_code=self.__class__.status_code,
            detail=detail or self.__class__.detail,
        )


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    status_code = status.HTTP_404_NOT_FOUND
    detail = "Resource not found."


class ConflictError(AppError):
    """Raised when a resource already exists or conflicts with current state."""

    status_code = status.HTTP_409_CONFLICT
    detail = "Resource already exists."


class UnauthorizedError(AppError):
    """Raised when the request lacks valid authentication credentials."""

    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Authentication required."


class ForbiddenError(AppError):
    """Raised when an authenticated user does not own the requested resource."""

    status_code = status.HTTP_403_FORBIDDEN
    detail = "You do not have permission to perform this action."


class ValidationError(AppError):
    """Raised when request data fails validation beyond Pydantic's schema checks."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Validation error."


class FileTooLargeError(AppError):
    """Raised when an uploaded file exceeds the configured size limit."""

    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    detail = "Uploaded file exceeds the maximum allowed size."


class InvalidFileTypeError(AppError):
    """Raised when an uploaded file's extension/content type is not supported."""

    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Unsupported file type."


class AIServiceError(AppError):
    """Raised when the LLM provider (Watsonx/OpenAI) fails or is unreachable."""

    status_code = status.HTTP_502_BAD_GATEWAY
    detail = "AI service is unavailable or returned an error."


class PromptInjectionError(AppError):
    """Raised when a user question is flagged as a prompt injection attempt."""

    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Question contains disallowed content."


class DatasetNotReadyError(AppError):
    """Raised when an operation is attempted on a dataset still being processed."""

    status_code = status.HTTP_409_CONFLICT
    detail = "Dataset is still being processed. Please try again shortly."
