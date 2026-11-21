from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_returns_service_status_when_demo_mode_is_enabled(monkeypatch) -> None:
    monkeypatch.setenv("DEMO_MODE", "1")
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "credweave-ai-api",
        "version": "0.1.0",
        "synthetic_demo": True,
    }


def test_health_reports_demo_mode_disabled_by_default(monkeypatch) -> None:
    monkeypatch.setattr(app.state, "synthetic_demo", False)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["synthetic_demo"] is False
