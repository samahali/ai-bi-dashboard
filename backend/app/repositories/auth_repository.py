"""
Auth repository — raw persistence for User and RefreshToken rows.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RefreshToken, User


class AuthRepository:
    """DB access for user accounts and refresh tokens."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_username_or_email(self, username: str, email: str) -> User | None:
        """Find an existing user matching either the given username or email."""
        result = await self.db.execute(
            select(User).where((User.email == email) | (User.username == username))
        )
        return result.scalar_one_or_none()

    async def get_active_by_username(self, username: str) -> User | None:
        """Find an active user by username, or None if inactive/missing."""
        result = await self.db.execute(
            select(User).where(User.username == username, User.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    def create_user(self, **fields) -> User:
        """Instantiate and stage a new User row (caller flushes/commits)."""
        user = User(**fields)
        self.db.add(user)
        return user

    async def get_valid_refresh_token(self, token_hash: str) -> RefreshToken | None:
        """Find a non-revoked refresh token row by its hash."""
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_active_refresh_tokens(self, user_id: int) -> list[RefreshToken]:
        """List a user's non-revoked refresh tokens."""
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
        )
        return list(result.scalars().all())

    def store_refresh_token(
        self, user_id: int, token_hash: str, expires_at: datetime
    ) -> RefreshToken:
        """Stage a new refresh token row (caller flushes/commits)."""
        rt = RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self.db.add(rt)
        return rt
