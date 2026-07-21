"""
Insight service — fetches and manages AI-detected insights.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.models import Dataset, Insight
from app.schemas.insight import InsightResponse


class InsightService:
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
        # Verify dataset access
        ds_result = await self.db.execute(
            select(Dataset).where(Dataset.id == dataset_id, Dataset.deleted_at.is_(None))
        )
        dataset = ds_result.scalar_one_or_none()
        if not dataset:
            raise NotFoundError("Dataset not found.")
        if dataset.user_id != user_id:
            raise ForbiddenError()

        stmt = select(Insight).where(
            Insight.dataset_id == dataset_id,
            Insight.is_dismissed == False,
        )
        if insight_type:
            stmt = stmt.where(Insight.insight_type == insight_type)
        if severity:
            stmt = stmt.where(Insight.severity == severity)

        stmt = stmt.order_by(Insight.created_at.desc()).limit(limit)
        result = await self.db.execute(stmt)
        return [InsightResponse.model_validate(i) for i in result.scalars().all()]

    async def dismiss(self, insight_id: int, user_id: int) -> InsightResponse:
        result = await self.db.execute(select(Insight).where(Insight.id == insight_id))
        insight = result.scalar_one_or_none()
        if not insight:
            raise NotFoundError("Insight not found.")
        if insight.user_id != user_id:
            raise ForbiddenError()

        insight.is_dismissed = True
        insight.dismissed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(insight)
        return InsightResponse.model_validate(insight)
