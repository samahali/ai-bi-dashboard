"""
Visualization ORM model.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base

if TYPE_CHECKING:
    from app.db.models.query import Query


class Visualization(Base):
    __tablename__ = "visualizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("queries.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    chart_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # line|bar|pie|scatter|area
    title: Mapped[str | None] = mapped_column(String(255))
    config: Mapped[dict | None] = mapped_column(JSON)  # Recharts config
    x_axis: Mapped[str | None] = mapped_column(String(100))
    y_axis: Mapped[str | None] = mapped_column(String(100))
    is_saved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    query: Mapped["Query"] = relationship("Query", back_populates="visualizations")

    def __repr__(self) -> str:
        return f"<Visualization id={self.id} type={self.chart_type!r}>"
