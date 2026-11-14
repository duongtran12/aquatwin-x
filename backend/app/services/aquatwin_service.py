import os
from pathlib import Path
from typing import Any, Callable

from backend.app.schemas.requests import (
    BaselineSimulationRequest,
    FailureSimulationRequest,
    ManualRecoveryRequest,
    OptimizationRequest,
)
from backend.app.services.history import RunHistoryStore
from optimization.ga_runner import run_genetic_search
from optimization.runner import run_exhaustive_search
from simulation.engine import (
    get_wntr_status,
    inspect_inp,
    load_valve_registry,
    read_inp_elements,
    run_baseline,
    run_failure,
    run_manual_recovery,
)
from simulation.engine.demo import (
    DEMO_WARNING,
    run_demo_baseline,
    run_demo_failure,
    run_demo_manual_recovery,
    run_demo_optimization,
)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
NETWORK_DIR = PROJECT_ROOT / "simulation" / "networks"
VALVE_DIR = PROJECT_ROOT / "simulation" / "valves"


class AquaTwinService:
    def __init__(
        self,
        runtime_mode: str | None = None,
        history_store: RunHistoryStore | None = None,
    ) -> None:
        selected_mode = runtime_mode or os.getenv("AQUATWIN_RUNTIME_MODE", "auto")
        self.runtime_mode = selected_mode.strip().lower()
        if self.runtime_mode not in {"auto", "real", "demo"}:
            raise ValueError("AQUATWIN_RUNTIME_MODE must be auto, real, or demo")
        self.history_store = history_store

    @staticmethod
    def _history_summary(run_type: str, result: dict[str, Any]) -> dict[str, Any]:
        if run_type == "failure":
            metrics = result.get("summary", {})
            actions = []
            score = None
        elif run_type == "manual_recovery":
            metrics = result.get("recovery", {}).get("summary", {})
            actions = result.get("actions", [])
            score = None
        else:
            candidate = result.get("best_candidate") or {}
            metrics = candidate.get("summary", {})
            actions = candidate.get("actions", [])
            score = candidate.get("score")
        return {
            "score": score,
            "minimum_service_availability": metrics.get("minimum_service_availability"),
            "maximum_pressure_violations": metrics.get("maximum_pressure_violations"),
            "maximum_affected_nodes": metrics.get("maximum_affected_nodes"),
            "total_leakage_volume": metrics.get("total_leakage_volume"),
            "action_count": len(actions),
        }

    def _record_result(
        self,
        run_type: str,
        network_id: str,
        pipe_id: str | None,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        if self.history_store is None:
            return result
        metadata = self.history_store.save(
            run_type=run_type,
            network_id=network_id,
            pipe_id=pipe_id,
            runtime_mode=result.get("runtime", {}).get("mode", "unknown"),
            summary=self._history_summary(run_type, result),
            result=result,
        )
        result["history_id"] = metadata["run_id"]
        return result

    def runtime_status(self) -> dict[str, Any]:
        wntr = get_wntr_status()
        if self.runtime_mode == "demo":
            effective_mode = "demo"
        elif self.runtime_mode == "real":
            effective_mode = "real" if wntr["available"] else "unavailable"
        else:
            effective_mode = "real" if wntr["available"] else "demo"
        return {
            "configured_mode": self.runtime_mode,
            "effective_mode": effective_mode,
            "wntr_available": wntr["available"],
            "wntr_version": wntr["version"],
            "error": wntr["error"],
            "synthetic_data": effective_mode == "demo",
        }

    def _execute(
        self,
        real_runner: Callable[[], dict[str, Any]],
        demo_runner: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        if self.runtime_mode == "demo":
            result = demo_runner()
            result["runtime"] = {
                "mode": "demo",
                "synthetic_data": True,
                "warning": DEMO_WARNING,
            }
            return result
        if self.runtime_mode == "real":
            result = real_runner()
            result["runtime"] = {"mode": "real", "synthetic_data": False, "warning": None}
            return result
        try:
            result = real_runner()
        except RuntimeError as exc:
            result = demo_runner()
            result["runtime"] = {
                "mode": "demo",
                "synthetic_data": True,
                "warning": f"{DEMO_WARNING} Runtime detail: {exc}",
            }
            return result
        result["runtime"] = {"mode": "real", "synthetic_data": False, "warning": None}
        return result

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
            "runtime": self.runtime_status(),
        }
        valve_path = VALVE_DIR / f"{network_id}_valves.json"
        if valve_path.is_file():
            result["valves"] = [
                valve.to_dict()
                for valve in load_valve_registry(valve_path).valves
            ]
        return result

    def run_baseline(self, request: BaselineSimulationRequest) -> dict[str, Any]:
        path = self._network_path(request.network_id)
        return self._execute(
            lambda: run_baseline(path),
            lambda: run_demo_baseline(path),
        )

    def run_failure(self, request: FailureSimulationRequest) -> dict[str, Any]:
        path = self._network_path(request.network_id)
        scenario = request.scenario.to_domain()
        result = self._execute(
            lambda: run_failure(path, scenario),
            lambda: run_demo_failure(path, scenario),
        )
        return self._record_result("failure", request.network_id, scenario.pipe_id, result)

    def run_manual_recovery(self, request: ManualRecoveryRequest) -> dict[str, Any]:
        path = self._network_path(request.network_id)
        scenario = request.scenario.to_domain()
        registry = self._valve_registry(request.network_id)
        actions = [action.to_domain() for action in request.actions]
        result = self._execute(
            lambda: run_manual_recovery(path, scenario, registry, actions),
            lambda: run_demo_manual_recovery(path, scenario, registry, actions),
        )
        return self._record_result(
            "manual_recovery",
            request.network_id,
            scenario.pipe_id,
            result,
        )

    def optimize(self, request: OptimizationRequest) -> dict[str, Any]:
        network_path = self._network_path(request.network_id)
        scenario = request.scenario.to_domain()
        registry = self._valve_registry(request.network_id)
        def real_runner() -> dict[str, Any]:
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

        result = self._execute(
            real_runner,
            lambda: run_demo_optimization(
                network_path,
                scenario,
                registry,
                algorithm=request.algorithm,
                generations=request.generations,
                seed=request.seed,
                max_actions=request.max_actions,
                top_k=request.top_k,
            ),
        )
        return self._record_result(
            "optimization",
            request.network_id,
            scenario.pipe_id,
            result,
        )

