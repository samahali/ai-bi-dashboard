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
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Resource not found."


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    detail = "Resource already exists."


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Authentication required."


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "You do not have permission to perform this action."


class ValidationError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Validation error."


class FileTooLargeError(AppError):
    status_code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    detail = "Uploaded file exceeds the maximum allowed size."


class InvalidFileTypeError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Unsupported file type."


class AIServiceError(AppError):
    status_code = status.HTTP_502_BAD_GATEWAY
    detail = "AI service is unavailable or returned an error."


class PromptInjectionError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Question contains disallowed content."


class DatasetNotReadyError(AppError):
    status_code = status.HTTP_409_CONFLICT
    detail = "Dataset is still being processed. Please try again shortly."
