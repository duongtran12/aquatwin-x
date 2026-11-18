from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_runtime_health_check_exposes_effective_mode() -> None:
    response = client.get("/api/health/runtime")

    assert response.status_code == 200
    assert response.json()["runtime"]["effective_mode"] in {"real", "demo", "unavailable"}
    assert "wntr_available" in response.json()["runtime"]

