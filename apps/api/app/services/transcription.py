from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class TranscribedWord:
    text: str
    start_ms: int
    end_ms: int
    probability: float | None


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language_code: str | None
    words: list[TranscribedWord]


@lru_cache
def get_whisper_model(model_name: str, device: str, compute_type: str):
    from faster_whisper import WhisperModel

    return WhisperModel(model_name, device=device, compute_type=compute_type)


def transcribe_audio(
    *, audio_path: Path, model_name: str, device: str, compute_type: str
) -> TranscriptionResult:
    model = get_whisper_model(model_name, device, compute_type)
    segments, info = model.transcribe(str(audio_path), vad_filter=True, word_timestamps=True)
    words: list[TranscribedWord] = []
    text_parts: list[str] = []
    for segment in segments:
        text_parts.append(segment.text.strip())
        for word in segment.words or []:
            words.append(
                TranscribedWord(
                    text=word.word.strip(),
                    start_ms=round(word.start * 1000),
                    end_ms=round(word.end * 1000),
                    probability=word.probability,
                )
            )
    return TranscriptionResult(
        text=" ".join(part for part in text_parts if part),
        language_code=getattr(info, "language", None),
        words=words,
    )
