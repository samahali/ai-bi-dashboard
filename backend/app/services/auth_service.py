"""
Auth service — register, login, logout, token refresh.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.exceptions import ConflictError, UnauthorizedError
from app.db.models import RefreshToken, User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, TokenResponse, UserResponse


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def register(self, payload: RegisterRequest) -> AuthResponse:
        # Check uniqueness
        existing = await self.db.execute(
            select(User).where(
                (User.email == payload.email) | (User.username == payload.username)
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError("Username or email already registered.")

        user = User(
            username=payload.username,
            email=payload.email,
            password_hash=hash_password(payload.password),
            first_name=payload.first_name,
            last_name=payload.last_name,
        )
        self.db.add(user)
        await self.db.flush()   # get user.id before commit

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
        result = await self.db.execute(
            select(User).where(User.username == payload.username, User.is_active == True)
        )
        user = result.scalar_one_or_none()

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
        try:
            payload = decode_token(token)
            if payload.get("type") != "refresh":
                raise UnauthorizedError("Invalid token type.")
            user_id = int(payload["sub"])
        except Exception:
            raise UnauthorizedError("Invalid or expired refresh token.")

        # Verify token is stored and not revoked
        from app.core.auth import hash_password as _hash
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
        )
        stored = result.scalar_one_or_none()
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
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        for token in result.scalars().all():
            token.revoked_at = datetime.now(timezone.utc)
        await self.db.commit()

    async def _store_refresh_token(self, user_id: int, token: str) -> None:
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
        rt = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.db.add(rt)
