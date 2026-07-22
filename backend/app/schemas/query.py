"""
Query Pydantic schemas.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from typing import Literal


class QueryCreate(BaseModel):
    dataset_id: int
    question: str = Field(..., min_length=3, max_length=2000)
    ai_model: Literal["granite", "openai"] = "granite"


class QueryResponse(BaseModel):
    id: int
    dataset_id: int
    question: str
    generated_sql: str | None
    results: list[dict[str, Any]] | None
    execution_time_ms: int | None
    row_count: int | None
    status: str
    error_message: str | None
    ai_model_used: str | None
    confidence_score: float | None
    visualization_suggestion: str | None
    created_at: datetime
    executed_at: datetime | None

    model_config = {"from_attributes": True}


class QueryStatusResponse(BaseModel):
    id: int
    status: str
    message: str
