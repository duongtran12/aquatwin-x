from backend.app.services.aquatwin_service import AquaTwinService
from backend.app.schemas.requests import FailureSimulationRequest, LeakScenarioPayload


def test_demo_runtime_is_explicitly_labeled() -> None:
    service = AquaTwinService("demo")
    status = service.runtime_status()
    assert status["effective_mode"] == "demo"
    assert status["synthetic_data"] is True


def test_demo_failure_response_contains_warning() -> None:
    service = AquaTwinService("demo")
    request = FailureSimulationRequest(
        network_id="aquatwin_demo",
        scenario=LeakScenarioPayload(
            pipe_id="P3",
            leak_area=0.0005,
            start_time=7200,
            end_time=43200,
        ),
    )
    result = service.run_failure(request)
    assert result["runtime"]["mode"] == "demo"
    assert result["runtime"]["synthetic_data"] is True
    assert "Do not use" in result["runtime"]["warning"]


def test_rejects_unknown_runtime_mode() -> None:
    try:
        AquaTwinService("unknown")
    except ValueError as exc:
        assert "auto, real, or demo" in str(exc)
    else:
        raise AssertionError("Invalid runtime mode was accepted")
