"""
Datasets router — CRUD and preview.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas import (
    DatasetPreviewResponse,
    DatasetResponse,
    DatasetUpdate,
    PaginatedDatasets,
)
from app.services import DatasetService

router = APIRouter()


@router.get("", response_model=PaginatedDatasets)
async def list_datasets(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: str | None = Query(None, max_length=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's datasets, paginated and optionally name-filtered."""
    return await DatasetService(db).list_datasets(
        user_id=current_user.id, page=page, limit=limit, search=search
    )


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single dataset the current user owns."""
    return await DatasetService(db).get_dataset(dataset_id, current_user.id)


@router.get("/{dataset_id}/preview", response_model=DatasetPreviewResponse)
async def preview_dataset(
    dataset_id: int,
    rows: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    table: str | None = Query(None, max_length=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a page of raw row data for a dataset (or one of its tables)."""
    return await DatasetService(db).preview_dataset(
        dataset_id, current_user.id, rows, offset, table
    )


@router.put("/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(
    dataset_id: int,
    payload: DatasetUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Partially update a dataset's metadata."""
    return await DatasetService(db).update_dataset(dataset_id, current_user.id, payload)


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(
    dataset_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a dataset the current user owns."""
    await DatasetService(db).delete_dataset(dataset_id, current_user.id)
