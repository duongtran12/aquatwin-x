from typing import Any

from fastapi.testclient import TestClient

from backend.app.dependencies import get_aquatwin_service
from backend.app.main import app


class FakeAquaTwinService:
    def run_baseline(self, request: Any) -> dict[str, Any]:
        return {"scenario": "baseline", "network_id": request.network_id}

    def run_failure(self, request: Any) -> dict[str, Any]:
        return {
            "scenario": "pipe_leak",
            "pipe_id": request.scenario.pipe_id,
        }

    def run_manual_recovery(self, request: Any) -> dict[str, Any]:
        return {
            "scenario": "manual_recovery",
            "action_count": len(request.actions),
        }


client = TestClient(app)


def setup_function() -> None:
    app.dependency_overrides[get_aquatwin_service] = FakeAquaTwinService


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_runs_baseline_endpoint() -> None:
    response = client.post(
        "/api/simulations/baseline",
        json={"network_id": "aquatwin_demo"},
    )

    assert response.status_code == 200
    assert response.json()["scenario"] == "baseline"


def test_runs_failure_endpoint() -> None:
    response = client.post(
        "/api/simulations/failure",
        json={
            "network_id": "aquatwin_demo",
            "scenario": {
                "pipe_id": "P3",
                "leak_area": 0.0005,
                "start_time": 7200,
                "end_time": 43200,
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["pipe_id"] == "P3"


def test_rejects_invalid_failure_time_range() -> None:
    response = client.post(
        "/api/simulations/failure",
        json={
            "network_id": "aquatwin_demo",
            "scenario": {
                "pipe_id": "P3",
                "leak_area": 0.0005,
                "start_time": 7200,
                "end_time": 3600,
            },
        },
    )

    assert response.status_code == 422

