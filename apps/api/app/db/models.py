import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

JSON_TYPE = JSON().with_variant(JSONB, "postgresql")


class GoalKind(enum.StrEnum):
    PRESENTATION = "presentation"
    INTERVIEW = "interview"
    CONVERSATION = "conversation"
    LEADERSHIP = "leadership"
    OTHER = "other"


class SessionKind(enum.StrEnum):
    PRACTICE = "practice"
    PRESENTATION = "presentation"
    CONVERSATION = "conversation"


class SessionStatus(enum.StrEnum):
    DRAFT = "draft"
    UPLOADING = "uploading"
    READY = "ready"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


class MediaKind(enum.StrEnum):
    ORIGINAL_AUDIO = "original_audio"
    NORMALIZED_AUDIO = "normalized_audio"
    DERIVED_AUDIO = "derived_audio"


class AnalysisRunStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class PersonalProfile(TimestampMixin, Base):
    __tablename__ = "personal_profiles"
    __table_args__ = (
        CheckConstraint("is_primary", name="only_primary_profile"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(120))
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    preferences: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)

    goals: Mapped[list["CommunicationGoal"]] = relationship(back_populates="profile")
    sessions: Mapped[list["SpeechSession"]] = relationship(back_populates="profile")


class CommunicationGoal(TimestampMixin, Base):
    __tablename__ = "communication_goals"
    __table_args__ = (CheckConstraint("priority BETWEEN 1 AND 5", name="priority_range"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("personal_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[GoalKind] = mapped_column(Enum(GoalKind, name="goal_kind"), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    profile: Mapped[PersonalProfile] = relationship(back_populates="goals")
    sessions: Mapped[list["SpeechSession"]] = relationship(back_populates="goal")


class SpeechSession(TimestampMixin, Base):
    __tablename__ = "speech_sessions"
    __table_args__ = (Index("ix_speech_sessions_profile_started", "profile_id", "started_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("personal_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    goal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("communication_goals.id", ondelete="SET NULL"), index=True
    )
    kind: Mapped[SessionKind] = mapped_column(
        Enum(SessionKind, name="session_kind"), nullable=False
    )
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="session_status"), default=SessionStatus.DRAFT, nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(32), default="recorded", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    context: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)

    profile: Mapped[PersonalProfile] = relationship(back_populates="sessions")
    goal: Mapped[CommunicationGoal | None] = relationship(back_populates="sessions")
    media_assets: Mapped[list["MediaAsset"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    transcript: Mapped["Transcript | None"] = relationship(
        back_populates="session", cascade="all, delete-orphan", uselist=False
    )
    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class MediaAsset(TimestampMixin, Base):
    __tablename__ = "media_assets"
    __table_args__ = (UniqueConstraint("storage_key", name="storage_key"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("speech_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[MediaKind] = mapped_column(Enum(MediaKind, name="media_kind"), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    sample_rate_hz: Mapped[int | None] = mapped_column(Integer)
    channel_count: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    encryption_key_version: Mapped[str | None] = mapped_column(String(64))

    session: Mapped[SpeechSession] = relationship(back_populates="media_assets")


class Transcript(TimestampMixin, Base):
    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("speech_sessions.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(160), nullable=False)
    language_code: Mapped[str | None] = mapped_column(String(16))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))

    session: Mapped[SpeechSession] = relationship(back_populates="transcript")
    words: Mapped[list["TranscriptWord"]] = relationship(
        back_populates="transcript",
        cascade="all, delete-orphan",
        order_by="TranscriptWord.position",
    )


class TranscriptWord(Base):
    __tablename__ = "transcript_words"

    transcript_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("transcripts.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String(200), nullable=False)
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))

    transcript: Mapped[Transcript] = relationship(back_populates="words")


class AnalysisRun(TimestampMixin, Base):
    __tablename__ = "analysis_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("speech_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pipeline_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[AnalysisRunStatus] = mapped_column(
        Enum(AnalysisRunStatus, name="analysis_run_status"),
        default=AnalysisRunStatus.QUEUED,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(String(80))

    session: Mapped[SpeechSession] = relationship(back_populates="analysis_runs")
    metrics: Mapped[list["MetricValue"]] = relationship(
        back_populates="analysis_run", cascade="all, delete-orphan"
    )


class MetricValue(Base):
    __tablename__ = "metric_values"
    __table_args__ = (
        UniqueConstraint("analysis_run_id", "metric_code", name="analysis_metric"),
        Index("ix_metric_values_code_measured", "metric_code", "measured_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    metric_code: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="metrics")
