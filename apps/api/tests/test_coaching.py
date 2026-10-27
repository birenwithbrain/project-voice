import pytest

from app.schemas.coaching import (
    CoachingResult,
    CoachingStrength,
    RecommendedExercise,
)
from app.services.gemini_coach import EvidenceValidationError, validate_evidence


def report_with_evidence(evidence: str) -> CoachingResult:
    return CoachingResult(
        strengths=[
            CoachingStrength(
                title="Measured pacing",
                evidence=evidence,
                priority="medium",
            )
        ],
        improvements=[],
        recommended_exercises=[
            RecommendedExercise(
                title="One idea, one pause",
                instructions="Explain one idea, then pause for one second before continuing.",
                duration_minutes=2,
            )
        ],
        next_focus="Maintain a deliberate pace.",
    )


def test_metric_evidence_must_match_supplied_value_and_unit() -> None:
    report = report_with_evidence(
        "metric:speaking_rate_wpm value:142.5 unit:words_per_minute"
    )
    validate_evidence(
        report,
        transcript="I will explain this clearly.",
        metrics=[
            {
                "metric_code": "speaking_rate_wpm",
                "value": 142.5,
                "unit": "words_per_minute",
            }
        ],
    )


@pytest.mark.parametrize(
    "evidence",
    [
        "metric:speaking_rate_wpm value:999 unit:words_per_minute",
        "metric:made_up_metric value:142.5 unit:words_per_minute",
        "The model says my pace is good.",
    ],
)
def test_unverifiable_metric_evidence_is_rejected(evidence: str) -> None:
    with pytest.raises(EvidenceValidationError):
        validate_evidence(
            report_with_evidence(evidence),
            transcript="I will explain this clearly.",
            metrics=[
                {
                    "metric_code": "speaking_rate_wpm",
                    "value": 142.5,
                    "unit": "words_per_minute",
                }
            ],
        )


def test_transcript_quote_must_exist_in_source_text() -> None:
    report = report_with_evidence('transcript_quote: "I will explain this clearly."')
    validate_evidence(report, transcript="I will explain this clearly.", metrics=[])

    invented_quote = report_with_evidence('transcript_quote: "I am a brilliant speaker."')
    with pytest.raises(EvidenceValidationError):
        validate_evidence(invented_quote, transcript="I will explain this clearly.", metrics=[])
