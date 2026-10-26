from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_database_session
from app.main import app


def test_create_and_upload_practice_session(tmp_path, monkeypatch) -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_database_session():
        database = session_factory()
        try:
            yield database
        finally:
            database.close()

    monkeypatch.setattr(
        "app.routers.speech_sessions.get_settings",
        lambda: SimpleNamespace(storage_root=tmp_path, max_upload_bytes=1024),
    )
    app.dependency_overrides[get_database_session] = override_database_session
    client = TestClient(app)
    try:
        created = client.post("/api/v1/speech-sessions", json={"kind": "practice"})
        assert created.status_code == 201

        session_id = created.json()["id"]
        uploaded = client.post(
            f"/api/v1/speech-sessions/{session_id}/audio",
            data={"duration_ms": "2500"},
            files={"file": ("practice.webm", b"test audio", "audio/webm")},
        )

        assert uploaded.status_code == 200
        assert uploaded.json()["status"] == "ready"
        assert uploaded.json()["media_assets"][0]["byte_size"] == len(b"test audio")
        assert (tmp_path / "sessions" / session_id / "original.webm").exists()
    finally:
        app.dependency_overrides.clear()
