import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.dependencies import get_history_store
from backend.app.main import app
from backend.app.services.history import RunHistoryStore


def sample_result() -> dict:
    return {
        "runtime": {"mode": "demo", "synthetic_data": True},
        "summary": {"maximum_affected_nodes": 3},
    }


def test_history_store_saves_lists_and_reads_runs() -> None:
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
        store = RunHistoryStore(Path(directory) / "history.db")
        saved = store.save(
            "failure",
            "aquatwin_demo",
            "P3",
            "demo",
            {"maximum_affected_nodes": 3},
            sample_result(),
        )
        rows = store.list()
        item = store.get(saved["run_id"])
    assert len(rows) == 1
    assert rows[0]["runtime_mode"] == "demo"
    assert item["result"]["summary"]["maximum_affected_nodes"] == 3


def test_history_api_lists_and_downloads_json_and_csv() -> None:
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
        store = RunHistoryStore(Path(directory) / "history.db")
        saved = store.save(
            "failure",
            "aquatwin_demo",
            "P3",
            "demo",
            {"maximum_affected_nodes": 3, "score": None},
            sample_result(),
        )
        app.dependency_overrides[get_history_store] = lambda: store
        client = TestClient(app)
        listing = client.get("/api/history")
        json_download = client.get(f"/api/history/{saved['run_id']}/download?format=json")
        csv_download = client.get(f"/api/history/{saved['run_id']}/download?format=csv")
        app.dependency_overrides.clear()
    assert listing.status_code == 200
    assert listing.json()[0]["run_id"] == saved["run_id"]
    assert json_download.headers["content-type"].startswith("application/json")
    assert "aquatwin_demo" in json_download.text
    assert csv_download.headers["content-type"].startswith("text/csv")
    assert "maximum_affected_nodes" in csv_download.text


def test_history_api_returns_not_found() -> None:
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
        store = RunHistoryStore(Path(directory) / "history.db")
        app.dependency_overrides[get_history_store] = lambda: store
        response = TestClient(app).get("/api/history/missing")
        app.dependency_overrides.clear()
    assert response.status_code == 404
