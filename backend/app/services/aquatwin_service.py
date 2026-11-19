import json
import os
import re
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from backend.app.schemas.requests import (
    BaselineSimulationRequest,
    BatchExperimentRequest,
    FailureSimulationRequest,
    ManualRecoveryRequest,
    OptimizationRequest,
)
from backend.app.services.history import RunHistoryStore
from experiments.benchmark import BenchmarkConfig, run_benchmark, write_results
from optimization.genetic import GeneticConfig
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
BUILTIN_NETWORK_DIR = PROJECT_ROOT / "simulation" / "networks"
BUILTIN_VALVE_DIR = PROJECT_ROOT / "simulation" / "valves"
DEFAULT_CUSTOM_NETWORK_DIR = PROJECT_ROOT / "data" / "networks"
DEFAULT_CUSTOM_VALVE_DIR = PROJECT_ROOT / "data" / "valves"
MAX_NETWORK_FILE_SIZE = 5 * 1024 * 1024


class AquaTwinService:
    def __init__(
        self,
        runtime_mode: str | None = None,
        history_store: RunHistoryStore | None = None,
        custom_network_dir: str | Path | None = None,
        custom_valve_dir: str | Path | None = None,
    ) -> None:
        selected_mode = runtime_mode or os.getenv("AQUATWIN_RUNTIME_MODE", "auto")
        self.runtime_mode = selected_mode.strip().lower()
        if self.runtime_mode not in {"auto", "real", "demo"}:
            raise ValueError("AQUATWIN_RUNTIME_MODE must be auto, real, or demo")
        self.history_store = history_store
        self.custom_network_dir = Path(
            custom_network_dir
            or os.getenv("AQUATWIN_CUSTOM_NETWORK_DIR", DEFAULT_CUSTOM_NETWORK_DIR)
        )
        self.custom_valve_dir = Path(
            custom_valve_dir
            or os.getenv("AQUATWIN_CUSTOM_VALVE_DIR", DEFAULT_CUSTOM_VALVE_DIR)
        )

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
        for directory in (BUILTIN_NETWORK_DIR, self.custom_network_dir):
            path = directory / f"{network_id}.inp"
            if path.is_file():
                return path
        raise FileNotFoundError(f"Network '{network_id}' was not found")

    def _valve_path(self, network_id: str) -> Path:
        for directory in (BUILTIN_VALVE_DIR, self.custom_valve_dir):
            path = directory / f"{network_id}_valves.json"
            if path.is_file():
                return path
        raise FileNotFoundError(f"Network '{network_id}' has no valve registry")

    def _valve_registry(self, network_id: str) -> Any:
        return load_valve_registry(self._valve_path(network_id))

    def list_networks(self) -> list[dict[str, Any]]:
        networks: dict[str, dict[str, Any]] = {}
        for source, directory in (
            ("builtin", BUILTIN_NETWORK_DIR),
            ("uploaded", self.custom_network_dir),
        ):
            for path in sorted(directory.glob("*.inp")):
                summary = inspect_inp(path).to_dict()
                summary["source"] = source
                networks.setdefault(str(summary["name"]), summary)
        return sorted(networks.values(), key=lambda item: str(item["name"]))

    def import_network(self, filename: str, content: bytes) -> dict[str, Any]:
        if Path(filename or "").suffix.lower() != ".inp":
            raise ValueError("Only EPANET .inp files are supported")
        if not content:
            raise ValueError("The uploaded network file is empty")
        if len(content) > MAX_NETWORK_FILE_SIZE:
            raise ValueError("The uploaded network file exceeds the 5 MB limit")

        network_id = re.sub(r"[^a-zA-Z0-9_-]+", "_", Path(filename).stem).strip("_-").lower()
        if not network_id:
            raise ValueError("The uploaded file must have a valid network name")
        if (BUILTIN_NETWORK_DIR / f"{network_id}.inp").exists():
            raise FileExistsError(f"Network '{network_id}' is built in and cannot be replaced")

        self.custom_network_dir.mkdir(parents=True, exist_ok=True)
        self.custom_valve_dir.mkdir(parents=True, exist_ok=True)
        network_path = self.custom_network_dir / f"{network_id}.inp"
        valve_path = self.custom_valve_dir / f"{network_id}_valves.json"
        if network_path.exists():
            raise FileExistsError(f"Network '{network_id}' already exists")

        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("The INP file must use UTF-8 compatible text encoding") from exc

        token = uuid4().hex
        temporary_network = self.custom_network_dir / f".{network_id}.{token}.inp"
        temporary_valves = self.custom_valve_dir / f".{network_id}.{token}.json"
        try:
            temporary_network.write_text(text, encoding="utf-8")
            summary = inspect_inp(temporary_network)
            elements = read_inp_elements(temporary_network)
            node_ids = {str(node["id"]) for node in elements["nodes"]}
            pipe_links = [link for link in elements["links"] if link["type"] == "pipe"]
            if summary.total_nodes < 2 or not pipe_links:
                raise ValueError("The INP file must contain at least two nodes and one pipe")
            if summary.reservoirs + summary.tanks < 1:
                raise ValueError("The INP file must contain at least one reservoir or tank")
            if len(node_ids) != len(elements["nodes"]):
                raise ValueError("The INP file contains duplicate node IDs")
            link_ids = [str(link["id"]) for link in elements["links"]]
            if len(set(link_ids)) != len(link_ids):
                raise ValueError("The INP file contains duplicate link IDs")
            if any(
                link["source"] not in node_ids or link["target"] not in node_ids
                for link in elements["links"]
            ):
                raise ValueError("Every link endpoint must reference an existing node")

            valves = [
                {
                    "valve_id": f"V_{link['id']}_{endpoint.upper()}",
                    "link_id": link["id"],
                    "endpoint": endpoint,
                }
                for link in pipe_links
                for endpoint in ("start", "end")
            ]
            temporary_valves.write_text(
                json.dumps({"network": network_id, "valves": valves}, indent=2),
                encoding="utf-8",
            )
            temporary_network.replace(network_path)
            temporary_valves.replace(valve_path)
        except (IndexError, KeyError) as exc:
            raise ValueError("The INP file structure is invalid") from exc
        finally:
            temporary_network.unlink(missing_ok=True)
            temporary_valves.unlink(missing_ok=True)

        return self.get_network(network_id)

    def delete_network(self, network_id: str) -> dict[str, str]:
        network_path = self._network_path(network_id)
        if network_path.parent == BUILTIN_NETWORK_DIR:
            raise PermissionError(f"Built-in network '{network_id}' cannot be deleted")

        network_path.unlink()
        valve_path = self.custom_valve_dir / f"{network_id}_valves.json"
        valve_path.unlink(missing_ok=True)
        return {"network_id": network_id, "status": "deleted"}

    def get_network(self, network_id: str) -> dict[str, Any]:
        path = self._network_path(network_id)
        result = {
            "network": inspect_inp(path).to_dict(),
            "elements": read_inp_elements(path),
            "valves": [],
            "runtime": self.runtime_status(),
        }
        try:
            valve_path = self._valve_path(network_id)
        except FileNotFoundError:
            valve_path = None
        if valve_path is not None:
            result["valves"] = [
                valve.to_dict()
                for valve in load_valve_registry(valve_path).valves
            ]
        result["source"] = "builtin" if path.parent == BUILTIN_NETWORK_DIR else "uploaded"
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

    def run_batch_experiment(
        self,
        request: BatchExperimentRequest,
        output_dir: str | Path,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> dict[str, Any]:
        network_path = self._network_path(request.network_id)
        valve_path = self._valve_path(request.network_id)
        self._valve_registry(request.network_id)
        pipe_ids = {
            link["id"]
            for link in read_inp_elements(network_path)["links"]
            if link["type"] == "pipe"
        }
        missing = sorted(set(request.pipe_ids) - pipe_ids)
        if missing:
            raise ValueError(f"Unknown pipe IDs: {', '.join(missing)}")

        config = BenchmarkConfig(
            network_path=network_path,
            valve_path=valve_path,
            pipe_ids=tuple(request.pipe_ids),
            leak_areas=tuple(request.leak_areas),
            seeds=tuple(request.seeds),
            start_time=request.start_time,
            end_time=request.end_time,
            population_size=request.population_size,
            generations=request.generations,
            max_actions=request.max_actions,
            top_k=request.top_k,
        )
        runtime = self.runtime_status()
        if runtime["effective_mode"] == "unavailable":
            raise RuntimeError(runtime["error"] or "WNTR runtime is unavailable")

        selected_exhaustive_runner = run_exhaustive_search
        selected_ga_runner = run_genetic_search
        if runtime["effective_mode"] == "demo":
            def demo_exhaustive_runner(
                path: Path,
                scenario: Any,
                valve_registry: Any,
                max_actions: int,
                top_k: int,
            ) -> dict[str, Any]:
                return run_demo_optimization(
                    path,
                    scenario,
                    valve_registry,
                    algorithm="exhaustive",
                    max_actions=max_actions,
                    top_k=top_k,
                )

            def demo_ga_runner(
                path: Path,
                scenario: Any,
                valve_registry: Any,
                config: GeneticConfig,
                top_k: int,
            ) -> dict[str, Any]:
                return run_demo_optimization(
                    path,
                    scenario,
                    valve_registry,
                    algorithm="ga",
                    generations=config.generations,
                    seed=config.seed,
                    max_actions=config.max_actions,
                    top_k=top_k,
                )

            selected_exhaustive_runner = demo_exhaustive_runner
            selected_ga_runner = demo_ga_runner

        result = run_benchmark(
            config,
            output_dir,
            exhaustive_runner=selected_exhaustive_runner,
            ga_runner=selected_ga_runner,
            progress_callback=progress_callback,
        )
        result["runtime"] = {
            "mode": runtime["effective_mode"],
            "synthetic_data": runtime["effective_mode"] == "demo",
            "warning": DEMO_WARNING if runtime["effective_mode"] == "demo" else None,
        }
        result["configuration"]["network_id"] = request.network_id
        result.pop("output_files", None)
        for row in result["runs"]:
            row["runtime_mode"] = runtime["effective_mode"]
        json_path, csv_path, summary_path, report_path = write_results(result, output_dir)
        result["output_files"] = {
            "json": str(json_path),
            "csv": str(csv_path),
            "summary": str(summary_path),
            "report": str(report_path),
        }
        return result

