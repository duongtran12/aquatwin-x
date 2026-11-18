from typing import Any

from fastapi import APIRouter, Depends

from backend.app.dependencies import get_aquatwin_service
from backend.app.services.aquatwin_service import AquaTwinService


router = APIRouter(tags=["System"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "aquatwin-x-api",
    }


@router.get("/health/runtime")
def runtime_health_check(
    service: AquaTwinService = Depends(get_aquatwin_service),
) -> dict[str, Any]:
    runtime = service.runtime_status()
    return {
        "status": "ok" if runtime["effective_mode"] in {"real", "demo"} else "unavailable",
        "service": "aquatwin-x-api",
        "runtime": runtime,
    }

