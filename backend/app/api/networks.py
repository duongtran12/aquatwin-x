from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from backend.app.dependencies import get_aquatwin_service
from backend.app.services.aquatwin_service import (
    AquaTwinService,
    MAX_NETWORK_FILE_SIZE,
    MAX_VALVE_REGISTRY_SIZE,
)


router = APIRouter(prefix="/networks", tags=["Networks"])


@router.get("")
def list_networks(
    service: AquaTwinService = Depends(get_aquatwin_service),
) -> list[dict[str, Any]]:
    return service.list_networks()


@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_network(
    file: UploadFile = File(...),
    service: AquaTwinService = Depends(get_aquatwin_service),
) -> dict[str, Any]:
    try:
        content = await file.read(MAX_NETWORK_FILE_SIZE + 1)
        return service.import_network(file.filename or "", content)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{network_id}")
def get_network(
    network_id: str,
    service: AquaTwinService = Depends(get_aquatwin_service),
) -> dict[str, Any]:
    return service.get_network(network_id)


@router.post("/{network_id}/valves/import")
async def import_valve_registry(
    network_id: str,
    file: UploadFile = File(...),
    service: AquaTwinService = Depends(get_aquatwin_service),
) -> dict[str, Any]:
    try:
        content = await file.read(MAX_VALVE_REGISTRY_SIZE + 1)
        return service.import_valve_registry(
            network_id,
            file.filename or "",
            content,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.delete("/{network_id}")
def delete_network(
    network_id: str,
    service: AquaTwinService = Depends(get_aquatwin_service),
) -> dict[str, str]:
    try:
        return service.delete_network(network_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

