"""
Query service — orchestrates the Text-to-SQL AI flow.
"""
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DatasetNotReadyError, ForbiddenError, NotFoundError
from app.db.models import Dataset, Query
from app.db.session import AsyncSessionLocal
from app.schemas.query import QueryCreate, QueryResponse, QueryStatusResponse


class QueryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_query(self, payload: QueryCreate, user_id: int) -> QueryStatusResponse:
        # Verify dataset ownership and readiness
        result = await self.db.execute(
            select(Dataset).where(Dataset.id == payload.dataset_id, Dataset.deleted_at.is_(None))
        )
        dataset = result.scalar_one_or_none()
        if not dataset:
            raise NotFoundError("Dataset not found.")
        if dataset.user_id != user_id:
            raise ForbiddenError()
        if dataset.status != "ready":
            raise DatasetNotReadyError()

        query = Query(
            user_id=user_id,
            dataset_id=payload.dataset_id,
            question=payload.question,
            status="pending",
            ai_model_used=payload.ai_model,
        )
        self.db.add(query)
        await self.db.commit()
        await self.db.refresh(query)

        # Fire-and-forget: run AI agent in background
        asyncio.create_task(self._execute_query(query.id, dataset, payload))

        return QueryStatusResponse(
            id=query.id,
            status="pending",
            message="Your question is being processed. Poll GET /queries/{id} for results.",
        )

    async def get_query(self, query_id: int, user_id: int) -> QueryResponse:
        query = await self._get_owned(query_id, user_id)
        return QueryResponse.model_validate(query)

    async def list_queries(
        self, user_id: int, dataset_id: int | None, page: int, limit: int
    ) -> list[QueryResponse]:
        stmt = select(Query).where(Query.user_id == user_id)
        if dataset_id:
            stmt = stmt.where(Query.dataset_id == dataset_id)
        stmt = stmt.order_by(Query.created_at.desc()).offset((page - 1) * limit).limit(limit)
        result = await self.db.execute(stmt)
        return [QueryResponse.model_validate(q) for q in result.scalars().all()]

    async def delete_query(self, query_id: int, user_id: int) -> None:
        query = await self._get_owned(query_id, user_id)
        await self.db.delete(query)
        await self.db.commit()

    async def _execute_query(self, query_id: int, dataset: Dataset, payload: QueryCreate) -> None:
        """
        Background task: run the AI agent and update the query record.
        Opens its own DB session since the request session that spawned it
        may already be closed by the time this runs.
        """
        import time
        from app.ai.agent import BIAgent

        start = time.perf_counter()

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Query).where(Query.id == query_id))
            query = result.scalar_one_or_none()
            if not query:
                return

            try:
                agent = BIAgent(provider=payload.ai_model)
                response = await agent.process_question(
                    question=payload.question,
                    dataset=dataset,
                )

                query.generated_sql = response.get("sql")
                query.results = response.get("results")
                query.row_count = len(response.get("results") or [])
                query.confidence_score = response.get("confidence_score")
                query.visualization_suggestion = response.get("visualization_suggestion")
                query.status = "success"
                query.executed_at = datetime.now(timezone.utc)

            except Exception as exc:
                query.status = "error"
                query.error_message = str(exc)

            finally:
                query.execution_time_ms = round((time.perf_counter() - start) * 1000)
                await db.commit()

    async def _get_owned(self, query_id: int, user_id: int) -> Query:
        result = await self.db.execute(select(Query).where(Query.id == query_id))
        query = result.scalar_one_or_none()
        if not query:
            raise NotFoundError("Query not found.")
        if query.user_id != user_id:
            raise ForbiddenError()
        return query
