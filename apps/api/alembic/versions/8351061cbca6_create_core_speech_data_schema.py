"""create core speech data schema

Revision ID: 8351061cbca6
Revises:
Create Date: 2026-10-27 03:26:50.838079
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "8351061cbca6"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    goal_kind = sa.Enum(
        "presentation", "interview", "conversation", "leadership", "other", name="goal_kind"
    )
    session_kind = sa.Enum("practice", "presentation", "conversation", name="session_kind")
    session_status = sa.Enum(
        "draft", "uploading", "ready", "processing", "complete", "failed", name="session_status"
    )
    media_kind = sa.Enum(
        "original_audio", "normalized_audio", "derived_audio", name="media_kind"
    )
    analysis_run_status = sa.Enum("queued", "running", "complete", "failed", name="analysis_run_status")

    op.create_table(
        "personal_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("display_name", sa.String(length=120), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("preferences", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("is_primary", name="only_primary_profile"),
        sa.PrimaryKeyConstraint("id", name="pk_personal_profiles"),
        sa.UniqueConstraint("is_primary", name="uq_personal_profiles_is_primary"),
    )
    op.create_table(
        "communication_goals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("kind", goal_kind, nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("priority BETWEEN 1 AND 5", name="priority_range"),
        sa.ForeignKeyConstraint(["profile_id"], ["personal_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_communication_goals"),
    )
    op.create_index("ix_communication_goals_profile_id", "communication_goals", ["profile_id"])
    op.create_table(
        "speech_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("goal_id", sa.Uuid(), nullable=True),
        sa.Column("kind", session_kind, nullable=False),
        sa.Column("status", session_status, nullable=False, server_default="draft"),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="recorded"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["goal_id"], ["communication_goals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["profile_id"], ["personal_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_speech_sessions"),
    )
    op.create_index("ix_speech_sessions_goal_id", "speech_sessions", ["goal_id"])
    op.create_index("ix_speech_sessions_profile_id", "speech_sessions", ["profile_id"])
    op.create_index("ix_speech_sessions_profile_started", "speech_sessions", ["profile_id", "started_at"])
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("kind", media_kind, nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("sample_rate_hz", sa.Integer(), nullable=True),
        sa.Column("channel_count", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("encryption_key_version", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["speech_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_media_assets"),
        sa.UniqueConstraint("storage_key", name="storage_key"),
    )
    op.create_index("ix_media_assets_session_id", "media_assets", ["session_id"])
    op.create_index("ix_media_assets_sha256", "media_assets", ["sha256"])
    op.create_table(
        "transcripts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("model", sa.String(length=160), nullable=False),
        sa.Column("language_code", sa.String(length=16), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["speech_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_transcripts"),
        sa.UniqueConstraint("session_id", name="uq_transcripts_session_id"),
    )
    op.create_table(
        "transcript_words",
        sa.Column("transcript_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(length=200), nullable=False),
        sa.Column("start_ms", sa.Integer(), nullable=False),
        sa.Column("end_ms", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.ForeignKeyConstraint(["transcript_id"], ["transcripts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("transcript_id", "position", name="pk_transcript_words"),
    )
    op.create_table(
        "analysis_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_version", sa.String(length=64), nullable=False),
        sa.Column("status", analysis_run_status, nullable=False, server_default="queued"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["speech_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_analysis_runs"),
    )
    op.create_index("ix_analysis_runs_session_id", "analysis_runs", ["session_id"])
    op.create_table(
        "metric_values",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_run_id", sa.Uuid(), nullable=False),
        sa.Column("metric_code", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["analysis_run_id"], ["analysis_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_metric_values"),
        sa.UniqueConstraint("analysis_run_id", "metric_code", name="analysis_metric"),
    )
    op.create_index("ix_metric_values_analysis_run_id", "metric_values", ["analysis_run_id"])
    op.create_index("ix_metric_values_code_measured", "metric_values", ["metric_code", "measured_at"])


def downgrade() -> None:
    op.drop_index("ix_metric_values_code_measured", table_name="metric_values")
    op.drop_index("ix_metric_values_analysis_run_id", table_name="metric_values")
    op.drop_table("metric_values")
    op.drop_index("ix_analysis_runs_session_id", table_name="analysis_runs")
    op.drop_table("analysis_runs")
    op.drop_table("transcript_words")
    op.drop_table("transcripts")
    op.drop_index("ix_media_assets_sha256", table_name="media_assets")
    op.drop_index("ix_media_assets_session_id", table_name="media_assets")
    op.drop_table("media_assets")
    op.drop_index("ix_speech_sessions_profile_started", table_name="speech_sessions")
    op.drop_index("ix_speech_sessions_profile_id", table_name="speech_sessions")
    op.drop_index("ix_speech_sessions_goal_id", table_name="speech_sessions")
    op.drop_table("speech_sessions")
    op.drop_index("ix_communication_goals_profile_id", table_name="communication_goals")
    op.drop_table("communication_goals")
    op.drop_table("personal_profiles")

    for enum_name in (
        "analysis_run_status",
        "media_kind",
        "session_status",
        "session_kind",
        "goal_kind",
    ):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
