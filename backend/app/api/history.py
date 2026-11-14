import csv
import io
import json
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from backend.app.dependencies import get_history_store
from backend.app.services.history import RunHistoryStore


router = APIRouter(prefix="/history", tags=["History"])


@router.get("")
def list_history(
    limit: int = Query(default=20, ge=1, le=100),
    store: RunHistoryStore = Depends(get_history_store),
) -> list[dict[str, Any]]:
    return store.list(limit)


@router.get("/{run_id}")
def get_history_item(
    run_id: str,
    store: RunHistoryStore = Depends(get_history_store),
) -> dict[str, Any]:
    try:
        return store.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="History item not found") from exc


@router.get("/{run_id}/download")
def download_history_item(
    run_id: str,
    format: Literal["json", "csv"] = "json",
    store: RunHistoryStore = Depends(get_history_store),
) -> Response:
    try:
        item = store.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="History item not found") from exc

    if format == "json":
        content = json.dumps(item, ensure_ascii=False, indent=2)
        media_type = "application/json"
    else:
        stream = io.StringIO()
        summary = item["summary"]
        row = {
            "run_id": item["run_id"],
            "run_type": item["run_type"],
            "network_id": item["network_id"],
            "pipe_id": item["pipe_id"],
            "runtime_mode": item["runtime_mode"],
            "created_at": item["created_at"],
            **summary,
        }
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
        content = stream.getvalue()
        media_type = "text/csv"

    filename = f"aquatwin-{run_id}.{format}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
