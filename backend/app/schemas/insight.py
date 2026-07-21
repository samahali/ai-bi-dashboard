"""
Insight Pydantic schemas.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class InsightResponse(BaseModel):
    id: int
    dataset_id: int
    insight_type: str
    title: str
    description: str
    affected_columns: list[str] | None
    severity: str
    confidence_score: float | None
    insight_metadata: dict[str, Any] | None
    is_dismissed: bool
    created_at: datetime
    dismissed_at: datetime | None

    model_config = {"from_attributes": True}
