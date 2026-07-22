"""
Report service — generates professional PDF reports from queries + visualizations.
"""

from pathlib import Path

from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import NotFoundError
from app.db.models import Dataset, Insight, Query, Report
from app.db.session import AsyncSessionLocal
from app.schemas import ReportCreate, ReportResponse, ReportStatusResponse
from app.utils import get_owned, track


class ReportService:
    """Generates PDF reports from a dataset's queries and/or insights."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_report(
        self, payload: ReportCreate, user_id: int
    ) -> ReportStatusResponse:
        """Create a pending report and kick off PDF generation in the background."""
        await get_owned(
            self.db,
            Dataset,
            payload.dataset_id,
            user_id,
            extra_filters=(Dataset.deleted_at.is_(None),),
            not_found_msg="Dataset not found.",
        )

        report = Report(
            user_id=user_id,
            dataset_id=payload.dataset_id,
            title=payload.title,
            description=payload.description,
            query_ids=payload.query_ids,
            visualization_ids=payload.visualization_ids,
            status="pending",
        )
        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)

        track(self._generate_pdf(report.id, payload))

        return ReportStatusResponse(
            id=report.id,
            status="pending",
            message="Report generation started. Poll GET /reports/{id} for status.",
        )

    async def get_report(self, report_id: int, user_id: int) -> ReportResponse:
        """Fetch a single report the user owns."""
        report = await self._get_owned(report_id, user_id)
        return ReportResponse.model_validate(report)

    async def get_pdf_path(self, report_id: int, user_id: int) -> str:
        """Return the on-disk PDF path for a report, bumping its download count."""
        report = await self._get_owned(report_id, user_id)
        if not report.pdf_path or not Path(report.pdf_path).exists():
            raise NotFoundError("PDF not yet generated. Check report status.")
        report.downloaded_count += 1
        await self.db.commit()
        return report.pdf_path

    async def list_reports(self, user_id: int) -> list[ReportResponse]:
        """List all reports owned by the user, newest first."""
        result = await self.db.execute(
            select(Report)
            .where(Report.user_id == user_id)
            .order_by(Report.created_at.desc())
        )
        return [ReportResponse.model_validate(r) for r in result.scalars().all()]

    async def delete_report(self, report_id: int, user_id: int) -> None:
        """Delete a report the user owns and its PDF file, if any."""
        report = await self._get_owned(report_id, user_id)
        # Clean up PDF file if it exists
        if report.pdf_path:
            path = Path(report.pdf_path)
            if path.exists():
                path.unlink()
        await self.db.delete(report)
        await self.db.commit()

    async def _generate_pdf(self, report_id: int, payload: ReportCreate) -> None:
        """
        Background task: generate the PDF and update the report record.
        Opens its own DB session since the request session that spawned it
        may already be closed by the time this runs.
        """
        from app.utils import PDFGenerator

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Report).where(Report.id == report_id))
            report = result.scalar_one_or_none()
            if not report:
                return

            try:
                report.status = "generating"
                await db.commit()

                # Fetch queries — scoped to this report's dataset/owner so a
                # stale or foreign query_id can't leak another dataset's data
                # into the PDF, and silently drops IDs that don't match
                # instead of raising (they may have been deleted since the
                # report was requested).
                queries: list[Query] = []
                if payload.query_ids:
                    q_result = await db.execute(
                        select(Query).where(
                            Query.id.in_(payload.query_ids),
                            Query.dataset_id == payload.dataset_id,
                            Query.user_id == report.user_id,
                        )
                    )
                    queries = list(q_result.scalars().all())

                insights: list[Insight] = []
                if payload.include_insights:
                    # severity is a free-text column (low|medium|high|critical),
                    # not an ordered type — .desc() would sort alphabetically
                    # ("medium" before "critical"), so rank explicitly instead.
                    severity_rank = case(
                        (Insight.severity == "critical", 0),
                        (Insight.severity == "high", 1),
                        (Insight.severity == "medium", 2),
                        (Insight.severity == "low", 3),
                        else_=4,
                    )
                    i_result = await db.execute(
                        select(Insight)
                        .where(
                            Insight.dataset_id == payload.dataset_id,
                            Insight.user_id == report.user_id,
                            Insight.is_dismissed.is_(False),
                        )
                        .order_by(severity_rank, Insight.created_at.desc())
                    )
                    insights = list(i_result.scalars().all())

                if not queries and not insights:
                    raise ValueError(
                        "No content available for this report: the selected "
                        "queries no longer exist and there are no active "
                        "insights for this dataset."
                    )

                # Generate PDF
                generator = PDFGenerator()
                pdf_path = await generator.generate(
                    report_id=report_id,
                    title=payload.title,
                    description=payload.description,
                    queries=queries,
                    insights=insights,
                    output_dir=settings.reports_dir,
                )

                report.pdf_path = pdf_path
                report.file_size = Path(pdf_path).stat().st_size
                report.status = "completed"

            except Exception as exc:
                report.status = "error"
                report.ai_insights = f"Error generating report: {exc}"

            finally:
                await db.commit()

    async def _get_owned(self, report_id: int, user_id: int) -> Report:
        """Fetch a Report row by id, scoped to `user_id` (404/403 via get_owned)."""
        return await get_owned(
            self.db, Report, report_id, user_id, not_found_msg="Report not found."
        )
