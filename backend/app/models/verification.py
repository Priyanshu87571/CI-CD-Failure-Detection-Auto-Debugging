from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, generate_uuid, utc_now

if TYPE_CHECKING:
    from backend.app.models.fix import FixProposal


class VerificationRun(Base):
    __tablename__ = "verification_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    fix_proposal_id: Mapped[str] = mapped_column(String(36), ForeignKey("fix_proposals.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="not_run", nullable=False)  # not_run, running, passed, failed, timed_out, cancelled, unavailable
    test_summary_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    exit_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    baseline_result: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # failed, passed, error
    candidate_result: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # passed, failed, error
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    fix_proposal: Mapped["FixProposal"] = relationship("FixProposal", back_populates="verification_runs")
