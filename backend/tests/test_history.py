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


def test_history_store_filters_archive_fields() -> None:
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
        store = RunHistoryStore(Path(directory) / "history.db")
        store.save("failure", "network_a", "P1", "demo", {}, sample_result())
        expected = store.save(
            "optimization",
            "network_b",
            "P2",
            "real",
            {"score": 90.0},
            sample_result(),
        )

        filtered = store.list(
            network_id="network_b",
            run_type="optimization",
            runtime_mode="real",
        )
        no_matches = store.list(network_id="network_a", runtime_mode="real")

    assert [item["run_id"] for item in filtered] == [expected["run_id"]]
    assert no_matches == []


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
        html_report = client.get(f"/api/history/{saved['run_id']}/download?format=html")
        app.dependency_overrides.clear()
    assert listing.status_code == 200
    assert listing.json()[0]["run_id"] == saved["run_id"]
    assert json_download.headers["content-type"].startswith("application/json")
    assert "aquatwin_demo" in json_download.text
    assert csv_download.headers["content-type"].startswith("text/csv")
    assert "maximum_affected_nodes" in csv_download.text
    assert html_report.headers["content-type"].startswith("text/html")
    assert html_report.headers["content-disposition"].startswith("inline")
    assert "AQUATWIN-X DECISION EVIDENCE" in html_report.text
    assert "Synthetic demo result" in html_report.text
    assert "aquatwin_demo" in html_report.text


def test_optimization_report_includes_reproducibility_settings() -> None:
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
        store = RunHistoryStore(Path(directory) / "history.db")
        saved = store.save(
            "optimization",
            "aquatwin_demo",
            "P3",
            "real",
            {"score": 92.5},
            {
                "algorithm": "genetic_algorithm",
                "scenario": {
                    "pipe_id": "P3",
                    "leak_area": 0.0005,
                    "start_time": 7200,
                    "end_time": 43200,
                },
                "config": {
                    "population_size": 24,
                    "generations": 30,
                    "max_actions": 2,
                    "seed": 101,
                    "crossover_rate": 0.8,
                    "mutation_rate": 0.1,
                },
                "best_candidate": {"score": 92.5, "actions": [], "summary": {}},
            },
        )
        app.dependency_overrides[get_history_store] = lambda: store
        response = TestClient(app).get(
            f"/api/history/{saved['run_id']}/download?format=html"
        )
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "Optimization settings" in response.text
    assert "genetic_algorithm" in response.text
    assert "Population" in response.text
    assert ">24<" in response.text
    assert "Generations" in response.text
    assert ">30<" in response.text
    assert "Random seed" in response.text
    assert ">101<" in response.text


def test_history_api_returns_not_found() -> None:
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
        store = RunHistoryStore(Path(directory) / "history.db")
        app.dependency_overrides[get_history_store] = lambda: store
        response = TestClient(app).get("/api/history/missing")
        app.dependency_overrides.clear()
    assert response.status_code == 404


def test_history_api_supports_combined_filters() -> None:
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
        store = RunHistoryStore(Path(directory) / "history.db")
        store.save("failure", "network_a", "P1", "demo", {}, sample_result())
        expected = store.save("optimization", "network_b", "P2", "real", {}, sample_result())
        app.dependency_overrides[get_history_store] = lambda: store
        response = TestClient(app).get(
            "/api/history?network_id=network_b&run_type=optimization&runtime_mode=real"
        )
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert [item["run_id"] for item in response.json()] == [expected["run_id"]]


def test_history_analytics_aggregates_recovery_and_runtime_modes() -> None:
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
        store = RunHistoryStore(Path(directory) / "history.db")
        failure = {
            "minimum_service_availability": 0.70,
            "maximum_pressure_violations": 3,
            "maximum_affected_nodes": 4,
            "total_leakage_volume": 100.0,
        }
        recovery = {
            "minimum_service_availability": 0.92,
            "maximum_pressure_violations": 1,
            "maximum_affected_nodes": 1,
            "total_leakage_volume": 25.0,
        }
        store.save(
            "manual_recovery",
            "aquatwin_demo",
            "P3",
            "demo",
            {**recovery, "score": None, "action_count": 2},
            {"failure": {"summary": failure}, "recovery": {"summary": recovery}},
        )
        store.save(
            "optimization",
            "aquatwin_demo",
            "P3",
            "real",
            {**recovery, "score": 91.5, "action_count": 2},
            {"failure_summary": failure, "best_candidate": {"score": 91.5, "summary": recovery}},
        )
        analytics = store.analytics()
        real_only = store.analytics("real")
    assert analytics["total_runs"] == 2
    assert analytics["runtime_counts"] == {"demo": 1, "real": 1}
    assert analytics["optimization"]["best_score"] == 91.5
    assert analytics["recovery"]["average_leakage_reduction"] == 75.0
    assert analytics["by_pipe"][0]["runs"] == 2
    assert real_only["total_runs"] == 1


def test_history_analytics_api_supports_runtime_filter() -> None:
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
        store = RunHistoryStore(Path(directory) / "history.db")
        store.save("failure", "aquatwin_demo", "P2", "demo", {}, sample_result())
        app.dependency_overrides[get_history_store] = lambda: store
        response = TestClient(app).get("/api/history/analytics?runtime_mode=demo")
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["filter"]["runtime_mode"] == "demo"
    assert response.json()["total_runs"] == 1
