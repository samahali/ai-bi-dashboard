"""
Insights router — AI-detected anomalies, trends, and recommendations.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.insight import InsightResponse
from app.services.insight_service import InsightService

router = APIRouter()


@router.get("/{dataset_id}", response_model=list[InsightResponse])
async def get_insights(
    dataset_id: int,
    insight_type: str | None = Query(None),
    severity: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await InsightService(db).get_insights(
        dataset_id=dataset_id,
        user_id=current_user.id,
        insight_type=insight_type,
        severity=severity,
        limit=limit,
    )


@router.post("/{insight_id}/dismiss", response_model=InsightResponse)
async def dismiss_insight(
    insight_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await InsightService(db).dismiss(insight_id, current_user.id)
