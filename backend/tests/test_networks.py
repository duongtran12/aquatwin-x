from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_lists_demo_network() -> None:
    response = client.get("/api/networks")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "aquatwin_demo"


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

