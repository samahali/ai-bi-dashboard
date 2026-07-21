"""
JWT token creation and validation.
"""
from datetime import datetime, timedelta, timezone

from jose import jwt
import bcrypt

from app.config import settings


def hash_password(plain: str) -> str:
    if len(plain) > 72:
        plain = plain[:72]
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain.encode(), salt).decode()


def verify_password(plain: str, hashed: str) -> bool:
    if len(plain) > 72:
        plain = plain[:72]
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(subject: str | int) -> str:
    """Create a short-lived JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(subject), "type": "access", "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: str | int) -> str:
    """Create a long-lived JWT refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    payload = {"sub": str(subject), "type": "refresh", "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    Raises JWTError on invalid/expired tokens.
    """
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
