import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.db.models import (
    MediaAsset,
    MediaKind,
    PersonalProfile,
    SessionStatus,
    SpeechSession,
    Transcript,
    TranscriptWord,
)
from app.db.session import get_database_session
from app.schemas.speech_sessions import CreateSpeechSessionRequest, SpeechSessionResponse
from app.services.audio_pipeline import AudioPipelineError, normalize_for_speech
from app.services.media_storage import delete_stored_media, store_original_audio
from app.services.transcription import transcribe_audio

router = APIRouter(prefix="/speech-sessions", tags=["speech sessions"])


def get_or_create_profile(database: Session) -> PersonalProfile:
    profile = database.scalar(select(PersonalProfile).where(PersonalProfile.is_primary.is_(True)))
    if profile is None:
        profile = PersonalProfile()
        database.add(profile)
        database.flush()
    return profile


def get_session_or_404(database: Session, session_id: uuid.UUID) -> SpeechSession:
    speech_session = database.scalar(
        select(SpeechSession)
        .options(selectinload(SpeechSession.media_assets))
        .where(SpeechSession.id == session_id)
    )
    if speech_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Speech session not found.",
        )
    return speech_session


@router.post("", response_model=SpeechSessionResponse, status_code=status.HTTP_201_CREATED)
def create_speech_session(
    payload: CreateSpeechSessionRequest,
    database: Session = Depends(get_database_session),
) -> SpeechSession:
    profile = get_or_create_profile(database)
    speech_session = SpeechSession(
        profile=profile,
        goal_id=payload.goal_id,
        kind=payload.kind,
        title=payload.title,
        status=SessionStatus.DRAFT,
    )
    database.add(speech_session)
    database.commit()
    database.refresh(speech_session)
    return speech_session


@router.post("/{session_id}/audio", response_model=SpeechSessionResponse)
async def upload_original_audio(
    session_id: uuid.UUID,
    file: UploadFile = File(...),
    duration_ms: int | None = Form(default=None, ge=1),
    database: Session = Depends(get_database_session),
) -> SpeechSession:
    speech_session = get_session_or_404(database, session_id)
    if speech_session.status is not SessionStatus.DRAFT or speech_session.media_assets:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This session already has an uploaded recording.",
        )

    settings = get_settings()
    stored_media = await store_original_audio(
        file=file,
        session_id=speech_session.id,
        storage_root=settings.storage_root,
        max_upload_bytes=settings.max_upload_bytes,
    )
    try:
        media_asset = MediaAsset(
            session=speech_session,
            kind=MediaKind.ORIGINAL_AUDIO,
            storage_key=stored_media.storage_key,
            content_type=file.content_type or "application/octet-stream",
            byte_size=stored_media.byte_size,
            duration_ms=duration_ms,
            sha256=stored_media.sha256,
        )
        speech_session.duration_ms = duration_ms
        speech_session.status = SessionStatus.READY
        database.add(media_asset)
        database.commit()
    except Exception:
        database.rollback()
        delete_stored_media(settings.storage_root, stored_media.storage_key)
        raise

    return get_session_or_404(database, session_id)


@router.get("/{session_id}", response_model=SpeechSessionResponse)
def get_speech_session(
    session_id: uuid.UUID,
    database: Session = Depends(get_database_session),
) -> SpeechSession:
    return get_session_or_404(database, session_id)


@router.post("/{session_id}/preprocess", response_model=SpeechSessionResponse)
def preprocess_audio(
    session_id: uuid.UUID,
    database: Session = Depends(get_database_session),
) -> SpeechSession:
    """Normalize stored audio to a consistent, speech-analysis-ready WAV file."""

    speech_session = get_session_or_404(database, session_id)
    original = next(
        (asset for asset in speech_session.media_assets if asset.kind is MediaKind.ORIGINAL_AUDIO),
        None,
    )
    already_normalized = any(
        asset.kind is MediaKind.NORMALIZED_AUDIO for asset in speech_session.media_assets
    )
    if original is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Upload audio before preprocessing.",
        )
    if already_normalized:
        return speech_session

    settings = get_settings()
    target_key = f"sessions/{session_id}/normalized.wav"
    try:
        normalized = normalize_for_speech(
            source=settings.storage_root / original.storage_key,
            destination=settings.storage_root / target_key,
            ffmpeg_path=settings.ffmpeg_path,
            ffprobe_path=settings.ffprobe_path,
        )
    except AudioPipelineError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Audio preprocessing is unavailable. Install FFmpeg or use the container stack.",
        ) from error

    database.add(
        MediaAsset(
            session=speech_session,
            kind=MediaKind.NORMALIZED_AUDIO,
            storage_key=target_key,
            content_type="audio/wav",
            byte_size=normalized.byte_size,
            duration_ms=normalized.duration_ms,
            sample_rate_hz=normalized.sample_rate_hz,
            channel_count=normalized.channel_count,
            sha256=normalized.sha256,
        )
    )
    database.commit()
    return get_session_or_404(database, session_id)


@router.post("/{session_id}/transcribe", response_model=SpeechSessionResponse)
def transcribe_speech_session(
    session_id: uuid.UUID,
    database: Session = Depends(get_database_session),
) -> SpeechSession:
    """Transcribe prepared audio locally with word timestamps."""
    speech_session = get_session_or_404(database, session_id)
    if speech_session.transcript is not None:
        return speech_session
    normalized = next(
        (
            asset
            for asset in speech_session.media_assets
            if asset.kind is MediaKind.NORMALIZED_AUDIO
        ),
        None,
    )
    if normalized is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Preprocess audio before transcription.",
        )

    settings = get_settings()
    try:
        result = transcribe_audio(
            audio_path=settings.storage_root / normalized.storage_key,
            model_name=settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Local transcription is unavailable.",
        ) from error

    transcript = Transcript(
        session=speech_session,
        provider="faster-whisper",
        model=settings.whisper_model,
        language_code=result.language_code,
        text=result.text,
    )
    transcript.words = [
        TranscriptWord(
            position=index,
            text=word.text,
            start_ms=word.start_ms,
            end_ms=word.end_ms,
            confidence=word.probability,
        )
        for index, word in enumerate(result.words)
    ]
    database.add(transcript)
    database.commit()
    return get_session_or_404(database, session_id)
