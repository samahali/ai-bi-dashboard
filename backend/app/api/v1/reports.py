"""
Reports router — PDF report generation and download.
"""
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.report import ReportCreate, ReportResponse, ReportStatusResponse
from app.services.report_service import ReportService

router = APIRouter()


@router.post("", response_model=ReportStatusResponse, status_code=201)
async def create_report(
    payload: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Kick off PDF report generation. Poll GET /reports/{id} for status."""
    return await ReportService(db).create_report(payload, current_user.id)


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ReportService(db).get_report(report_id, current_user.id)


@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream the generated PDF file to the client."""
    pdf_path = await ReportService(db).get_pdf_path(report_id, current_user.id)
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"report_{report_id}.pdf",
    )


@router.get("", response_model=list[ReportResponse])
async def list_reports(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ReportService(db).list_reports(current_user.id)


@router.delete("/{report_id}", status_code=204)
async def delete_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ReportService(db).delete_report(report_id, current_user.id)
