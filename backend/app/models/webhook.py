from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.base import Base, generate_uuid, utc_now


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    __table_args__ = (
        UniqueConstraint("external_delivery_id", name="uq_webhook_delivery_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    provider: Mapped[str] = mapped_column(String(50), default="github", nullable=False)
    external_delivery_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    processing_status: Mapped[str] = mapped_column(String(50), default="received", nullable=False)  # received, processed, duplicate, ignored, error
    payload_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
