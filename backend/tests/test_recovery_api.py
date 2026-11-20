from threading import Event
from time import sleep
from typing import Any

from fastapi.testclient import TestClient

from backend.app.dependencies import get_aquatwin_service, get_job_manager
from backend.app.main import app
from backend.app.services.jobs import JobManager


class FakeOptimizationService:
    def optimize(self, request: Any) -> dict[str, Any]:
        return {
            "algorithm": request.algorithm,
            "best_candidate": {"score": 92.5},
        }


client = TestClient(app)
job_manager: JobManager | None = None


def setup_function() -> None:
    global job_manager
    job_manager = JobManager(max_workers=1)
    app.dependency_overrides[get_aquatwin_service] = FakeOptimizationService
    app.dependency_overrides[get_job_manager] = lambda: job_manager


def teardown_function() -> None:
    app.dependency_overrides.clear()
    if job_manager is not None:
        job_manager.shutdown()


def test_submits_and_reads_optimization_result() -> None:
    response = client.post(
        "/api/recovery/optimize",
        json={
            "network_id": "aquatwin_demo",
            "algorithm": "ga",
            "scenario": {
                "pipe_id": "P3",
                "leak_area": 0.0005,
                "start_time": 7200,
                "end_time": 43200,
            },
        },
    )

    assert response.status_code == 202
    job_id = response.json()["job_id"]
    for _ in range(100):
        status = client.get(f"/api/jobs/{job_id}").json()["status"]
        if status == "completed":
            break
        sleep(0.001)

    result = client.get(f"/api/results/{job_id}")
    assert result.status_code == 200
    assert result.json()["algorithm"] == "ga"
    assert result.json()["best_candidate"]["score"] == 92.5


def test_cancels_running_progress_job_through_api() -> None:
    assert job_manager is not None
    started = Event()
    release = Event()

    def task(job_id, report):
        started.set()
        release.wait(timeout=2)
        report(1, 2, "First run")
        return {"job_id": job_id}

    job = job_manager.submit_progress(task, total_steps=2)
    assert started.wait(timeout=2)

    response = client.delete(f"/api/jobs/{job['job_id']}")
    release.set()

    assert response.status_code == 200
    assert response.json()["status"] == "cancelling"
    for _ in range(100):
        status = client.get(f"/api/jobs/{job['job_id']}").json()["status"]
        if status == "cancelled":
            break
        sleep(0.001)
    assert status == "cancelled"
    result = client.get(f"/api/results/{job['job_id']}")
    assert result.status_code == 409
    assert result.json()["detail"] == "Job was cancelled"

