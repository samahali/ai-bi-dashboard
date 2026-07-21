"""
Auth router — register, login, logout, token refresh, me.

Tokens are delivered as httpOnly cookies (see app/core/cookies.py) so they
are not readable by client-side JavaScript. The response body still includes
the tokens for non-browser API clients, but the browser app ignores them and
relies on the cookies. The refresh token is read from its cookie, never a
query string (which would leak it into logs/history).
"""
from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.config import settings
from app.core.cookies import clear_auth_cookies, set_auth_cookies
from app.core.exceptions import UnauthorizedError
from app.core.rate_limit import limiter
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=201)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def register(
    request: Request,
    payload: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user, set auth cookies, and return the user + tokens."""
    result = await AuthService(db).register(payload)
    set_auth_cookies(response, result.access_token, result.refresh_token)
    return result


@router.post("/login", response_model=AuthResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def login(
    request: Request,
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate, set auth cookies, and return the user + tokens."""
    result = await AuthService(db).login(payload)
    set_auth_cookies(response, result.access_token, result.refresh_token)
    return result


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange the refresh-token cookie for a fresh access token, and reset the
    access cookie. The refresh token comes from the httpOnly cookie only.
    """
    if not refresh_token:
        raise UnauthorizedError("No refresh token provided.")
    result = await AuthService(db).refresh(refresh_token)
    # Only the access cookie changes; the refresh token is unchanged/rotated
    # inside the service and re-set here to refresh its Max-Age.
    set_auth_cookies(response, result.access_token, result.refresh_token)
    return result


@router.post("/logout", status_code=200)
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke the current user's refresh tokens and clear the auth cookies."""
    await AuthService(db).logout(current_user.id)
    clear_auth_cookies(response)
    return {"message": "Logged out successfully."}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user
