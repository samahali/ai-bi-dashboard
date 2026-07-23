"""
Dataset service — CRUD and preview operations.
"""

import math

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Dataset
from app.repositories import DatasetRepository
from app.schemas import (
    DatasetPreviewResponse,
    DatasetResponse,
    DatasetUpdate,
    PaginatedDatasets,
    PaginationMeta,
)
from app.utils import DEFAULT_TABLE_NAME, FileParser, get_owned


class DatasetService:
    """CRUD and preview operations for datasets."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = DatasetRepository(db)

    async def list_datasets(
        self, user_id: int, page: int, limit: int, search: str | None
    ) -> PaginatedDatasets:
        """List the user's non-deleted datasets, paginated and name-filterable."""
        datasets, total = await self.repo.list_paginated(user_id, page, limit, search)

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
        """Fetch a single dataset the user owns."""
        dataset = await self._get_owned(dataset_id, user_id)
        return DatasetResponse.model_validate(dataset)

    async def preview_dataset(
        self,
        dataset_id: int,
        user_id: int,
        rows: int,
        offset: int = 0,
        table: str | None = None,
    ) -> DatasetPreviewResponse:
        """
        Preview a page of `rows` rows starting at `offset`. For multi-sheet
        Excel datasets, `table` selects which sanitized table name to preview
        (defaults to the primary/first table when omitted); an unknown table
        falls back to the primary one rather than erroring.

        CSV datasets use a true streaming read (`FileParser.read_csv_page`):
        pandas skips the rows before `offset` at the C-parser level and stops
        at `limit`, so paging a large CSV never loads the whole file into
        memory. Excel/JSON have no equivalent chunked-read API in pandas, so
        those fall back to a full read + in-memory slice — acceptable since
        `total_rows` for every table is already known from parse-time
        metadata, so this path never needs a second full read just to count
        rows.
        """
        dataset = await self._get_owned(dataset_id, user_id)
        parser = FileParser()

        if dataset.file_type == "csv":
            selected_name = DEFAULT_TABLE_NAME
            preview = parser.read_csv_page(dataset.file_path, offset, rows)
            total_rows = dataset.row_count
        else:
            frames = parser.get_dataframes(dataset.file_path, dataset.file_type)
            selected_name = table if table in frames else next(iter(frames))
            preview = frames[selected_name].iloc[offset : offset + rows]
            if dataset.tables_metadata and selected_name in dataset.tables_metadata:
                total_rows = dataset.tables_metadata[selected_name]["row_count"]
            else:
                total_rows = len(frames[selected_name])

        return DatasetPreviewResponse(
            id=dataset.id,
            table=selected_name,
            columns=list(preview.columns),
            data=preview.values.tolist(),
            row_count=len(preview),
            total_rows=total_rows,
            offset=offset,
        )

    async def update_dataset(
        self, dataset_id: int, user_id: int, payload: DatasetUpdate
    ) -> DatasetResponse:
        """Partially update a dataset's metadata (name/description/is_public)."""
        dataset = await self._get_owned(dataset_id, user_id)
        for field, value in payload.model_dump(exclude_none=True).items():
            setattr(dataset, field, value)
        await self.db.commit()
        await self.db.refresh(dataset)
        return DatasetResponse.model_validate(dataset)

    async def delete_dataset(self, dataset_id: int, user_id: int) -> None:
        """Soft-delete a dataset the user owns and remove its indexed RAG schema."""
        from datetime import datetime, timezone

        dataset = await self._get_owned(dataset_id, user_id)
        dataset.deleted_at = datetime.now(timezone.utc)
        await self.db.commit()

        from app.ai import SchemaRAGStore

        SchemaRAGStore().delete_dataset_schema(dataset_id)

    async def _get_owned(self, dataset_id: int, user_id: int) -> Dataset:
        """Fetch a non-deleted Dataset row by id, scoped to `user_id`."""
        return await get_owned(
            self.db,
            Dataset,
            dataset_id,
            user_id,
            extra_filters=(Dataset.deleted_at.is_(None),),
            not_found_msg="Dataset not found.",
        )
