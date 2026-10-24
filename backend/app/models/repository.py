from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, generate_uuid, utc_now

if TYPE_CHECKING:
    from backend.app.models.workspace import Workspace
    from backend.app.models.workflow import WorkflowRun


class Repository(Base):
    __tablename__ = "repositories"
    __table_args__ = (
        UniqueConstraint("workspace_id", "full_name", name="uq_workspace_repo_fullname"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), default="github", nullable=False)
    external_repository_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)  # e.g. "owner/repo"
    default_branch: Mapped[str] = mapped_column(String(100), default="main", nullable=False)
    installation_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    connection_status: Mapped[str] = mapped_column(String(50), default="connected", nullable=False)  # connected, disconnected
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="repositories")
    workflow_runs: Mapped[List["WorkflowRun"]] = relationship("WorkflowRun", back_populates="repository", cascade="all, delete-orphan")
