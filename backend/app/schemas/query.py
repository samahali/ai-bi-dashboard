"""
Query Pydantic schemas.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class QueryCreate(BaseModel):
    """Request body for asking a natural-language question against a dataset."""

    dataset_id: int
    question: str = Field(..., min_length=3, max_length=2000)
    ai_model: Literal["granite", "openai"] = "granite"


class QueryResponse(BaseModel):
    """Full query record including generated SQL, results, and status."""

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
    """Lightweight status poll response for an in-progress query."""

    id: int
    status: str
    message: str
