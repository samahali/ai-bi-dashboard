"""
Dataset repository — raw persistence for Dataset rows.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Dataset


class DatasetRepository:
    """DB access for datasets: listing, pagination, and mutation."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_paginated(
        self, user_id: int, page: int, limit: int, search: str | None
    ) -> tuple[list[Dataset], int]:
        """Return a page of the user's non-deleted datasets plus the total count."""
        query = select(Dataset).where(
            Dataset.user_id == user_id, Dataset.deleted_at.is_(None)
        )
        if search:
            query = query.where(Dataset.name.ilike(f"%{search}%"))

        total_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = total_result.scalar_one()

        query = (
            query.order_by(Dataset.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total
