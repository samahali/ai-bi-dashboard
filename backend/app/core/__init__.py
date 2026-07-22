"""
Cross-cutting concerns (auth primitives, cookies, exceptions, rate limiting),
re-exported so call sites can do `from app.core import NotFoundError` instead
of importing each module.
"""

from app.core.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.cookies import clear_auth_cookies, set_auth_cookies
from app.core.exceptions import (
    AIServiceError,
    AppError,
    ConflictError,
    DatasetNotReadyError,
    FileTooLargeError,
    ForbiddenError,
    InvalidFileTypeError,
    NotFoundError,
    PromptInjectionError,
    UnauthorizedError,
    ValidationError,
)
from app.core.rate_limit import limiter

__all__ = [
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "hash_password",
    "verify_password",
    "clear_auth_cookies",
    "set_auth_cookies",
    "AIServiceError",
    "AppError",
    "ConflictError",
    "DatasetNotReadyError",
    "FileTooLargeError",
    "ForbiddenError",
    "InvalidFileTypeError",
    "NotFoundError",
    "PromptInjectionError",
    "UnauthorizedError",
    "ValidationError",
    "limiter",
]
