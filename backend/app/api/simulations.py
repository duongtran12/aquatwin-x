from typing import Any

from fastapi import APIRouter, Depends

from backend.app.dependencies import get_aquatwin_service
from backend.app.schemas.requests import (
    BaselineSimulationRequest,
    FailureSimulationRequest,
    ManualRecoveryRequest,
)
from backend.app.services.aquatwin_service import AquaTwinService


router = APIRouter(prefix="/simulations", tags=["Simulations"])


@router.post("/baseline")
def simulate_baseline(
    request: BaselineSimulationRequest,
    service: AquaTwinService = Depends(get_aquatwin_service),
) -> dict[str, Any]:
    return service.run_baseline(request)


@router.post("/failure")
def simulate_failure(
    request: FailureSimulationRequest,
    service: AquaTwinService = Depends(get_aquatwin_service),
) -> dict[str, Any]:
    return service.run_failure(request)


@router.post("/what-if")
def simulate_manual_recovery(
    request: ManualRecoveryRequest,
    service: AquaTwinService = Depends(get_aquatwin_service),
) -> dict[str, Any]:
    return service.run_manual_recovery(request)

