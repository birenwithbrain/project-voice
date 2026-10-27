import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class CoachingReportRecord(TimestampMixin, Base):
    """One versioned, evidence-checked AI coaching report per speech session."""

    __tablename__ = "coaching_reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("speech_sessions.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(160), nullable=False)
    input_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    report_data: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
