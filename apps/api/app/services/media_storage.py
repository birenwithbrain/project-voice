import hashlib
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

ALLOWED_AUDIO_TYPES = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
}
CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class StoredMedia:
    storage_key: str
    byte_size: int
    sha256: str


async def store_original_audio(
    *, file: UploadFile, session_id: uuid.UUID, storage_root: Path, max_upload_bytes: int
) -> StoredMedia:
    content_type = file.content_type or ""
    extension = ALLOWED_AUDIO_TYPES.get(content_type)
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported audio format.",
        )

    relative_path = Path("sessions") / str(session_id) / f"original{extension}"
    destination = storage_root / relative_path
    temporary_path = destination.with_suffix(f"{extension}.part")
    destination.parent.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha256()
    byte_size = 0
    try:
        with temporary_path.open("wb") as output:
            while chunk := await file.read(CHUNK_SIZE):
                byte_size += len(chunk)
                if byte_size > max_upload_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Audio file exceeds the configured upload limit.",
                    )
                digest.update(chunk)
                output.write(chunk)
        os.replace(temporary_path, destination)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    return StoredMedia(
        storage_key=relative_path.as_posix(),
        byte_size=byte_size,
        sha256=digest.hexdigest(),
    )


def delete_stored_media(storage_root: Path, storage_key: str) -> None:
    (storage_root / storage_key).unlink(missing_ok=True)
