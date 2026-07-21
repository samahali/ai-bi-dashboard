"""
FastAPI dependencies — reusable injected components.
"""
from fastapi import Cookie, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import decode_token
from app.core.exceptions import UnauthorizedError
from app.db.models import User
from app.db.session import get_db

# auto_error=False: HTTPBearer's default behavior raises 403 on a missing/malformed
# header, which the frontend's 401-only auth interceptor doesn't recognize as an
# auth failure. Handling it ourselves keeps every "not authenticated" case a 401.
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Validate the access token and return the authenticated user.

    Token source, in priority order:
    1. The httpOnly `access_token` cookie (how the browser app authenticates).
    2. An `Authorization: Bearer <token>` header (for non-browser API clients).

    Raises UnauthorizedError (401) if the token is missing, invalid, or expired.
    """
    token = access_token or (credentials.credentials if credentials else None)
    if not token:
        raise UnauthorizedError("Not authenticated.")

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise UnauthorizedError("Invalid token type.")
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise UnauthorizedError("Invalid or expired token.")

    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()

    if user is None:
        raise UnauthorizedError("User not found or inactive.")

    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require the authenticated user to be an admin."""
    if not current_user.is_admin:
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError("Admin access required.")
    return current_user
