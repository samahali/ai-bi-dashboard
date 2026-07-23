"""
Insight repository — raw persistence for Insight rows.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Insight


class InsightRepository:
    """DB access for listing and filtering dataset insights."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_active(
        self,
        dataset_id: int,
        insight_type: str | None,
        severity: str | None,
        limit: int,
    ) -> list[Insight]:
        """List non-dismissed insights for a dataset, newest first."""
        stmt = select(Insight).where(
            Insight.dataset_id == dataset_id,
            Insight.is_dismissed.is_(False),
        )
        if insight_type:
            stmt = stmt.where(Insight.insight_type == insight_type)
        if severity:
            stmt = stmt.where(Insight.severity == severity)

        stmt = stmt.order_by(Insight.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
