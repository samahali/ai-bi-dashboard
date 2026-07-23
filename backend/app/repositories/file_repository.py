"""
File repository — raw persistence for the Dataset row created on upload.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Dataset


class FileRepository:
    """DB access for creating a Dataset row from an uploaded file."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def create_dataset(self, **fields) -> Dataset:
        """Instantiate and stage a new Dataset row (caller flushes/commits)."""
        dataset = Dataset(**fields)
        self.db.add(dataset)
        return dataset
