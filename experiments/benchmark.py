import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any, Callable

from optimization.ga_runner import run_genetic_search
from optimization.genetic import GeneticConfig
from optimization.runner import run_exhaustive_search
from simulation.engine import LeakScenario, load_valve_registry


SearchRunner = Callable[..., dict[str, Any]]
ProgressCallback = Callable[[int, int, str], None]


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
            "median_score": median(scores) if scores else None,
            "score_standard_deviation": pstdev(scores) if len(scores) > 1 else 0.0 if scores else None,
            "mean_computation_time_seconds": mean(times) if times else None,
        }
        optimum_flags = [row["found_global_optimum"] for row in method_rows if row["found_global_optimum"] is not None]
        if optimum_flags:
            method_summary["global_optimum_hit_rate"] = sum(optimum_flags) / len(optimum_flags)
        summary[method] = method_summary
    return summary


def summarize_scenarios(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["scenario_id"]].append(row)

    scenarios = []
    for scenario_id, scenario_rows in grouped.items():
        exhaustive = next(row for row in scenario_rows if row["method"] == "exhaustive_search")
        baseline = next(row for row in scenario_rows if row["method"] == "isolation_baseline")
        ga_rows = [row for row in scenario_rows if row["method"] == "genetic_algorithm"]
        ga_scores = [float(row["score"]) for row in ga_rows if row["score"] is not None]
        ga_gaps = [float(row["score_gap_to_exhaustive"]) for row in ga_rows if row["score_gap_to_exhaustive"] is not None]
        ga_times = [float(row["computation_time_seconds"]) for row in ga_rows]
        ga_counts = [float(row["evaluated_count"]) for row in ga_rows if row["evaluated_count"] is not None]
        exhaustive_time = float(exhaustive["computation_time_seconds"])
        exhaustive_count = float(exhaustive["evaluated_count"] or 0)
        mean_ga_time = mean(ga_times) if ga_times else None
        mean_ga_count = mean(ga_counts) if ga_counts else None
        best_ga = max(
            ga_rows,
            key=lambda row: (
                float(row["score"]) if row["score"] is not None else float("-inf"),
                -float(row["computation_time_seconds"]),
            ),
            default=None,
        )
        scenarios.append({
            "scenario_id": scenario_id,
            "pipe_id": exhaustive["pipe_id"],
            "leak_area": exhaustive["leak_area"],
            "failure_minimum_service_availability": exhaustive["failure_minimum_service_availability"],
            "failure_total_leakage_volume": exhaustive["failure_total_leakage_volume"],
            "baseline_score": baseline["score"],
            "exhaustive_score": exhaustive["score"],
            "ga_mean_score": mean(ga_scores) if ga_scores else None,
            "ga_best_score": max(ga_scores) if ga_scores else None,
            "ga_best_seed": (best_ga or {}).get("seed"),
            "ga_mean_score_gap": mean(ga_gaps) if ga_gaps else None,
            "ga_maximum_score_gap": max(ga_gaps) if ga_gaps else None,
            "ga_global_optimum_hit_rate": (
                sum(bool(row["found_global_optimum"]) for row in ga_rows) / len(ga_rows)
                if ga_rows else None
            ),
            "ga_within_one_point_rate": (
                sum(gap <= 1.0 for gap in ga_gaps) / len(ga_gaps)
                if ga_gaps else None
            ),
            "exhaustive_evaluated_count": exhaustive["evaluated_count"],
            "ga_mean_evaluated_count": mean_ga_count,
            "candidate_reduction_rate": (
                1 - mean_ga_count / exhaustive_count
                if mean_ga_count is not None and exhaustive_count > 0 else None
            ),
            "exhaustive_time_seconds": exhaustive_time,
            "ga_mean_time_seconds": mean_ga_time,
            "ga_speedup": (
                exhaustive_time / mean_ga_time
                if mean_ga_time is not None and mean_ga_time > 0 else None
            ),
        })
    return scenarios


def summarize_evaluation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ga_rows = [row for row in rows if row["method"] == "genetic_algorithm"]
    gaps = [float(row["score_gap_to_exhaustive"]) for row in ga_rows if row["score_gap_to_exhaustive"] is not None]
    scenarios = summarize_scenarios(rows)
    speedups = [float(item["ga_speedup"]) for item in scenarios if item["ga_speedup"] is not None]
    reductions = [float(item["candidate_reduction_rate"]) for item in scenarios if item["candidate_reduction_rate"] is not None]
    return {
        "overall": {
            "scenario_count": len(scenarios),
            "ga_run_count": len(ga_rows),
            "mean_score_gap": mean(gaps) if gaps else None,
            "maximum_score_gap": max(gaps) if gaps else None,
            "global_optimum_hit_rate": (
                sum(bool(row["found_global_optimum"]) for row in ga_rows) / len(ga_rows)
                if ga_rows else None
            ),
            "within_one_point_rate": sum(gap <= 1.0 for gap in gaps) / len(gaps) if gaps else None,
            "mean_speedup": mean(speedups) if speedups else None,
            "mean_candidate_reduction_rate": mean(reductions) if reductions else None,
        },
        "scenarios": scenarios,
    }


def _display(value: Any, digits: int = 3) -> str:
    return "--" if value is None else f"{float(value):.{digits}f}"


def render_markdown_report(result: dict[str, Any]) -> str:
    config = result["configuration"]
    methods = result["summary"]
    evaluation = result["evaluation"]["overall"]
    scenarios = result["evaluation"]["scenarios"]
    runtime_mode = result.get("runtime", {}).get("mode", "direct real runner")
    lines = [
        "# AquaTwin-X Benchmark Report",
        "",
        "## Experiment configuration",
        "",
        f"- Network: `{config['network_file']}`",
        f"- Runtime: `{runtime_mode}`",
        f"- Scenarios: {config['scenario_count']}",
        f"- GA seeds: {', '.join(str(seed) for seed in config['seeds'])}",
        f"- Population / generations: {config['population_size']} / {config['generations']}",
        f"- Maximum valve actions: {config['max_actions']}",
        "",
        "## Method-level results",
        "",
        "| Method | Runs | Mean score | Median score | Score SD | Mean time (s) | Optimum hit rate |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for method in ("isolation_baseline", "exhaustive_search", "genetic_algorithm"):
        item = methods.get(method, {})
        hit_rate = item.get("global_optimum_hit_rate")
        lines.append(
            f"| {method.replace('_', ' ').title()} | {item.get('run_count', 0)} | "
            f"{_display(item.get('mean_score'))} | {_display(item.get('median_score'))} | "
            f"{_display(item.get('score_standard_deviation'))} | "
            f"{_display(item.get('mean_computation_time_seconds'))} | "
            f"{'--' if hit_rate is None else f'{hit_rate:.1%}'} |"
        )
    lines.extend([
        "",
        "## GA compared with exhaustive search",
        "",
        f"- Mean score gap: {_display(evaluation['mean_score_gap'])} points",
        f"- Maximum score gap: {_display(evaluation['maximum_score_gap'])} points",
        f"- Global-optimum hit rate: {_display(evaluation['global_optimum_hit_rate'] * 100 if evaluation['global_optimum_hit_rate'] is not None else None, 1)}%",
        f"- Within-one-point rate: {_display(evaluation['within_one_point_rate'] * 100 if evaluation['within_one_point_rate'] is not None else None, 1)}%",
        f"- Mean speedup: {_display(evaluation['mean_speedup'])}x",
        f"- Mean candidate reduction: {_display(evaluation['mean_candidate_reduction_rate'] * 100 if evaluation['mean_candidate_reduction_rate'] is not None else None, 1)}%",
        "",
        "## Scenario-level comparison",
        "",
        "| Scenario | Pipe | Leak area | Exhaustive | GA mean | Mean gap | Hit rate | Speedup | Candidate reduction |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for item in scenarios:
        lines.append(
            f"| {item['scenario_id']} | {item['pipe_id']} | {_display(item['leak_area'], 6)} | "
            f"{_display(item['exhaustive_score'])} | {_display(item['ga_mean_score'])} | "
            f"{_display(item['ga_mean_score_gap'])} | "
            f"{_display(item['ga_global_optimum_hit_rate'] * 100 if item['ga_global_optimum_hit_rate'] is not None else None, 1)}% | "
            f"{_display(item['ga_speedup'])}x | "
            f"{_display(item['candidate_reduction_rate'] * 100 if item['candidate_reduction_rate'] is not None else None, 1)}% |"
        )
    lines.extend([
        "",
        "> Results are generated from the configured runtime. Demo-mode outputs are synthetic and must not be cited as hydraulic evidence.",
        "",
    ])
    return "\n".join(lines)


def write_results(result: dict[str, Any], output_dir: str | Path) -> tuple[Path, Path, Path, Path]:
    target = Path(output_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    json_path = target / "benchmark_results.json"
    csv_path = target / "benchmark_runs.csv"
    summary_path = target / "benchmark_summary.csv"
    report_path = target / "benchmark_report.md"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = result["runs"]
    if rows:
        with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    scenario_rows = result["evaluation"]["scenarios"]
    if scenario_rows:
        with summary_path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(scenario_rows[0]))
            writer.writeheader()
            writer.writerows(scenario_rows)
    report_path.write_text(render_markdown_report(result), encoding="utf-8")
    return json_path, csv_path, summary_path, report_path


def run_benchmark(
    config: BenchmarkConfig,
    output_dir: str | Path,
    exhaustive_runner: SearchRunner = run_exhaustive_search,
    ga_runner: SearchRunner = run_genetic_search,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    registry = load_valve_registry(config.valve_path)
    rows: list[dict[str, Any]] = []
    scenario_payloads = []
    scenarios = build_scenarios(config)
    total_steps = len(scenarios) * (2 + len(config.seeds))
    completed_steps = 0

    for scenario_id, scenario in scenarios:
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
        completed_steps += 2
        if progress_callback:
            progress_callback(
                completed_steps,
                total_steps,
                f"Completed baseline and exhaustive search for {scenario_id}",
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
            completed_steps += 1
            if progress_callback:
                progress_callback(
                    completed_steps,
                    total_steps,
                    f"Completed GA seed {seed} for {scenario_id}",
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
        "evaluation": summarize_evaluation(rows),
    }
    json_path, csv_path, summary_path, report_path = write_results(result, output_dir)
    result["output_files"] = {
        "json": str(json_path),
        "csv": str(csv_path),
        "summary": str(summary_path),
        "report": str(report_path),
    }
    return result
