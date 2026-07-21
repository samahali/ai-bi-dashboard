"""
Report Pydantic schemas.
"""
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class ReportCreate(BaseModel):
    dataset_id: int
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    query_ids: list[int] = []
    visualization_ids: list[int] = []
    include_insights: bool = True

    @model_validator(mode="after")
    def require_some_content(self) -> "ReportCreate":
        if not self.query_ids and not self.include_insights:
            raise ValueError(
                "A report needs at least one query or include_insights=True — "
                "otherwise the PDF would be empty."
            )
        return self


class ReportResponse(BaseModel):
    id: int
    user_id: int
    dataset_id: int
    title: str
    description: str | None
    query_ids: list[int] | None
    visualization_ids: list[int] | None
    status: str
    pdf_path: str | None
    file_size: int | None
    downloaded_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportStatusResponse(BaseModel):
    id: int
    status: str
    message: str
