import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import SessionKind, SessionStatus


class CreateSpeechSessionRequest(BaseModel):
    kind: SessionKind = SessionKind.PRACTICE
    title: str | None = Field(default=None, max_length=200)
    goal_id: uuid.UUID | None = None


class MediaAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content_type: str
    byte_size: int
    duration_ms: int | None
    created_at: datetime


class SpeechSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: SessionKind
    status: SessionStatus
    title: str | None
    duration_ms: int | None
    created_at: datetime
    media_assets: list[MediaAssetResponse]
