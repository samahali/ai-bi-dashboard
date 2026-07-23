"""
Query repository — raw persistence for Query rows.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Query


class QueryRepository:
    """DB access for creating, listing, and updating queries."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def create(self, **fields) -> Query:
        """Instantiate and stage a new Query row (caller flushes/commits)."""
        query = Query(**fields)
        self.db.add(query)
        return query

    async def list_for_user(
        self, user_id: int, dataset_id: int | None, page: int, limit: int
    ) -> list[Query]:
        """List a user's queries, optionally filtered to one dataset."""
        stmt = select(Query).where(Query.user_id == user_id)
        if dataset_id:
            stmt = stmt.where(Query.dataset_id == dataset_id)
        stmt = (
            stmt.order_by(Query.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
