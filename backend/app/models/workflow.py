from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, generate_uuid, utc_now

if TYPE_CHECKING:
    from backend.app.models.repository import Repository
    from backend.app.models.failure import Failure


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    __table_args__ = (
        UniqueConstraint("repository_id", "external_run_id", name="uq_repo_external_run"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    repository_id: Mapped[str] = mapped_column(String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    external_run_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    workflow_name: Mapped[str] = mapped_column(String(255), nullable=False)
    branch: Mapped[str] = mapped_column(String(255), nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # queued, in_progress, completed
    conclusion: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # success, failure, cancelled, timed_out
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository", back_populates="workflow_runs")
    failures: Mapped[List["Failure"]] = relationship("Failure", back_populates="workflow_run", cascade="all, delete-orphan")
    log_artifacts: Mapped[List["LogArtifact"]] = relationship("LogArtifact", back_populates="workflow_run", cascade="all, delete-orphan")


class LogArtifact(Base):
    __tablename__ = "log_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workflow_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    storage_reference: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sanitized_excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    workflow_run: Mapped["WorkflowRun"] = relationship("WorkflowRun", back_populates="log_artifacts")
