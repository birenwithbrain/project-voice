import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import SessionKind, SessionStatus


Priority = Literal["low", "medium", "high"]


class CoachingStrength(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=3, max_length=160)
    evidence: str = Field(min_length=8, max_length=500)
    priority: Priority


class CoachingImprovement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=3, max_length=160)
    evidence: str = Field(min_length=8, max_length=500)
    why_it_matters: str = Field(min_length=3, max_length=500)
    priority: Priority


class RecommendedExercise(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=3, max_length=160)
    instructions: str = Field(min_length=10, max_length=1200)
    duration_minutes: int = Field(ge=1, le=30)


class CoachingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strengths: list[CoachingStrength] = Field(max_length=4)
    improvements: list[CoachingImprovement] = Field(max_length=4)
    recommended_exercises: list[RecommendedExercise] = Field(min_length=1, max_length=3)
    next_focus: str = Field(min_length=3, max_length=240)


class GenerateCoachingRequest(BaseModel):
    consent: bool


class ReportMetric(BaseModel):
    metric_code: str
    value: float
    unit: str


class SessionReportResponse(BaseModel):
    id: uuid.UUID
    kind: SessionKind
    status: SessionStatus
    title: str | None
    created_at: datetime
    transcript: str | None
    metrics: list[ReportMetric]
    coaching_report: CoachingResult | None
    coaching_model: str | None
    coaching_created_at: datetime | None
