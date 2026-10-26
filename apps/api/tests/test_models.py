from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import (
    AnalysisRun,
    AnalysisRunStatus,
    CommunicationGoal,
    GoalKind,
    MetricValue,
    PersonalProfile,
    SessionKind,
    SpeechSession,
    Transcript,
    TranscriptWord,
)


def test_core_speech_data_graph_persists() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        profile = PersonalProfile(display_name="Private user")
        goal = CommunicationGoal(
            profile=profile,
            kind=GoalKind.PRESENTATION,
            title="Present clearly",
        )
        speech_session = SpeechSession(
            profile=profile,
            goal=goal,
            kind=SessionKind.PRACTICE,
            started_at=datetime.now(UTC),
        )
        transcript = Transcript(
            session=speech_session,
            provider="local-test",
            model="test-model",
            text="I will make this point clearly.",
        )
        transcript.words.append(TranscriptWord(position=0, text="I", start_ms=0, end_ms=100))
        analysis_run = AnalysisRun(
            session=speech_session,
            pipeline_version="test-v1",
            status=AnalysisRunStatus.COMPLETE,
        )
        analysis_run.metrics.append(
            MetricValue(
                metric_code="speaking_rate_wpm",
                value=Decimal("142.5"),
                unit="words_per_minute",
                measured_at=datetime.now(UTC),
            )
        )
        session.add(profile)
        session.commit()

        stored = session.scalar(select(SpeechSession))
        assert stored is not None
        assert stored.transcript is not None
        assert stored.transcript.words[0].text == "I"
        assert stored.analysis_runs[0].metrics[0].metric_code == "speaking_rate_wpm"
