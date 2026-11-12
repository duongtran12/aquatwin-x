import argparse
import json
from pathlib import Path
from typing import Any

from optimization.comparison import compare_search_results, load_result
from optimization.ga_runner import run_genetic_search
from optimization.genetic import GeneticConfig
from optimization.runner import run_exhaustive_search
from simulation.engine import load_leak_scenario, load_valve_registry


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NETWORK = PROJECT_ROOT / "simulation" / "networks" / "aquatwin_demo.inp"
DEFAULT_SCENARIO = PROJECT_ROOT / "simulation" / "scenarios" / "demo_pipe_leak.json"
DEFAULT_VALVES = PROJECT_ROOT / "simulation" / "valves" / "aquatwin_demo_valves.json"
OUTPUT_DIR = PROJECT_ROOT / "optimization" / "outputs"


def _add_common_search_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--network", type=Path, default=DEFAULT_NETWORK)
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--valves", type=Path, default=DEFAULT_VALVES)
    parser.add_argument("--max-actions", type=int, default=2)
    parser.add_argument("--top-k", type=int, default=5)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AquaTwin-X recovery optimization")
    commands = parser.add_subparsers(dest="command", required=True)

    exhaustive = commands.add_parser("exhaustive")
    _add_common_search_arguments(exhaustive)
    exhaustive.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR / "exhaustive.json",
    )

    genetic = commands.add_parser("ga")
    _add_common_search_arguments(genetic)
    genetic.add_argument("--population-size", type=int, default=20)
    genetic.add_argument("--generations", type=int, default=20)
    genetic.add_argument("--crossover-rate", type=float, default=0.8)
    genetic.add_argument("--mutation-rate", type=float, default=0.1)
    genetic.add_argument("--tournament-size", type=int, default=3)
    genetic.add_argument("--elite-count", type=int, default=2)
    genetic.add_argument("--seed", type=int, default=42)
    genetic.add_argument("--output", type=Path, default=OUTPUT_DIR / "ga.json")

    comparison = commands.add_parser("compare")
    comparison.add_argument(
        "--exhaustive-result",
        type=Path,
        default=OUTPUT_DIR / "exhaustive.json",
    )
    comparison.add_argument(
        "--ga-result",
        type=Path,
        default=OUTPUT_DIR / "ga.json",
    )
    comparison.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR / "comparison.json",
    )
    return parser


def _run_search(args: argparse.Namespace) -> dict[str, Any]:
    scenario = load_leak_scenario(args.scenario)
    registry = load_valve_registry(args.valves)
    if args.command == "exhaustive":
        return run_exhaustive_search(
            args.network,
            scenario,
            registry,
            max_actions=args.max_actions,
            top_k=args.top_k,
        )

    config = GeneticConfig(
        population_size=args.population_size,
        generations=args.generations,
        crossover_rate=args.crossover_rate,
        mutation_rate=args.mutation_rate,
        tournament_size=args.tournament_size,
        elite_count=args.elite_count,
        max_actions=args.max_actions,
        seed=args.seed,
    )
    return run_genetic_search(
        args.network,
        scenario,
        registry,
        config=config,
        top_k=args.top_k,
    )


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "compare":
        result = compare_search_results(
            load_result(args.exhaustive_result),
            load_result(args.ga_result),
        )
    else:
        result = _run_search(args)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("Optimization output created successfully.")


if __name__ == "__main__":
    main()
