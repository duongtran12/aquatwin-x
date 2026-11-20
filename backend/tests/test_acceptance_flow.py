from time import sleep

from fastapi.testclient import TestClient

from backend.app.dependencies import get_aquatwin_service, get_history_store, get_job_manager
from backend.app.main import app
from backend.app.services.aquatwin_service import AquaTwinService
from backend.app.services.history import RunHistoryStore
from backend.app.services.jobs import JobManager


def test_complete_operator_decision_flow(tmp_path) -> None:
    history = RunHistoryStore(tmp_path / "acceptance.db")
    service = AquaTwinService(
        "demo",
        history_store=history,
        custom_network_dir=tmp_path / "networks",
        custom_valve_dir=tmp_path / "valves",
    )
    jobs = JobManager(max_workers=1)
    app.dependency_overrides[get_aquatwin_service] = lambda: service
    app.dependency_overrides[get_history_store] = lambda: history
    app.dependency_overrides[get_job_manager] = lambda: jobs
    client = TestClient(app)
    scenario = {
        "pipe_id": "P3",
        "leak_area": 0.0005,
        "start_time": 7200,
        "end_time": 21600,
    }

    try:
        network = client.get("/api/networks/aquatwin_demo")
        failure = client.post(
            "/api/simulations/failure",
            json={"network_id": "aquatwin_demo", "scenario": scenario},
        )
        manual = client.post(
            "/api/simulations/what-if",
            json={
                "network_id": "aquatwin_demo",
                "scenario": scenario,
                "actions": [{"valve_id": "V_P3_START", "status": "CLOSED"}],
            },
        )
        optimization = client.post(
            "/api/recovery/optimize",
            json={
                "network_id": "aquatwin_demo",
                "scenario": scenario,
                "algorithm": "ga",
                "population_size": 6,
                "generations": 3,
                "max_actions": 1,
                "top_k": 3,
                "tournament_size": 2,
                "elite_count": 1,
                "seed": 42,
            },
        )
        job_id = optimization.json()["job_id"]
        job = {}
        for _ in range(300):
            job = client.get(f"/api/jobs/{job_id}").json()
            if job["status"] in {"completed", "failed"}:
                break
            sleep(0.01)
        result = client.get(f"/api/results/{job_id}")
        archive = client.get("/api/history")
        optimization_run = next(item for item in archive.json() if item["run_type"] == "optimization")
        report = client.get(
            f"/api/history/{optimization_run['run_id']}/download?format=html"
        )
    finally:
        app.dependency_overrides.clear()
        jobs.shutdown()

    assert network.status_code == 200
    assert network.json()["runtime"]["effective_mode"] == "demo"
    assert failure.status_code == 200
    assert failure.json()["summary"]["maximum_affected_nodes"] >= 0
    assert manual.status_code == 200
    assert manual.json()["actions"][0]["valve_id"] == "V_P3_START"
    assert optimization.status_code == 202
    assert job["status"] == "completed"
    assert result.status_code == 200
    assert result.json()["algorithm"] == "demo_genetic_algorithm"
    assert result.json()["best_candidate"]["score"] >= 0
    assert len(archive.json()) == 3
    assert {item["run_type"] for item in archive.json()} == {
        "failure",
        "manual_recovery",
        "optimization",
    }
    assert report.status_code == 200
    assert "AQUATWIN-X DECISION EVIDENCE" in report.text
    assert "Synthetic demo result" in report.text
