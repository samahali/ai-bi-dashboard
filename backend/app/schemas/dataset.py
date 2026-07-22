"""
Dataset Pydantic schemas.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DatasetCreate(BaseModel):
    """Request body for registering a new dataset alongside a file upload."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    is_public: bool = False


class DatasetUpdate(BaseModel):
    """Request body for partially updating a dataset's metadata."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    is_public: bool | None = None


class ColumnMeta(BaseModel):
    """Inferred type and sample values for a single dataset column."""

    type: str
    nullable: bool
    sample_values: list[Any] = []


class DatasetResponse(BaseModel):
    """Full dataset representation returned by the datasets API."""

    id: int
    user_id: int
    name: str
    description: str | None
    file_name: str
    file_type: str
    file_size: int | None
    row_count: int | None
    column_count: int | None
    columns_metadata: dict[str, Any] | None
    tables_metadata: dict[str, Any] | None = (
        None  # multi-sheet Excel: per-table metadata
    )
    table_relationships: list[dict[str, Any]] | None = None  # detected likely joins
    is_public: bool
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DatasetPreviewResponse(BaseModel):
    """A page of raw row data for previewing a dataset (or one of its tables)."""

    id: int
    table: str | None = None
    columns: list[str]
    data: list[list[Any]]
    row_count: int
    total_rows: int
    offset: int = 0


class PaginationMeta(BaseModel):
    """Page/limit/total bookkeeping for a paginated list response."""

    page: int
    limit: int
    total: int
    total_pages: int


class PaginatedDatasets(BaseModel):
    """A page of datasets plus pagination metadata."""

    data: list[DatasetResponse]
    pagination: PaginationMeta
