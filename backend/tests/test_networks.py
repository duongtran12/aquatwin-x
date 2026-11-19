from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.dependencies import get_aquatwin_service
from backend.app.main import app
from backend.app.services.aquatwin_service import AquaTwinService


client = TestClient(app)


def test_lists_demo_network() -> None:
    response = client.get("/api/networks")

    assert response.status_code == 200
    assert "aquatwin_demo" in {item["name"] for item in response.json()}


def test_gets_network_elements_and_valves() -> None:
    response = client.get("/api/networks/aquatwin_demo")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["elements"]["nodes"]) == 5
    assert len(payload["elements"]["links"]) == 6
    assert len(payload["valves"]) == 12


def test_returns_not_found_for_unknown_network() -> None:
    response = client.get("/api/networks/unknown")

    assert response.status_code == 404


def test_lists_larger_benchmark_network() -> None:
    response = client.get("/api/networks/aquatwin_benchmark")
    assert response.status_code == 200
    payload = response.json()
    assert payload["network"]["junctions"] == 12
    assert payload["network"]["pipes"] == 21
    assert len(payload["valves"]) == 42


def test_imports_network_and_generates_virtual_valves(tmp_path: Path) -> None:
    service = AquaTwinService(
        "demo",
        custom_network_dir=tmp_path / "networks",
        custom_valve_dir=tmp_path / "valves",
    )
    app.dependency_overrides[get_aquatwin_service] = lambda: service
    source = Path("simulation/networks/aquatwin_demo.inp").read_bytes()
    try:
        response = client.post(
            "/api/networks/import",
            files={"file": ("City Pilot.inp", source, "application/octet-stream")},
        )
        duplicate = client.post(
            "/api/networks/import",
            files={"file": ("City Pilot.inp", source, "application/octet-stream")},
        )
        listing = client.get("/api/networks")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["network"]["name"] == "city_pilot"
    assert response.json()["source"] == "uploaded"
    assert len(response.json()["valves"]) == 12
    assert duplicate.status_code == 409
    assert "city_pilot" in {item["name"] for item in listing.json()}
    assert (tmp_path / "networks" / "city_pilot.inp").is_file()
    assert (tmp_path / "valves" / "city_pilot_valves.json").is_file()


def test_rejects_invalid_network_upload(tmp_path: Path) -> None:
    service = AquaTwinService(
        "demo",
        custom_network_dir=tmp_path / "networks",
        custom_valve_dir=tmp_path / "valves",
    )
    app.dependency_overrides[get_aquatwin_service] = lambda: service
    try:
        response = client.post(
            "/api/networks/import",
            files={"file": ("notes.txt", b"not an inp", "text/plain")},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert "Only EPANET .inp" in response.json()["detail"]


def test_deletes_only_uploaded_networks(tmp_path: Path) -> None:
    service = AquaTwinService(
        "demo",
        custom_network_dir=tmp_path / "networks",
        custom_valve_dir=tmp_path / "valves",
    )
    app.dependency_overrides[get_aquatwin_service] = lambda: service
    source = Path("simulation/networks/aquatwin_demo.inp").read_bytes()
    try:
        imported = client.post(
            "/api/networks/import",
            files={"file": ("Temporary.inp", source, "application/octet-stream")},
        )
        deleted = client.delete("/api/networks/temporary")
        missing = client.get("/api/networks/temporary")
        protected = client.delete("/api/networks/aquatwin_demo")
    finally:
        app.dependency_overrides.clear()

    assert imported.status_code == 201
    assert deleted.status_code == 200
    assert deleted.json() == {"network_id": "temporary", "status": "deleted"}
    assert missing.status_code == 404
    assert protected.status_code == 403
    assert not (tmp_path / "networks" / "temporary.inp").exists()
    assert not (tmp_path / "valves" / "temporary_valves.json").exists()

