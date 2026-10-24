import enum
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, Integer, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, generate_uuid, utc_now

if TYPE_CHECKING:
    from backend.app.models.workflow import WorkflowRun
    from backend.app.models.analysis import Analysis


class FailureCategory(str, enum.Enum):
    DEPENDENCY_INSTALLATION = "dependency_installation"
    COMPILATION_SYNTAX = "compilation_syntax"
    UNIT_TEST = "unit_test"
    LINTING_FORMATTING = "linting_formatting"
    MISSING_ENV_VAR = "missing_env_var"
    CONFIGURATION_ERROR = "configuration_error"
    PERMISSION_ERROR = "permission_error"
    NETWORK_EXTERNAL_SERVICE = "network_external_service"
    RESOURCE_TIMEOUT = "resource_timeout"
    UNKNOWN = "unknown"


class FailureStatus(str, enum.Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    FIX_PROPOSED = "fix_proposed"
    VERIFIED = "verified"
    RESOLVED = "resolved"


class Failure(Base):
    __tablename__ = "failures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workflow_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    failed_job_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="unknown", nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    error_signature: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False, index=True)

    # Relationships
    workflow_run: Mapped["WorkflowRun"] = relationship("WorkflowRun", back_populates="failures")
    analyses: Mapped[List["Analysis"]] = relationship("Analysis", back_populates="failure", cascade="all, delete-orphan")
