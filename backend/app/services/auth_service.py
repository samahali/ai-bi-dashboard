"""
Auth service — register, login, logout, token refresh.
"""

import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import (
    ConflictError,
    UnauthorizedError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.repositories import AuthRepository
from app.schemas import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)


class AuthService:
    """Handles registration, login, logout, and refresh-token exchange."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AuthRepository(db)

    async def register(self, payload: RegisterRequest) -> AuthResponse:
        """Create a new user account and issue an initial token pair."""
        existing = await self.repo.get_by_username_or_email(
            payload.username, payload.email
        )
        if existing:
            raise ConflictError("Username or email already registered.")

        user = self.repo.create_user(
            username=payload.username,
            email=payload.email,
            password_hash=hash_password(payload.password),
            first_name=payload.first_name,
            last_name=payload.last_name,
        )
        await self.db.flush()  # get user.id before commit

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)
        await self._store_refresh_token(user.id, refresh_token)
        await self.db.commit()
        await self.db.refresh(user)

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserResponse.model_validate(user),
        )

    async def login(self, payload: LoginRequest) -> AuthResponse:
        """Verify credentials and issue a new access/refresh token pair."""
        user = await self.repo.get_active_by_username(payload.username)

        if not user or not verify_password(payload.password, user.password_hash):
            raise UnauthorizedError("Invalid username or password.")

        # Update last login
        user.last_login = datetime.now(timezone.utc)

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)
        await self._store_refresh_token(user.id, refresh_token)
        await self.db.commit()
        await self.db.refresh(user)

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserResponse.model_validate(user),
        )

    async def refresh(self, token: str) -> TokenResponse:
        """Exchange a valid, non-revoked refresh token for a new access token."""
        try:
            payload = decode_token(token)
            if payload.get("type") != "refresh":
                raise UnauthorizedError("Invalid token type.")
            user_id = int(payload["sub"])
        except Exception as e:
            raise UnauthorizedError("Invalid or expired refresh token.") from e

        # Verify token is stored and not revoked
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        stored = await self.repo.get_valid_refresh_token(token_hash)
        if not stored or not stored.is_valid:
            raise UnauthorizedError("Refresh token is invalid or expired.")

        new_access = create_access_token(user_id)
        return TokenResponse(
            access_token=new_access,
            refresh_token=token,
            expires_in=settings.access_token_expire_minutes * 60,
        )

    async def logout(self, user_id: int) -> None:
        """Revoke all refresh tokens for this user."""
        for token in await self.repo.get_active_refresh_tokens(user_id):
            token.revoked_at = datetime.now(timezone.utc)
        await self.db.commit()

    async def _store_refresh_token(self, user_id: int, token: str) -> None:
        """Persist the hash (never the raw token) of an issued refresh token."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        )
        self.repo.store_refresh_token(user_id, token_hash, expires_at)
