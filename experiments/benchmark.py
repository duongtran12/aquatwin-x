import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Callable

from optimization.ga_runner import run_genetic_search
from optimization.genetic import GeneticConfig
from optimization.runner import run_exhaustive_search
from simulation.engine import LeakScenario, load_valve_registry


SearchRunner = Callable[..., dict[str, Any]]


@dataclass(frozen=True)
class BenchmarkConfig:
    network_path: Path
    valve_path: Path
    pipe_ids: tuple[str, ...]
    leak_areas: tuple[float, ...]
    seeds: tuple[int, ...]
    start_time: int = 7200
    end_time: int = 43200
    split_position: float = 0.5
    discharge_coefficient: float = 0.75
    pressure_drop_threshold: float = 2.0
    population_size: int = 20
    generations: int = 20
    max_actions: int = 2
    top_k: int = 5

    @classmethod
    def from_json(cls, config_path: str | Path) -> "BenchmarkConfig":
        path = Path(config_path).resolve()
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        base = path.parent

        def resolve(value: str) -> Path:
            candidate = Path(value)
            return candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()

        return cls(
            network_path=resolve(payload["network_path"]),
            valve_path=resolve(payload["valve_path"]),
            pipe_ids=tuple(str(item) for item in payload["pipe_ids"]),
            leak_areas=tuple(float(item) for item in payload["leak_areas"]),
            seeds=tuple(int(item) for item in payload["seeds"]),
            start_time=int(payload.get("start_time", 7200)),
            end_time=int(payload.get("end_time", 43200)),
            split_position=float(payload.get("split_position", 0.5)),
            discharge_coefficient=float(payload.get("discharge_coefficient", 0.75)),
            pressure_drop_threshold=float(payload.get("pressure_drop_threshold", 2.0)),
            population_size=int(payload.get("population_size", 20)),
            generations=int(payload.get("generations", 20)),
            max_actions=int(payload.get("max_actions", 2)),
            top_k=int(payload.get("top_k", 5)),
        )


def build_scenarios(config: BenchmarkConfig) -> list[tuple[str, LeakScenario]]:
    scenarios = []
    for pipe_id in config.pipe_ids:
        for index, leak_area in enumerate(config.leak_areas, start=1):
            scenario_id = f"{pipe_id}_L{index}"
            scenarios.append(
                (
                    scenario_id,
                    LeakScenario(
                        pipe_id=pipe_id,
                        leak_area=leak_area,
                        start_time=config.start_time,
                        end_time=config.end_time,
                        split_position=config.split_position,
                        discharge_coefficient=config.discharge_coefficient,
                        pressure_drop_threshold=config.pressure_drop_threshold,
                    ),
                )
            )
    return scenarios


def _actions_text(candidate: dict[str, Any] | None) -> str:
    if not candidate:
        return ""
    return ";".join(
        f"{action['valve_id']}:{action['status']}"
        for action in candidate.get("actions", [])
    )


def _result_row(
    scenario_id: str,
    scenario: LeakScenario,
    method: str,
    candidate: dict[str, Any] | None,
    computation_time: float,
    evaluated_count: int | None,
    failure_summary: dict[str, Any],
    seed: int | None = None,
    exhaustive_score: float | None = None,
) -> dict[str, Any]:
    summary = (candidate or {}).get("summary", {})
    score = (candidate or {}).get("score")
    gap = None if score is None or exhaustive_score is None else exhaustive_score - float(score)
    return {
        "scenario_id": scenario_id,
        "pipe_id": scenario.pipe_id,
        "leak_area": scenario.leak_area,
        "method": method,
        "seed": seed,
        "score": score,
        "score_gap_to_exhaustive": gap,
        "found_global_optimum": None if gap is None else abs(gap) <= 1e-6,
        "failure_minimum_service_availability": failure_summary.get("minimum_service_availability"),
        "failure_maximum_pressure_violations": failure_summary.get("maximum_pressure_violations"),
        "failure_maximum_affected_nodes": failure_summary.get("maximum_affected_nodes"),
        "failure_total_leakage_volume": failure_summary.get("total_leakage_volume"),
        "recovery_minimum_service_availability": summary.get("minimum_service_availability"),
        "recovery_maximum_pressure_violations": summary.get("maximum_pressure_violations"),
        "recovery_maximum_affected_nodes": summary.get("maximum_affected_nodes"),
        "recovery_total_leakage_volume": summary.get("total_leakage_volume"),
        "action_count": len((candidate or {}).get("actions", [])),
        "actions": _actions_text(candidate),
        "evaluated_count": evaluated_count,
        "computation_time_seconds": computation_time,
    }


def summarize_runs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["method"]].append(row)

    summary = {}
    for method, method_rows in grouped.items():
        scores = [float(row["score"]) for row in method_rows if row["score"] is not None]
        times = [float(row["computation_time_seconds"]) for row in method_rows]
        method_summary: dict[str, Any] = {
            "run_count": len(method_rows),
            "mean_score": mean(scores) if scores else None,
            "mean_computation_time_seconds": mean(times) if times else None,
        }
        optimum_flags = [row["found_global_optimum"] for row in method_rows if row["found_global_optimum"] is not None]
        if optimum_flags:
            method_summary["global_optimum_hit_rate"] = sum(optimum_flags) / len(optimum_flags)
        summary[method] = method_summary
    return summary


def write_results(result: dict[str, Any], output_dir: str | Path) -> tuple[Path, Path]:
    target = Path(output_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    json_path = target / "benchmark_results.json"
    csv_path = target / "benchmark_runs.csv"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = result["runs"]
    if rows:
        with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    return json_path, csv_path


def run_benchmark(
    config: BenchmarkConfig,
    output_dir: str | Path,
    exhaustive_runner: SearchRunner = run_exhaustive_search,
    ga_runner: SearchRunner = run_genetic_search,
) -> dict[str, Any]:
    registry = load_valve_registry(config.valve_path)
    rows: list[dict[str, Any]] = []
    scenario_payloads = []

    for scenario_id, scenario in build_scenarios(config):
        exhaustive = exhaustive_runner(
            config.network_path,
            scenario,
            registry,
            max_actions=config.max_actions,
            top_k=config.top_k,
        )
        exhaustive_best = exhaustive.get("best_candidate")
        exhaustive_score = float(exhaustive_best["score"]) if exhaustive_best else None
        failure_summary = exhaustive.get("failure_summary", {})
        scenario_payloads.append({
            "scenario_id": scenario_id,
            **scenario.to_dict(),
            "failure_summary": failure_summary,
        })
        baseline = exhaustive.get("isolation_baseline")
        rows.append(
            _result_row(
                scenario_id,
                scenario,
                "isolation_baseline",
                baseline,
                float((baseline or {}).get("computation_time_seconds", 0)),
                1,
                failure_summary,
                exhaustive_score=exhaustive_score,
            )
        )
        rows.append(
            _result_row(
                scenario_id,
                scenario,
                "exhaustive_search",
                exhaustive_best,
                float(exhaustive.get("computation_time_seconds", 0)),
                exhaustive.get("candidate_count"),
                failure_summary,
                exhaustive_score=exhaustive_score,
            )
        )

        for seed in config.seeds:
            genetic = ga_runner(
                config.network_path,
                scenario,
                registry,
                config=GeneticConfig(
                    population_size=config.population_size,
                    generations=config.generations,
                    max_actions=config.max_actions,
                    seed=seed,
                ),
                top_k=config.top_k,
            )
            rows.append(
                _result_row(
                    scenario_id,
                    scenario,
                    "genetic_algorithm",
                    genetic.get("best_candidate"),
                    float(genetic.get("computation_time_seconds", 0)),
                    genetic.get("unique_evaluated_count"),
                    failure_summary,
                    seed=seed,
                    exhaustive_score=exhaustive_score,
                )
            )

    result = {
        "configuration": {
            "network_file": config.network_path.name,
            "valve_file": config.valve_path.name,
            "scenario_count": len(scenario_payloads),
            "seeds": list(config.seeds),
            "population_size": config.population_size,
            "generations": config.generations,
            "max_actions": config.max_actions,
        },
        "scenarios": scenario_payloads,
        "runs": rows,
        "summary": summarize_runs(rows),
    }
    json_path, csv_path = write_results(result, output_dir)
    result["output_files"] = {"json": str(json_path), "csv": str(csv_path)}
    return result
