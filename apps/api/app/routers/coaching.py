import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.db.coaching_models import CoachingReportRecord
from app.db.models import AnalysisRun, AnalysisRunStatus, SpeechSession
from app.db.session import get_database_session
from app.schemas.coaching import (
    CoachingResult,
    GenerateCoachingRequest,
    ReportMetric,
    SessionReportResponse,
)
from app.services.gemini_coach import EvidenceValidationError, generate_coaching

router = APIRouter(prefix="/speech-sessions", tags=["coaching"])
logger = logging.getLogger(__name__)


def _load_session(database: Session, session_id: uuid.UUID) -> SpeechSession:
    session = database.scalar(
        select(SpeechSession)
        .options(
            selectinload(SpeechSession.transcript),
            selectinload(SpeechSession.goal),
            selectinload(SpeechSession.analysis_runs).selectinload(AnalysisRun.metrics),
        )
        .where(SpeechSession.id == session_id)
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Speech session not found.")
    return session


def _report_response(database: Session, session: SpeechSession) -> SessionReportResponse:
    completed_runs = sorted(
        (run for run in session.analysis_runs if run.status is AnalysisRunStatus.COMPLETE),
        key=lambda run: run.created_at,
        reverse=True,
    )
    metrics = []
    if completed_runs:
        metrics = [
            ReportMetric(metric_code=item.metric_code, value=float(item.value), unit=item.unit)
            for item in sorted(completed_runs[0].metrics, key=lambda item: item.metric_code)
        ]
    saved = database.scalar(
        select(CoachingReportRecord).where(CoachingReportRecord.session_id == session.id)
    )
    return SessionReportResponse(
        id=session.id,
        kind=session.kind,
        status=session.status,
        title=session.title,
        created_at=session.created_at,
        transcript=session.transcript.text if session.transcript else None,
        metrics=metrics,
        coaching_report=CoachingResult.model_validate(saved.report_data) if saved else None,
        coaching_model=saved.model if saved else None,
        coaching_created_at=saved.updated_at if saved else None,
    )


@router.get("/{session_id}/report", response_model=SessionReportResponse)
def get_session_report(
    session_id: uuid.UUID,
    database: Session = Depends(get_database_session),
) -> SessionReportResponse:
    """Return local transcript and metrics, plus coaching if it has been generated."""
    session = _load_session(database, session_id)
    return _report_response(database, session)


@router.post("/{session_id}/coach", response_model=CoachingResult)
def coach_session(
    session_id: uuid.UUID,
    payload: GenerateCoachingRequest,
    database: Session = Depends(get_database_session),
) -> CoachingResult:
    """Generate post-session coaching after explicit consent to send text to Gemini."""
    if not payload.consent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Explicit consent is required before sending transcript text to Gemini.",
        )

    settings = get_settings()
    if not settings.gemini_api_key or not settings.gemini_model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini is not configured. Set VOICE_COACH_GEMINI_API_KEY and VOICE_COACH_GEMINI_MODEL on the server.",
        )

    session = _load_session(database, session_id)
    if session.transcript is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transcribe the session locally before requesting coaching.",
        )
    if len(session.transcript.text) > 40000:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="This transcript is too long for one coaching request. Shorten it and try again.",
        )

    completed_runs = sorted(
        (run for run in session.analysis_runs if run.status is AnalysisRunStatus.COMPLETE),
        key=lambda run: run.created_at,
        reverse=True,
    )
    if not completed_runs or not completed_runs[0].metrics:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Run deterministic local analysis before requesting coaching.",
        )

    metrics = [
        {
            "metric_code": item.metric_code,
            "value": float(item.value),
            "unit": item.unit,
        }
        for item in sorted(completed_runs[0].metrics, key=lambda item: item.metric_code)
    ]
    goal = None
    if session.goal is not None:
        goal = {"title": session.goal.title, "description": session.goal.description}
    context = session.context if isinstance(session.context, dict) else {}
    input_payload = {
        "transcript": session.transcript.text,
        "metrics": metrics,
        "goal": goal,
        "user_context": context,
    }
    digest = hashlib.sha256(
        json.dumps(input_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    try:
        result = generate_coaching(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            transcript=session.transcript.text,
            metrics=metrics,
            goal=goal,
            user_context=context,
        )
    except EvidenceValidationError:
        logger.warning("coaching_rejected_invalid_evidence session_id=%s", session.id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The coaching response did not meet evidence checks. Try generating it again.",
        ) from None
    except Exception as error:
        # Log only the exception type, never provider text or user content.
        logger.warning(
            "coaching_provider_failed session_id=%s error_type=%s",
            session.id,
            type(error).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gemini coaching could not be completed. Check server configuration and try again.",
        ) from None

    saved = database.scalar(
        select(CoachingReportRecord).where(CoachingReportRecord.session_id == session.id)
    )
    if saved is None:
        saved = CoachingReportRecord(
            session_id=session.id,
            provider="google-genai",
            model=settings.gemini_model,
            input_digest=digest,
            report_data=result.model_dump(mode="json"),
        )
        database.add(saved)
    else:
        saved.provider = "google-genai"
        saved.model = settings.gemini_model
        saved.input_digest = digest
        saved.report_data = result.model_dump(mode="json")
        saved.updated_at = datetime.now(UTC)

    database.commit()
    return result
