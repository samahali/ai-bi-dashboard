"""
Visualization service.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Query, Visualization
from app.schemas.visualization import (
    VisualizationCreate,
    VisualizationResponse,
    VisualizationUpdate,
)
from app.utils.ownership import get_owned


class VisualizationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, payload: VisualizationCreate, user_id: int
    ) -> VisualizationResponse:
        await get_owned(
            self.db, Query, payload.query_id, user_id, not_found_msg="Query not found."
        )

        viz = Visualization(
            query_id=payload.query_id,
            user_id=user_id,
            chart_type=payload.chart_type,
            title=payload.title,
            x_axis=payload.x_axis,
            y_axis=payload.y_axis,
            config=payload.config,
        )
        self.db.add(viz)
        await self.db.commit()
        await self.db.refresh(viz)
        return VisualizationResponse.model_validate(viz)

    async def get(self, viz_id: int, user_id: int) -> VisualizationResponse:
        viz = await self._get_owned(viz_id, user_id)
        return VisualizationResponse.model_validate(viz)

    async def list_for_query(
        self, query_id: int, user_id: int
    ) -> list[VisualizationResponse]:
        # Verify query ownership first — a query the user doesn't own should
        # 404/403 the same way create() does, rather than silently returning
        # an empty list for someone else's query_id.
        await get_owned(
            self.db, Query, query_id, user_id, not_found_msg="Query not found."
        )

        viz_result = await self.db.execute(
            select(Visualization)
            .where(Visualization.query_id == query_id, Visualization.user_id == user_id)
            .order_by(Visualization.created_at.desc())
        )
        return [
            VisualizationResponse.model_validate(v) for v in viz_result.scalars().all()
        ]

    async def update(
        self, viz_id: int, user_id: int, payload: VisualizationUpdate
    ) -> VisualizationResponse:
        viz = await self._get_owned(viz_id, user_id)
        for field, value in payload.model_dump(exclude_none=True).items():
            setattr(viz, field, value)
        await self.db.commit()
        await self.db.refresh(viz)
        return VisualizationResponse.model_validate(viz)

    async def delete(self, viz_id: int, user_id: int) -> None:
        viz = await self._get_owned(viz_id, user_id)
        await self.db.delete(viz)
        await self.db.commit()

    async def _get_owned(self, viz_id: int, user_id: int) -> Visualization:
        return await get_owned(
            self.db,
            Visualization,
            viz_id,
            user_id,
            not_found_msg="Visualization not found.",
        )
