"""
Data-access repositories, re-exported so call sites can do
`from app.repositories import DatasetRepository` instead of importing each module.
"""

from app.repositories.auth_repository import AuthRepository
from app.repositories.dataset_repository import DatasetRepository
from app.repositories.file_repository import FileRepository
from app.repositories.insight_repository import InsightRepository
from app.repositories.query_repository import QueryRepository
from app.repositories.report_repository import ReportRepository
from app.repositories.visualization_repository import VisualizationRepository

__all__ = [
    "AuthRepository",
    "DatasetRepository",
    "FileRepository",
    "InsightRepository",
    "QueryRepository",
    "ReportRepository",
    "VisualizationRepository",
]
