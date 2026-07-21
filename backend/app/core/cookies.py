"""
Auth cookie helpers.

Tokens are delivered to the browser as httpOnly cookies rather than in the
response body / localStorage, so client-side JavaScript (and therefore any
XSS) cannot read them. See docs/SECURITY.md.
"""
from fastapi import Response

from app.config import settings

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"


def _secure() -> bool:
    # Force Secure (HTTPS-only) cookies in production regardless of the raw
    # cookie_secure setting, so a prod misconfiguration can't downgrade them.
    return settings.cookie_secure or settings.app_env == "production"


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Attach httpOnly access + refresh token cookies to the response."""
    response.set_cookie(
        key=ACCESS_COOKIE,
        value=access_token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=_secure(),
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path="/",
    )
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=_secure(),
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        # Scope the refresh token to the refresh endpoint only, so it is not
        # sent (and can't leak) on every request the way the access token is.
        path="/api/v1/auth/refresh",
    )


def clear_auth_cookies(response: Response) -> None:
    """Remove the auth cookies (logout). Must mirror path/domain to delete."""
    response.delete_cookie(
        ACCESS_COOKIE, domain=settings.cookie_domain, path="/",
        samesite=settings.cookie_samesite, secure=_secure(), httponly=True,
    )
    response.delete_cookie(
        REFRESH_COOKIE, domain=settings.cookie_domain, path="/api/v1/auth/refresh",
        samesite=settings.cookie_samesite, secure=_secure(), httponly=True,
    )
