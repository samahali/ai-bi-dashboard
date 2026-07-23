"""
Dataset ORM model.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base

if TYPE_CHECKING:
    from app.db.models.insight import Insight
    from app.db.models.query import Query
    from app.db.models.report import Report
    from app.db.models.user import User


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # csv | excel | json
    file_size: Mapped[int | None] = mapped_column(Integer)  # bytes
    row_count: Mapped[int | None] = mapped_column(Integer)  # primary table
    column_count: Mapped[int | None] = mapped_column(Integer)  # primary table
    columns_metadata: Mapped[dict | None] = mapped_column(
        JSON
    )  # primary table: {col: {type, nullable, samples}}
    # Multi-table (Excel multi-sheet): per-table metadata keyed by sanitized
    # table name. NULL for datasets parsed before this feature — treated as a
    # single table synthesized from columns_metadata + file_type (see
    # dataset_tables() helper). CSV/JSON always have exactly one entry ("data").
    tables_metadata: Mapped[dict | None] = mapped_column(
        JSON
    )  # {table: {original_name, row_count, column_count, columns, sheet_index}}
    table_relationships: Mapped[list | None] = mapped_column(
        JSON
    )  # [{from_table, to_table, column, confidence}]
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="uploaded", nullable=False
    )  # uploaded|processing|ready|error
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="datasets")
    queries: Mapped[list["Query"]] = relationship(
        "Query", back_populates="dataset", cascade="all, delete-orphan"
    )
    reports: Mapped[list["Report"]] = relationship(
        "Report", back_populates="dataset", cascade="all, delete-orphan"
    )
    insights: Mapped[list["Insight"]] = relationship(
        "Insight", back_populates="dataset", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_datasets_user_id", "user_id"),
        Index("idx_datasets_status", "status"),
        Index("idx_datasets_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Dataset id={self.id} name={self.name!r} status={self.status!r}>"
