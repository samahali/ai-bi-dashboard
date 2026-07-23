"""
Insight ORM model.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
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


class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    dataset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    insight_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # anomaly|trend|outlier|correlation
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    affected_columns: Mapped[list[str] | None] = mapped_column(JSON)
    severity: Mapped[str] = mapped_column(
        String(20), default="medium", nullable=False
    )  # low|medium|high|critical
    confidence_score: Mapped[float | None] = mapped_column(Float)
    insight_metadata: Mapped[dict | None] = mapped_column(JSON)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="insights")
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="insights")

    __table_args__ = (
        Index("idx_insights_user_id", "user_id"),
        Index("idx_insights_dataset_id", "dataset_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<Insight id={self.id} type={self.insight_type!r} "
            f"severity={self.severity!r}>"
        )
