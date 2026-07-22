"""
Pydantic request/response schemas, re-exported so call sites can do
`from app.schemas import QueryCreate` instead of importing each module.
"""

from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.dataset import (
    ColumnMeta,
    DatasetCreate,
    DatasetPreviewResponse,
    DatasetResponse,
    DatasetUpdate,
    PaginatedDatasets,
    PaginationMeta,
)
from app.schemas.insight import InsightResponse
from app.schemas.query import QueryCreate, QueryResponse, QueryStatusResponse
from app.schemas.report import ReportCreate, ReportResponse, ReportStatusResponse
from app.schemas.visualization import (
    VisualizationCreate,
    VisualizationResponse,
    VisualizationUpdate,
)

__all__ = [
    "AuthResponse",
    "LoginRequest",
    "RefreshRequest",
    "RegisterRequest",
    "TokenResponse",
    "UserResponse",
    "ColumnMeta",
    "DatasetCreate",
    "DatasetPreviewResponse",
    "DatasetResponse",
    "DatasetUpdate",
    "PaginatedDatasets",
    "PaginationMeta",
    "InsightResponse",
    "QueryCreate",
    "QueryResponse",
    "QueryStatusResponse",
    "ReportCreate",
    "ReportResponse",
    "ReportStatusResponse",
    "VisualizationCreate",
    "VisualizationResponse",
    "VisualizationUpdate",
]
