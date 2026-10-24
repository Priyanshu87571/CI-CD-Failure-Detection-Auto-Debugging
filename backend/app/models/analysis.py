from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, DateTime, ForeignKey, Integer, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base, generate_uuid, utc_now

if TYPE_CHECKING:
    from backend.app.models.failure import Failure
    from backend.app.models.fix import FixProposal


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    failure_id: Mapped[str] = mapped_column(String(36), ForeignKey("failures.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="completed", nullable=False)  # completed, inconclusive, failed
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # deterministic_rule, openai, anthropic, fallback, mock
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    root_cause: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    alternatives_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    confidence_method: Mapped[str] = mapped_column(String(100), default="deterministic_rule", nullable=False)
    recommendations_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    token_usage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    failure: Mapped["Failure"] = relationship("Failure", back_populates="analyses")
    fix_proposals: Mapped[List["FixProposal"]] = relationship("FixProposal", back_populates="analysis", cascade="all, delete-orphan")
