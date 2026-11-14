import csv
import json
from pathlib import Path
from time import sleep

from fastapi.testclient import TestClient

from backend.app.api import experiments
from backend.app.dependencies import get_aquatwin_service, get_job_manager
from backend.app.main import app
from backend.app.services.jobs import JobManager


class FakeExperimentService:
    def run_batch_experiment(self, request, output_dir, progress_callback):
        target = Path(output_dir)
        target.mkdir(parents=True, exist_ok=True)
        json_path = target / "benchmark_results.json"
        csv_path = target / "benchmark_runs.csv"
        json_path.write_text(json.dumps({"runs": []}), encoding="utf-8")
        with csv_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["scenario_id", "score"])
        progress_callback(3, 3, "Completed")
        return {
            "configuration": {"scenario_count": 1},
            "summary": {},
            "runs": [],
            "output_files": {"json": str(json_path), "csv": str(csv_path)},
        }


def test_starts_tracks_and_downloads_batch_experiment(tmp_path) -> None:
    manager = JobManager(max_workers=1)
    original_root = experiments.OUTPUT_ROOT
    experiments.OUTPUT_ROOT = tmp_path
    app.dependency_overrides[get_aquatwin_service] = FakeExperimentService
    app.dependency_overrides[get_job_manager] = lambda: manager
    client = TestClient(app)
    response = client.post(
        "/api/experiments/batch",
        json={
            "network_id": "aquatwin_demo",
            "pipe_ids": ["P3"],
            "leak_areas": [0.0005],
            "seeds": [42],
        },
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    for _ in range(100):
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] == "completed":
            break
        sleep(0.001)
    download = client.get(f"/api/experiments/{job_id}/download?format=csv")
    assert job["progress"]["percent"] == 100.0
    assert download.status_code == 200
    assert "scenario_id" in download.text
    app.dependency_overrides.clear()
    experiments.OUTPUT_ROOT = original_root
    manager.shutdown()
