"""
Shared "fetch owned row or 404/403" helper.

Every service that scopes rows to the requesting user (ReportService,
QueryService, DatasetService, VisualizationService, InsightService)
re-implemented the same fetch-by-id → NotFoundError-if-missing →
ForbiddenError-if-not-owned logic. This is the single implementation they
all call into instead.

Deliberately a standalone async function rather than a base-service class
hierarchy: there are only 5 call sites and no other shared state/behavior
between the services, so inheritance would add indirection without buying
anything.
"""

from typing import TypeVar

from sqlalchemy import ColumnExpressionArgument, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError

ModelT = TypeVar("ModelT")


async def get_owned(
    db: AsyncSession,
    model: type[ModelT],
    id_value: int,
    user_id: int,
    *,
    extra_filters: tuple[ColumnExpressionArgument[bool], ...] = (),
    not_found_msg: str | None = None,
) -> ModelT:
    """
    Fetch a single `model` row by primary key, scoped to `user_id`.

    Raises NotFoundError (404) if no row matches `id_value` (and any
    `extra_filters`, e.g. a soft-delete guard like `Dataset.deleted_at.is_(None)`).
    Raises ForbiddenError (403) if the row exists but belongs to a
    different user.
    """
    stmt = select(model).where(model.id == id_value, *extra_filters)
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if not row:
        raise NotFoundError(not_found_msg or "Resource not found.")
    if row.user_id != user_id:
        raise ForbiddenError()
    return row
