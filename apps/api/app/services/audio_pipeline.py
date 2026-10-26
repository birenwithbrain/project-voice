import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NormalizedAudio:
    byte_size: int
    duration_ms: int | None
    sample_rate_hz: int | None
    channel_count: int | None
    sha256: str


class AudioPipelineError(RuntimeError):
    """Raised when an audio file cannot be prepared for speech processing."""


def normalize_for_speech(
    *, source: Path, destination: Path, ffmpeg_path: str, ffprobe_path: str
) -> NormalizedAudio:
    """Produce mono, 16 kHz PCM WAV audio suitable for deterministic speech analysis."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".wav.part")
    try:
        subprocess.run(
            [
                ffmpeg_path,
                "-nostdin",
                "-y",
                "-i",
                str(source),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                "-af",
                "loudnorm=I=-16:TP=-1.5:LRA=11",
                str(temporary),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        temporary.replace(destination)
        metadata = probe_audio(destination, ffprobe_path)
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        temporary.unlink(missing_ok=True)
        raise AudioPipelineError("Audio preprocessing failed.") from error

    with destination.open("rb") as audio_file:
        sha256 = hashlib.file_digest(audio_file, "sha256").hexdigest()

    return NormalizedAudio(
        byte_size=destination.stat().st_size,
        duration_ms=metadata.duration_ms,
        sample_rate_hz=metadata.sample_rate_hz,
        channel_count=metadata.channel_count,
        sha256=sha256,
    )


def probe_audio(path: Path, ffprobe_path: str) -> "AudioMetadata":
    try:
        result = subprocess.run(
            [
                ffprobe_path,
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        payload = json.loads(result.stdout)
    except (
        FileNotFoundError,
        json.JSONDecodeError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ) as error:
        raise AudioPipelineError("Audio metadata inspection failed.") from error

    stream = next(
        (item for item in payload.get("streams", []) if item.get("codec_type") == "audio"),
        {},
    )
    duration = payload.get("format", {}).get("duration")
    return AudioMetadata(
        duration_ms=round(float(duration) * 1000) if duration else None,
        sample_rate_hz=int(stream["sample_rate"]) if stream.get("sample_rate") else None,
        channel_count=int(stream["channels"]) if stream.get("channels") else None,
    )


@dataclass(frozen=True)
class AudioMetadata:
    duration_ms: int | None
    sample_rate_hz: int | None
    channel_count: int | None
