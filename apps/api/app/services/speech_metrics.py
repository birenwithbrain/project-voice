import re
from dataclasses import dataclass

from app.services.transcription import TranscribedWord

FILLERS = {"um", "uh", "like", "basically", "actually", "literally"}
HEDGES = {"maybe", "probably", "perhaps", "possibly", "somewhat", "kind of", "sort of"}


@dataclass(frozen=True)
class CalculatedMetric:
    code: str
    value: float
    unit: str


def calculate_metrics(*, text: str, words: list[TranscribedWord]) -> list[CalculatedMetric]:
    normalized_words = [word.text.lower().strip(".,!?;:\"") for word in words if word.text]
    word_count = len(normalized_words)
    duration_ms = words[-1].end_ms - words[0].start_ms if len(words) > 1 else 0
    minutes = duration_ms / 60_000 if duration_ms > 0 else 0
    sentences = [sentence for sentence in re.split(r"[.!?]+", text) if sentence.strip()]
    filler_count = sum(word in FILLERS for word in normalized_words)
    hedge_count = sum(text.lower().count(hedge) for hedge in HEDGES)
    repeated_count = sum(
        current == previous
        for previous, current in zip(normalized_words, normalized_words[1:], strict=False)
    )
    pauses = [
        current.start_ms - previous.end_ms
        for previous, current in zip(words, words[1:], strict=False)
        if current.start_ms - previous.end_ms >= 300
    ]
    return [
        CalculatedMetric("word_count", word_count, "words"),
        CalculatedMetric(
            "speaking_rate_wpm", word_count / minutes if minutes else 0, "words_per_minute"
        ),
        CalculatedMetric("filler_count", filler_count, "occurrences"),
        CalculatedMetric("filler_rate", filler_count / word_count if word_count else 0, "ratio"),
        CalculatedMetric("hedge_count", hedge_count, "occurrences"),
        CalculatedMetric("repeated_word_count", repeated_count, "occurrences"),
        CalculatedMetric("sentence_count", len(sentences), "sentences"),
        CalculatedMetric(
            "average_sentence_length",
            word_count / len(sentences) if sentences else 0,
            "words_per_sentence",
        ),
        CalculatedMetric("pause_count", len(pauses), "pauses"),
        CalculatedMetric(
            "average_pause_ms", sum(pauses) / len(pauses) if pauses else 0, "milliseconds"
        ),
    ]
