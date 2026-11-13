from typing import Any

from fastapi import APIRouter, Depends

from backend.app.dependencies import get_aquatwin_service
from backend.app.services.aquatwin_service import AquaTwinService


router = APIRouter(prefix="/networks", tags=["Networks"])


@router.get("")
def list_networks(
    service: AquaTwinService = Depends(get_aquatwin_service),
) -> list[dict[str, Any]]:
    return service.list_networks()


@router.get("/{network_id}")
def get_network(
    network_id: str,
    service: AquaTwinService = Depends(get_aquatwin_service),
) -> dict[str, Any]:
    return service.get_network(network_id)

