import csv
import io
import json
from pathlib import Path
from time import sleep
from zipfile import ZipFile

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
        summary_path = target / "benchmark_summary.csv"
        report_path = target / "benchmark_report.md"
        result = {
            "configuration": {"scenario_count": 1, "network_id": request.network_id},
            "runtime": {"mode": "real", "synthetic_data": False},
            "summary": {
                "genetic_algorithm": {
                    "run_count": 1,
                    "mean_score": 91.5,
                    "global_optimum_hit_rate": 1.0,
                },
            },
            "evaluation": {
                "overall": {
                    "ga_run_count": 1,
                    "mean_score_gap": 0.0,
                    "mean_speedup": 2.5,
                    "mean_candidate_reduction_rate": 0.6,
                    "global_optimum_hit_rate": 1.0,
                },
                "scenarios": [],
            },
            "runs": [],
        }
        json_path.write_text(json.dumps(result), encoding="utf-8")
        with csv_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["scenario_id", "score"])
        summary_path.write_text("scenario_id,ga_mean_score\n", encoding="utf-8")
        report_path.write_text("# Benchmark report\n", encoding="utf-8")
        progress_callback(3, 3, "Completed")
        return {
            **result,
            "output_files": {
                "json": str(json_path),
                "csv": str(csv_path),
                "summary": str(summary_path),
                "report": str(report_path),
            },
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
    summary_download = client.get(f"/api/experiments/{job_id}/download?format=summary")
    report_download = client.get(f"/api/experiments/{job_id}/download?format=report")
    zip_download = client.get(f"/api/experiments/{job_id}/download?format=zip")
    archive = client.get("/api/experiments").json()
    archived_result = client.get(f"/api/experiments/{job_id}").json()
    assert job["progress"]["percent"] == 100.0
    assert download.status_code == 200
    assert "scenario_id" in download.text
    assert summary_download.status_code == 200
    assert "ga_mean_score" in summary_download.text
    assert report_download.status_code == 200
    assert "Benchmark report" in report_download.text
    assert zip_download.status_code == 200
    assert zip_download.headers["content-type"] == "application/zip"
    with ZipFile(io.BytesIO(zip_download.content)) as archive_file:
        assert set(archive_file.namelist()) == {
            "benchmark_results.json",
            "benchmark_runs.csv",
            "benchmark_summary.csv",
            "benchmark_report.md",
        }
    assert archive[0]["experiment_id"] == job_id
    assert archive[0]["runtime_mode"] == "real"
    assert archive[0]["ga_mean_score"] == 91.5
    assert archived_result["experiment_id"] == job_id
    assert archived_result["evaluation"]["overall"]["mean_speedup"] == 2.5

    restarted_manager = JobManager(max_workers=1)
    app.dependency_overrides[get_job_manager] = lambda: restarted_manager
    persistent_download = client.get(f"/api/experiments/{job_id}/download?format=report")
    persistent_zip = client.get(f"/api/experiments/{job_id}/download?format=zip")
    assert persistent_download.status_code == 200
    assert persistent_zip.status_code == 200
    assert client.get("/api/experiments/not/a/valid/id").status_code == 404
    restarted_manager.shutdown()
    app.dependency_overrides.clear()
    experiments.OUTPUT_ROOT = original_root
    manager.shutdown()
