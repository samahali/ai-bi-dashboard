"""
Insight service — fetches and manages AI-detected insights.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Dataset, Insight
from app.schemas import InsightResponse
from app.utils import get_owned


class InsightService:
    """Fetches and manages AI-detected insights for a dataset."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_insights(
        self,
        dataset_id: int,
        user_id: int,
        insight_type: str | None,
        severity: str | None,
        limit: int,
    ) -> list[InsightResponse]:
        """List active (non-dismissed) insights for a dataset the user owns."""
        # Verify dataset access
        await get_owned(
            self.db,
            Dataset,
            dataset_id,
            user_id,
            extra_filters=(Dataset.deleted_at.is_(None),),
            not_found_msg="Dataset not found.",
        )

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
        return [InsightResponse.model_validate(i) for i in result.scalars().all()]

    async def dismiss(self, insight_id: int, user_id: int) -> InsightResponse:
        """Mark an insight the user owns as dismissed."""
        insight = await get_owned(
            self.db, Insight, insight_id, user_id, not_found_msg="Insight not found."
        )

        insight.is_dismissed = True
        insight.dismissed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(insight)
        return InsightResponse.model_validate(insight)
