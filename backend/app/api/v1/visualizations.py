"""
Visualizations router.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.visualization import VisualizationCreate, VisualizationResponse, VisualizationUpdate
from app.services.visualization_service import VisualizationService

router = APIRouter()


@router.post("", response_model=VisualizationResponse, status_code=201)
async def create_visualization(
    payload: VisualizationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await VisualizationService(db).create(payload, current_user.id)


@router.get("", response_model=list[VisualizationResponse])
async def list_visualizations(
    query_id: int = Query(..., description="List saved visualizations for this query."),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await VisualizationService(db).list_for_query(query_id, current_user.id)


@router.get("/{viz_id}", response_model=VisualizationResponse)
async def get_visualization(
    viz_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await VisualizationService(db).get(viz_id, current_user.id)


@router.put("/{viz_id}", response_model=VisualizationResponse)
async def update_visualization(
    viz_id: int,
    payload: VisualizationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await VisualizationService(db).update(viz_id, current_user.id, payload)


@router.delete("/{viz_id}", status_code=204)
async def delete_visualization(
    viz_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await VisualizationService(db).delete(viz_id, current_user.id)
