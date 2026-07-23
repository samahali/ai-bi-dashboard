"""
Queries router — natural language to SQL execution.
"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import limiter
from app.db.models import User
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas import QueryCreate, QueryResponse, QueryStatusResponse
from app.services import QueryService

router = APIRouter()


@router.post("", response_model=QueryStatusResponse, status_code=202)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def create_query(
    request: Request,
    payload: QueryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a natural language question for AI-powered SQL execution.
    Returns immediately with a query ID — poll GET /queries/{id} for results.
    """
    return await QueryService(db).create_query(payload, current_user.id)


@router.get("/{query_id}", response_model=QueryResponse)
async def get_query(
    query_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single query (including status, SQL, and results) the user owns."""
    return await QueryService(db).get_query(query_id, current_user.id)


@router.get("", response_model=list[QueryResponse])
async def list_queries(
    dataset_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's queries, optionally filtered to one dataset."""
    return await QueryService(db).list_queries(current_user.id, dataset_id, page, limit)


@router.delete("/{query_id}", status_code=204)
async def delete_query(
    query_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a query the current user owns."""
    await QueryService(db).delete_query(query_id, current_user.id)
