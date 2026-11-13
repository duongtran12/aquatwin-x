from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.dependencies import get_aquatwin_service, get_job_manager
from backend.app.schemas.requests import OptimizationRequest
from backend.app.services.aquatwin_service import AquaTwinService
from backend.app.services.jobs import JobManager


router = APIRouter(tags=["Recovery"])


@router.post("/recovery/optimize", status_code=status.HTTP_202_ACCEPTED)
def optimize_recovery(
    request: OptimizationRequest,
    service: AquaTwinService = Depends(get_aquatwin_service),
    jobs: JobManager = Depends(get_job_manager),
) -> dict[str, Any]:
    return jobs.submit(lambda: service.optimize(request))


@router.get("/jobs/{job_id}")
def get_job_status(
    job_id: str,
    jobs: JobManager = Depends(get_job_manager),
) -> dict[str, Any]:
    try:
        return jobs.status(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc


@router.get("/results/{job_id}")
def get_job_result(
    job_id: str,
    jobs: JobManager = Depends(get_job_manager),
) -> dict[str, Any]:
    try:
        job = jobs.status(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Không tìm thấy job") from exc
    if job["status"] == "failed":
        raise HTTPException(status_code=422, detail=job["error"])
    if job["status"] != "completed":
        raise HTTPException(
            status_code=409,
            detail=f"Job chưa hoàn thành, trạng thái hiện tại: {job['status']}",
        )
    return jobs.result(job_id)
