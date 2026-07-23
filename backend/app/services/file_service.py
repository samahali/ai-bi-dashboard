"""
File upload service — validates, stores, and triggers async parsing.
"""

import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core import FileTooLargeError, InvalidFileTypeError
from app.repositories import FileRepository
from app.schemas import DatasetResponse
from app.utils import FileParser


class FileService:
    """Validates, stores uploaded files, and triggers async dataset parsing."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = FileRepository(db)

    async def upload_and_create_dataset(
        self,
        file: UploadFile,
        name: str,
        description: str | None,
        is_public: bool,
        user_id: int,
    ) -> DatasetResponse:
        """Validate and persist an uploaded file, create its Dataset row, and
        kick off background parsing."""
        # ── Sanitize the client-supplied filename ───────────────
        # file.filename is fully attacker-controlled. Take only the basename
        # (Path.name drops any directory components, incl. traversal like
        # ../../) so it can never influence the on-disk path we build below.
        original_name = Path(file.filename or "").name
        if not original_name:
            raise InvalidFileTypeError("A valid filename is required.")

        # ── Validate file type ──────────────────────────────────
        ext = Path(original_name).suffix.lstrip(".").lower()
        if ext not in settings.allowed_file_types_list:
            allowed = ", ".join(settings.allowed_file_types_list)
            raise InvalidFileTypeError(
                f"File type '{ext}' not allowed. Allowed: {allowed}"
            )
        # Internal file_type used by the parser (xlsx → excel). Kept separate
        # from `ext`, which stays the real on-disk extension for the saved file.
        file_type = "excel" if ext == "xlsx" else ext

        # ── Read content into memory (chunked) ──────────────────
        content = await file.read()

        # ── Validate file size ──────────────────────────────────
        if len(content) > settings.max_upload_size_bytes:
            raise FileTooLargeError(
                f"File exceeds {settings.max_upload_size_mb}MB limit."
            )

        # ── Persist to disk ─────────────────────────────────────
        user_dir = Path(settings.upload_dir) / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)

        # On-disk name is built entirely from server-controlled values (a
        # random UUID + the validated extension) — the client filename never
        # touches the path, so directory traversal is structurally impossible.
        safe_filename = f"{uuid.uuid4().hex}.{ext}"
        file_path = (user_dir / safe_filename).resolve()

        # Belt-and-suspenders: ensure the resolved path is still inside the
        # user's upload directory before writing anything.
        if not file_path.is_relative_to(user_dir.resolve()):
            raise InvalidFileTypeError("Invalid file path.")

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        # ── Create Dataset record (status = processing) ─────────
        dataset = self.repo.create_dataset(
            user_id=user_id,
            name=name,
            description=description,
            file_name=original_name,  # sanitized basename, for display only
            file_path=str(file_path),
            file_type=file_type,  # internal type (excel|csv|json)
            file_size=len(content),
            is_public=is_public,
            status="processing",
        )
        self.db.add(dataset)
        await self.db.commit()
        await self.db.refresh(dataset)

        # ── Trigger async parsing (fire-and-forget) ─────────────
        # Uses its own DB session since it outlives this request's session.
        # track() keeps a strong reference so the task can't be GC'd mid-run.
        from app.utils import track

        track(FileParser().parse_and_index(dataset.id, str(file_path), file_type))

        return DatasetResponse.model_validate(dataset)
