"""
File upload router — handles raw file uploads before dataset creation.
"""

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas import DatasetResponse
from app.services import FileService

router = APIRouter()


@router.post("/upload", response_model=DatasetResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str | None = Form(None),
    is_public: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a CSV, Excel, or JSON file.
    Triggers async background processing to parse and index the data.
    """
    return await FileService(db).upload_and_create_dataset(
        file=file,
        name=name,
        description=description,
        is_public=is_public,
        user_id=current_user.id,
    )
