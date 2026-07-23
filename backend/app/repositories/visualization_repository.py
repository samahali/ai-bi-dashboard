"""
Visualization repository — raw persistence for Visualization rows.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Visualization


class VisualizationRepository:
    """DB access for creating and listing saved chart visualizations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def create(self, **fields) -> Visualization:
        """Instantiate and stage a new Visualization row (caller flushes/commits)."""
        viz = Visualization(**fields)
        self.db.add(viz)
        return viz

    async def list_for_query(self, query_id: int, user_id: int) -> list[Visualization]:
        """List a user's saved visualizations for one query, newest first."""
        result = await self.db.execute(
            select(Visualization)
            .where(Visualization.query_id == query_id, Visualization.user_id == user_id)
            .order_by(Visualization.created_at.desc())
        )
        return list(result.scalars().all())
