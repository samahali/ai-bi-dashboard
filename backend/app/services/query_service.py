"""
Query service — orchestrates the Text-to-SQL AI flow.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import DatasetNotReadyError
from app.db.models import Dataset, Query
from app.db.session import AsyncSessionLocal
from app.schemas import QueryCreate, QueryResponse, QueryStatusResponse
from app.utils import get_owned, track


class QueryService:
    """Orchestrates the Text-to-SQL AI flow: create, poll, and list queries."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_query(
        self, payload: QueryCreate, user_id: int
    ) -> QueryStatusResponse:
        """Create a pending query and kick off AI processing in the background."""
        dataset = await get_owned(
            self.db,
            Dataset,
            payload.dataset_id,
            user_id,
            extra_filters=(Dataset.deleted_at.is_(None),),
            not_found_msg="Dataset not found.",
        )
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
        track(self._execute_query(query.id, dataset, payload))

        return QueryStatusResponse(
            id=query.id,
            status="pending",
            message="Processing your question. Poll GET /queries/{id} for results.",
        )

    async def get_query(self, query_id: int, user_id: int) -> QueryResponse:
        """Fetch a single query the user owns."""
        query = await self._get_owned(query_id, user_id)
        return QueryResponse.model_validate(query)

    async def list_queries(
        self, user_id: int, dataset_id: int | None, page: int, limit: int
    ) -> list[QueryResponse]:
        """List the user's queries, optionally filtered to one dataset."""
        stmt = select(Query).where(Query.user_id == user_id)
        if dataset_id:
            stmt = stmt.where(Query.dataset_id == dataset_id)
        stmt = (
            stmt.order_by(Query.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [QueryResponse.model_validate(q) for q in result.scalars().all()]

    async def delete_query(self, query_id: int, user_id: int) -> None:
        """Delete a query the user owns."""
        query = await self._get_owned(query_id, user_id)
        await self.db.delete(query)
        await self.db.commit()

    async def _execute_query(
        self, query_id: int, dataset: Dataset, payload: QueryCreate
    ) -> None:
        """
        Background task: run the AI agent and update the query record.
        Opens its own DB session since the request session that spawned it
        may already be closed by the time this runs.
        """
        import time

        from app.ai import BIAgent

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
                query.visualization_suggestion = response.get(
                    "visualization_suggestion"
                )
                # NO_ANSWER: the model determined the question can't be answered
                # from this dataset's schema. Not an execution error — a valid
                # "no answer" outcome, surfaced via error_message for the UI.
                if response.get("no_answer"):
                    query.status = "success"
                    query.error_message = response["no_answer"]
                else:
                    query.status = "success"
                query.executed_at = datetime.now(timezone.utc)

            except Exception as exc:
                query.status = "error"
                query.error_message = str(exc)

            finally:
                query.execution_time_ms = round((time.perf_counter() - start) * 1000)
                await db.commit()

    async def _get_owned(self, query_id: int, user_id: int) -> Query:
        """Fetch a Query row by id, scoped to `user_id` (404/403 via get_owned)."""
        return await get_owned(
            self.db, Query, query_id, user_id, not_found_msg="Query not found."
        )
