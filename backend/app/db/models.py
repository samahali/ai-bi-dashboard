"""
SQLAlchemy ORM models.
Each model maps directly to a PostgreSQL table.
"""
from datetime import datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
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
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# ──────────────────────────────────────────────────────────────────
# User
# ──────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    datasets: Mapped[list["Dataset"]] = relationship("Dataset", back_populates="user", cascade="all, delete-orphan")
    queries: Mapped[list["Query"]] = relationship("Query", back_populates="user", cascade="all, delete-orphan")
    reports: Mapped[list["Report"]] = relationship("Report", back_populates="user", cascade="all, delete-orphan")
    insights: Mapped[list["Insight"]] = relationship("Insight", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"


# ──────────────────────────────────────────────────────────────────
# Dataset
# ──────────────────────────────────────────────────────────────────
class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)   # csv | excel | json
    file_size: Mapped[int | None] = mapped_column(Integer)               # bytes
    row_count: Mapped[int | None] = mapped_column(Integer)
    column_count: Mapped[int | None] = mapped_column(Integer)
    columns_metadata: Mapped[dict | None] = mapped_column(JSON)          # {col: {type, nullable, samples}}
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="uploaded", nullable=False)  # uploaded|processing|ready|error
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="datasets")
    queries: Mapped[list["Query"]] = relationship("Query", back_populates="dataset", cascade="all, delete-orphan")
    reports: Mapped[list["Report"]] = relationship("Report", back_populates="dataset", cascade="all, delete-orphan")
    insights: Mapped[list["Insight"]] = relationship("Insight", back_populates="dataset", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_datasets_user_id", "user_id"),
        Index("idx_datasets_status", "status"),
        Index("idx_datasets_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Dataset id={self.id} name={self.name!r} status={self.status!r}>"


# ──────────────────────────────────────────────────────────────────
# Query
# ──────────────────────────────────────────────────────────────────
class Query(Base):
    __tablename__ = "queries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    dataset_id: Mapped[int] = mapped_column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    generated_sql: Mapped[str | None] = mapped_column(Text)
    results: Mapped[list | None] = mapped_column(JSON)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer)
    row_count: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending|success|error
    error_message: Mapped[str | None] = mapped_column(Text)
    ai_model_used: Mapped[str | None] = mapped_column(String(50))
    confidence_score: Mapped[float | None] = mapped_column(Float)
    visualization_suggestion: Mapped[str | None] = mapped_column(String(20))  # bar|line|pie|scatter|table
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="queries")
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="queries")
    visualizations: Mapped[list["Visualization"]] = relationship("Visualization", back_populates="query", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_queries_user_id", "user_id"),
        Index("idx_queries_dataset_id", "dataset_id"),
        Index("idx_queries_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Query id={self.id} status={self.status!r}>"


# ──────────────────────────────────────────────────────────────────
# Visualization
# ──────────────────────────────────────────────────────────────────
class Visualization(Base):
    __tablename__ = "visualizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    query_id: Mapped[int] = mapped_column(Integer, ForeignKey("queries.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    chart_type: Mapped[str] = mapped_column(String(50), nullable=False)  # line|bar|pie|scatter|area
    title: Mapped[str | None] = mapped_column(String(255))
    config: Mapped[dict | None] = mapped_column(JSON)                    # Recharts config
    x_axis: Mapped[str | None] = mapped_column(String(100))
    y_axis: Mapped[str | None] = mapped_column(String(100))
    is_saved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    query: Mapped["Query"] = relationship("Query", back_populates="visualizations")

    def __repr__(self) -> str:
        return f"<Visualization id={self.id} type={self.chart_type!r}>"


# ──────────────────────────────────────────────────────────────────
# Report
# ──────────────────────────────────────────────────────────────────
class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    dataset_id: Mapped[int] = mapped_column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    query_ids: Mapped[list[int] | None] = mapped_column(JSON)
    visualization_ids: Mapped[list[int] | None] = mapped_column(JSON)
    ai_insights: Mapped[str | None] = mapped_column(Text)
    pdf_path: Mapped[str | None] = mapped_column(String(500))
    file_size: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    downloaded_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="reports")
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="reports")

    __table_args__ = (
        Index("idx_reports_user_id", "user_id"),
        Index("idx_reports_dataset_id", "dataset_id"),
    )

    def __repr__(self) -> str:
        return f"<Report id={self.id} title={self.title!r}>"


# ──────────────────────────────────────────────────────────────────
# Insight
# ──────────────────────────────────────────────────────────────────
class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    dataset_id: Mapped[int] = mapped_column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    insight_type: Mapped[str] = mapped_column(String(50), nullable=False)  # anomaly|trend|outlier|correlation
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    affected_columns: Mapped[list[str] | None] = mapped_column(JSON)
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)  # low|medium|high|critical
    confidence_score: Mapped[float | None] = mapped_column(Float)
    insight_metadata: Mapped[dict | None] = mapped_column(JSON)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="insights")
    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="insights")

    __table_args__ = (
        Index("idx_insights_user_id", "user_id"),
        Index("idx_insights_dataset_id", "dataset_id"),
    )

    def __repr__(self) -> str:
        return f"<Insight id={self.id} type={self.insight_type!r} severity={self.severity!r}>"


# ──────────────────────────────────────────────────────────────────
# RefreshToken
# ──────────────────────────────────────────────────────────────────
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    @property
    def is_valid(self) -> bool:
        from datetime import timezone
        return self.revoked_at is None and self.expires_at > datetime.now(timezone.utc)

    def __repr__(self) -> str:
        return f"<RefreshToken id={self.id} user_id={self.user_id}>"
