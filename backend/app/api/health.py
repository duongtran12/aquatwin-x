from typing import Any

from fastapi import APIRouter, Depends

from backend.app.dependencies import get_aquatwin_service
from backend.app.config import get_settings
from backend.app.services.aquatwin_service import AquaTwinService


router = APIRouter(tags=["System"])


@router.get("/health")
def health_check() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "service": "aquatwin-x-api",
        "version": settings.aquatwin_version,
        "build_commit": settings.aquatwin_build_commit,
    }


@router.get("/health/runtime")
def runtime_health_check(
    service: AquaTwinService = Depends(get_aquatwin_service),
) -> dict[str, Any]:
    runtime = service.runtime_status()
    settings = get_settings()
    return {
        "status": "ok" if runtime["effective_mode"] in {"real", "demo"} else "unavailable",
        "service": "aquatwin-x-api",
        "version": settings.aquatwin_version,
        "build_commit": settings.aquatwin_build_commit,
        "runtime": runtime,
    }

