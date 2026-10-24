import enum
from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, generate_uuid, utc_now

if TYPE_CHECKING:
    from backend.app.models.user import User
    from backend.app.models.repository import Repository
    from backend.app.models.audit import AuditEvent


class WorkspaceRole(str, enum.Enum):
    OWNER = "Owner"
    ADMIN = "Admin"
    MEMBER = "Member"


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="owned_workspaces")
    memberships: Mapped[List["WorkspaceMembership"]] = relationship("WorkspaceMembership", back_populates="workspace", cascade="all, delete-orphan")
    repositories: Mapped[List["Repository"]] = relationship("Repository", back_populates="workspace", cascade="all, delete-orphan")
    audit_events: Mapped[List["AuditEvent"]] = relationship("AuditEvent", back_populates="workspace", cascade="all, delete-orphan")


class WorkspaceMembership(Base):
    __tablename__ = "workspace_memberships"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_user"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[WorkspaceRole] = mapped_column(Enum(WorkspaceRole), default=WorkspaceRole.MEMBER, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace", back_populates="memberships")
    user: Mapped["User"] = relationship("User", back_populates="memberships")
