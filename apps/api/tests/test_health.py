from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_liveness_returns_success_and_request_id() -> None:
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["x-request-id"]


def test_readiness_returns_success_when_database_is_available(monkeypatch) -> None:
    monkeypatch.setattr("app.routers.health.database_is_ready", lambda: True)
    response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_readiness_returns_service_unavailable_without_database(monkeypatch) -> None:
    monkeypatch.setattr("app.routers.health.database_is_ready", lambda: False)

    response = client.get("/api/v1/health/ready")

    assert response.status_code == 503
