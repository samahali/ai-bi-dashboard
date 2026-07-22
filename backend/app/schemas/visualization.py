"""
Visualization Pydantic schemas.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class VisualizationCreate(BaseModel):
    """Request body for creating a chart from a query's results."""

    query_id: int
    chart_type: Literal["line", "bar", "pie", "scatter", "area"]
    title: str | None = Field(None, max_length=255)
    x_axis: str | None = None
    y_axis: str | None = None
    config: dict[str, Any] | None = None


class VisualizationUpdate(BaseModel):
    """Request body for partially updating a saved visualization."""

    title: str | None = Field(None, max_length=255)
    config: dict[str, Any] | None = None
    is_saved: bool | None = None


class VisualizationResponse(BaseModel):
    """Full visualization record returned by the visualizations API."""

    id: int
    query_id: int
    user_id: int
    chart_type: str
    title: str | None
    x_axis: str | None
    y_axis: str | None
    config: dict[str, Any] | None
    is_saved: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
