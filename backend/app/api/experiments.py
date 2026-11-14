from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from backend.app.dependencies import get_aquatwin_service, get_job_manager
from backend.app.schemas.requests import BatchExperimentRequest
from backend.app.services.aquatwin_service import AquaTwinService
from backend.app.services.jobs import JobManager


router = APIRouter(prefix="/experiments", tags=["Experiments"])
PROJECT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_ROOT = PROJECT_ROOT / "data" / "benchmark" / "api"


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
    format: Literal["json", "csv"] = "csv",
    jobs: JobManager = Depends(get_job_manager),
) -> FileResponse:
    try:
        job = jobs.status(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Experiment job not found") from exc
    if job["status"] == "failed":
        raise HTTPException(status_code=422, detail=job["error"])
    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail="Experiment is not completed")

    result = jobs.result(job_id)
    path = Path(result["output_files"][format]).resolve()
    expected_root = (OUTPUT_ROOT / job_id).resolve()
    if expected_root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Experiment output file not found")
    media_type = "application/json" if format == "json" else "text/csv"
    return FileResponse(path, media_type=media_type, filename=path.name)
