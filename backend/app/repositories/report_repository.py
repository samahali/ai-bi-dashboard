"""
Report repository — raw persistence for Report rows.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Report


class ReportRepository:
    """DB access for creating and listing reports."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def create(self, **fields) -> Report:
        """Instantiate and stage a new Report row (caller flushes/commits)."""
        report = Report(**fields)
        self.db.add(report)
        return report

    async def list_for_user(self, user_id: int) -> list[Report]:
        """List all reports owned by the user, newest first."""
        result = await self.db.execute(
            select(Report)
            .where(Report.user_id == user_id)
            .order_by(Report.created_at.desc())
        )
        return list(result.scalars().all())
