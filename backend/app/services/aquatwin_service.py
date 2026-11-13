from pathlib import Path
from typing import Any

from backend.app.schemas.requests import (
    BaselineSimulationRequest,
    FailureSimulationRequest,
    ManualRecoveryRequest,
    OptimizationRequest,
)
from optimization.ga_runner import run_genetic_search
from optimization.runner import run_exhaustive_search
from simulation.engine import (
    inspect_inp,
    load_valve_registry,
    read_inp_elements,
    run_baseline,
    run_failure,
    run_manual_recovery,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
NETWORK_DIR = PROJECT_ROOT / "simulation" / "networks"
VALVE_DIR = PROJECT_ROOT / "simulation" / "valves"


class AquaTwinService:
    def _network_path(self, network_id: str) -> Path:
        if not network_id or any(
            character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
            for character in network_id
        ):
            raise ValueError("network_id không hợp lệ")
        path = NETWORK_DIR / f"{network_id}.inp"
        if not path.is_file():
            raise FileNotFoundError(f"Không tìm thấy mạng '{network_id}'")
        return path

    def _valve_registry(self, network_id: str) -> Any:
        path = VALVE_DIR / f"{network_id}_valves.json"
        if not path.is_file():
            raise FileNotFoundError(f"Mạng '{network_id}' chưa có lớp dữ liệu van")
        return load_valve_registry(path)

    def list_networks(self) -> list[dict[str, Any]]:
        return [
            inspect_inp(path).to_dict()
            for path in sorted(NETWORK_DIR.glob("*.inp"))
        ]

    def get_network(self, network_id: str) -> dict[str, Any]:
        path = self._network_path(network_id)
        result = {
            "network": inspect_inp(path).to_dict(),
            "elements": read_inp_elements(path),
            "valves": [],
        }
        valve_path = VALVE_DIR / f"{network_id}_valves.json"
        if valve_path.is_file():
            result["valves"] = [
                valve.to_dict()
                for valve in load_valve_registry(valve_path).valves
            ]
        return result

    def run_baseline(self, request: BaselineSimulationRequest) -> dict[str, Any]:
        return run_baseline(self._network_path(request.network_id))

    def run_failure(self, request: FailureSimulationRequest) -> dict[str, Any]:
        return run_failure(
            self._network_path(request.network_id),
            request.scenario.to_domain(),
        )

    def run_manual_recovery(self, request: ManualRecoveryRequest) -> dict[str, Any]:
        return run_manual_recovery(
            self._network_path(request.network_id),
            request.scenario.to_domain(),
            self._valve_registry(request.network_id),
            [action.to_domain() for action in request.actions],
        )

    def optimize(self, request: OptimizationRequest) -> dict[str, Any]:
        network_path = self._network_path(request.network_id)
        scenario = request.scenario.to_domain()
        registry = self._valve_registry(request.network_id)
        if request.algorithm == "exhaustive":
            return run_exhaustive_search(
                network_path,
                scenario,
                registry,
                max_actions=request.max_actions,
                top_k=request.top_k,
            )
        return run_genetic_search(
            network_path,
            scenario,
            registry,
            config=request.to_genetic_config(),
            top_k=request.top_k,
        )

