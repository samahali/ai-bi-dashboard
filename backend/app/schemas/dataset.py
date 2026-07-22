"""
Dataset Pydantic schemas.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    is_public: bool = False


class DatasetUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    is_public: bool | None = None


class ColumnMeta(BaseModel):
    type: str
    nullable: bool
    sample_values: list[Any] = []


class DatasetResponse(BaseModel):
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
    tables_metadata: dict[str, Any] | None = None       # multi-sheet Excel: per-table metadata
    table_relationships: list[dict[str, Any]] | None = None  # detected likely joins
    is_public: bool
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DatasetPreviewResponse(BaseModel):
    id: int
    columns: list[str]
    data: list[list[Any]]
    row_count: int
    total_rows: int


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int


class PaginatedDatasets(BaseModel):
    data: list[DatasetResponse]
    pagination: PaginationMeta
