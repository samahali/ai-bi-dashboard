"""
Dataset service — CRUD and preview operations.
"""
import math
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.db.models import Dataset
from app.schemas.dataset import (
    DatasetPreviewResponse,
    DatasetResponse,
    DatasetUpdate,
    PaginatedDatasets,
    PaginationMeta,
)
from app.utils.file_parser import FileParser


class DatasetService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_datasets(
        self, user_id: int, page: int, limit: int, search: str | None
    ) -> PaginatedDatasets:
        query = select(Dataset).where(Dataset.user_id == user_id, Dataset.deleted_at.is_(None))
        if search:
            query = query.where(Dataset.name.ilike(f"%{search}%"))

        total_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar_one()

        query = query.order_by(Dataset.created_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await self.db.execute(query)
        datasets = result.scalars().all()

        return PaginatedDatasets(
            data=[DatasetResponse.model_validate(d) for d in datasets],
            pagination=PaginationMeta(
                page=page,
                limit=limit,
                total=total,
                total_pages=math.ceil(total / limit) if total else 0,
            ),
        )

    async def get_dataset(self, dataset_id: int, user_id: int) -> DatasetResponse:
        dataset = await self._get_owned(dataset_id, user_id)
        return DatasetResponse.model_validate(dataset)

    async def preview_dataset(
        self, dataset_id: int, user_id: int, rows: int
    ) -> DatasetPreviewResponse:
        dataset = await self._get_owned(dataset_id, user_id)
        parser = FileParser(self.db)
        df = parser.get_dataframe(dataset.file_path, dataset.file_type)
        preview = df.head(rows)

        return DatasetPreviewResponse(
            id=dataset.id,
            columns=list(preview.columns),
            data=preview.values.tolist(),
            row_count=len(preview),
            total_rows=dataset.row_count or len(df),
        )

    async def update_dataset(
        self, dataset_id: int, user_id: int, payload: DatasetUpdate
    ) -> DatasetResponse:
        dataset = await self._get_owned(dataset_id, user_id)
        for field, value in payload.model_dump(exclude_none=True).items():
            setattr(dataset, field, value)
        await self.db.commit()
        await self.db.refresh(dataset)
        return DatasetResponse.model_validate(dataset)

    async def delete_dataset(self, dataset_id: int, user_id: int) -> None:
        from datetime import datetime, timezone
        dataset = await self._get_owned(dataset_id, user_id)
        dataset.deleted_at = datetime.now(timezone.utc)
        await self.db.commit()

        from app.ai.rag_store import SchemaRAGStore
        SchemaRAGStore().delete_dataset_schema(dataset_id)

    async def _get_owned(self, dataset_id: int, user_id: int) -> Dataset:
        result = await self.db.execute(
            select(Dataset).where(Dataset.id == dataset_id, Dataset.deleted_at.is_(None))
        )
        dataset = result.scalar_one_or_none()
        if not dataset:
            raise NotFoundError("Dataset not found.")
        if dataset.user_id != user_id:
            raise ForbiddenError()
        return dataset
