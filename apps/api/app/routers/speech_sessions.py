import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.db.models import MediaAsset, MediaKind, PersonalProfile, SessionStatus, SpeechSession
from app.db.session import get_database_session
from app.schemas.speech_sessions import CreateSpeechSessionRequest, SpeechSessionResponse
from app.services.media_storage import delete_stored_media, store_original_audio

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
