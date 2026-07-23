"""
Query ORM model.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
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
    from app.db.models.dataset import Dataset
    from app.db.models.user import User
    from app.db.models.visualization import Visualization


class Query(Base):
    __tablename__ = "queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    dataset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    generated_sql: Mapped[str | None] = mapped_column(Text)
    results: Mapped[list | None] = mapped_column(JSON)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer)
    row_count: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending|success|error
    error_message: Mapped[str | None] = mapped_column(Text)
    ai_model_used: Mapped[str | None] = mapped_column(String(50))
    confidence_score: Mapped[float | None] = mapped_column(Float)
    visualization_suggestion: Mapped[str | None] = mapped_column(
        String(20)
    )  # bar|line|pie|scatter|table
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="queries")
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="queries")
    visualizations: Mapped[list["Visualization"]] = relationship(
        "Visualization", back_populates="query", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_queries_user_id", "user_id"),
        Index("idx_queries_dataset_id", "dataset_id"),
        Index("idx_queries_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Query id={self.id} status={self.status!r}>"
