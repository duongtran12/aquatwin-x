import json
from io import BytesIO
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, Response

from backend.app.dependencies import get_aquatwin_service, get_job_manager
from backend.app.schemas.requests import BatchExperimentRequest
from backend.app.services.aquatwin_service import AquaTwinService
from backend.app.services.jobs import JobManager


router = APIRouter(prefix="/experiments", tags=["Experiments"])
PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_ROOT = PROJECT_ROOT / "data" / "benchmark" / "api"


def _experiment_directory(experiment_id: str) -> Path:
    if not experiment_id or len(experiment_id) > 100 or any(
        character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        for character in experiment_id
    ):
        raise HTTPException(status_code=404, detail="Experiment not found")
    return (OUTPUT_ROOT / experiment_id).resolve()


def _load_archived_result(experiment_id: str) -> tuple[dict[str, Any], Path]:
    directory = _experiment_directory(experiment_id)
    root = OUTPUT_ROOT.resolve()
    if directory.parent != root:
        raise HTTPException(status_code=404, detail="Experiment not found")
    result_path = directory / "benchmark_results.json"
    if not result_path.is_file():
        raise HTTPException(status_code=404, detail="Experiment not found")
    try:
        return json.loads(result_path.read_text(encoding="utf-8-sig")), directory
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Experiment archive is invalid") from exc


def _archive_item(experiment_id: str, result: dict[str, Any], directory: Path) -> dict[str, Any]:
    configuration = result.get("configuration", {})
    ga = result.get("summary", {}).get("genetic_algorithm", {})
    evaluation = result.get("evaluation", {}).get("overall", {})
    created_at = datetime.fromtimestamp(
        (directory / "benchmark_results.json").stat().st_mtime,
        timezone.utc,
    ).isoformat()
    return {
        "experiment_id": experiment_id,
        "created_at": created_at,
        "network_id": configuration.get("network_id", configuration.get("network_file")),
        "runtime_mode": result.get("runtime", {}).get("mode", "direct"),
        "scenario_count": configuration.get("scenario_count", 0),
        "ga_run_count": evaluation.get("ga_run_count", ga.get("run_count", 0)),
        "ga_mean_score": ga.get("mean_score"),
        "global_optimum_hit_rate": evaluation.get(
            "global_optimum_hit_rate",
            ga.get("global_optimum_hit_rate"),
        ),
        "mean_score_gap": evaluation.get("mean_score_gap"),
        "mean_speedup": evaluation.get("mean_speedup"),
        "mean_candidate_reduction_rate": evaluation.get("mean_candidate_reduction_rate"),
    }


@router.get("")
def list_batch_experiments(limit: int = 20) -> list[dict[str, Any]]:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    if not OUTPUT_ROOT.is_dir():
        return []
    items = []
    for directory in OUTPUT_ROOT.iterdir():
        if not directory.is_dir():
            continue
        try:
            result, resolved_directory = _load_archived_result(directory.name)
            items.append(_archive_item(directory.name, result, resolved_directory))
        except HTTPException:
            continue
    return sorted(items, key=lambda item: item["created_at"], reverse=True)[:limit]


@router.post("/batch", status_code=status.HTTP_202_ACCEPTED)
def start_batch_experiment(
    request: BatchExperimentRequest,
    service: AquaTwinService = Depends(get_aquatwin_service),
    jobs: JobManager = Depends(get_job_manager),
) -> dict[str, Any]:
    total_steps = len(request.pipe_ids) * len(request.leak_areas) * (2 + len(request.seeds))

    def task(job_id: str, report: Any) -> dict[str, Any]:
        return service.run_batch_experiment(request, OUTPUT_ROOT / job_id, report)

    return jobs.submit_progress(task, total_steps)


@router.get("/{job_id}/download")
def download_batch_result(
    job_id: str,
    format: Literal["json", "csv", "summary", "report", "zip"] = "csv",
    jobs: JobManager = Depends(get_job_manager),
) -> Response:
    filenames = {
        "json": "benchmark_results.json",
        "csv": "benchmark_runs.csv",
        "summary": "benchmark_summary.csv",
        "report": "benchmark_report.md",
    }
    directory = _experiment_directory(job_id)
    if format == "zip":
        archived_files = [directory / filename for filename in filenames.values()]
        if all(path.is_file() for path in archived_files):
            stream = BytesIO()
            with ZipFile(stream, "w", ZIP_DEFLATED) as archive:
                for path in archived_files:
                    archive.write(path, arcname=path.name)
            return Response(
                content=stream.getvalue(),
                media_type="application/zip",
                headers={
                    "Content-Disposition": (
                        f'attachment; filename="aquatwin-experiment-{job_id}.zip"'
                    )
                },
            )
    else:
        archived_path = directory / filenames[format]
        if archived_path.is_file():
            media_types = {
                "json": "application/json",
                "csv": "text/csv",
                "summary": "text/csv",
                "report": "text/markdown",
            }
            return FileResponse(
                archived_path,
                media_type=media_types[format],
                filename=archived_path.name,
            )

    try:
        job = jobs.status(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Experiment job not found") from exc
    if job["status"] == "failed":
        raise HTTPException(status_code=422, detail=job["error"])
    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail="Experiment is not completed")

    raise HTTPException(status_code=404, detail="Experiment output file not found")


@router.get("/{experiment_id}")
def get_batch_experiment(experiment_id: str) -> dict[str, Any]:
    result, _ = _load_archived_result(experiment_id)
    result["experiment_id"] = experiment_id
    return result
