"""
Visualization service.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.models import Query, Visualization
from app.schemas.visualization import VisualizationCreate, VisualizationResponse, VisualizationUpdate


class VisualizationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, payload: VisualizationCreate, user_id: int) -> VisualizationResponse:
        # Verify query ownership
        result = await self.db.execute(select(Query).where(Query.id == payload.query_id))
        query = result.scalar_one_or_none()
        if not query:
            raise NotFoundError("Query not found.")
        if query.user_id != user_id:
            raise ForbiddenError()

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
        result = await self.db.execute(select(Visualization).where(Visualization.id == viz_id))
        viz = result.scalar_one_or_none()
        if not viz:
            raise NotFoundError("Visualization not found.")
        if viz.user_id != user_id:
            raise ForbiddenError()
        return viz
