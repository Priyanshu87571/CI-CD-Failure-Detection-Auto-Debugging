from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, generate_uuid, utc_now

if TYPE_CHECKING:
    from backend.app.models.analysis import Analysis
    from backend.app.models.verification import VerificationRun


class FixProposal(Base):
    __tablename__ = "fix_proposals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    analysis_id: Mapped[str] = mapped_column(String(36), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)  # draft, approved, rejected, applied
    patch_content: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    affected_files_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="fix_proposals")
    verification_runs: Mapped[List["VerificationRun"]] = relationship("VerificationRun", back_populates="fix_proposal", cascade="all, delete-orphan")
