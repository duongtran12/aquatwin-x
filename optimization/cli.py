import argparse
import json
from pathlib import Path

from optimization.runner import run_exhaustive_search
from simulation.engine import load_leak_scenario, load_valve_registry


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NETWORK = PROJECT_ROOT / "simulation" / "networks" / "aquatwin_demo.inp"
DEFAULT_SCENARIO = PROJECT_ROOT / "simulation" / "scenarios" / "demo_pipe_leak.json"
DEFAULT_VALVES = PROJECT_ROOT / "simulation" / "valves" / "aquatwin_demo_valves.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "optimization" / "outputs" / "exhaustive.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AquaTwin-X recovery optimization")
    parser.add_argument("command", choices=["exhaustive"])
    parser.add_argument("--network", type=Path, default=DEFAULT_NETWORK)
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--valves", type=Path, default=DEFAULT_VALVES)
    parser.add_argument("--max-actions", type=int, default=2)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    scenario = load_leak_scenario(args.scenario)
    registry = load_valve_registry(args.valves)
    result = run_exhaustive_search(
        args.network,
        scenario,
        registry,
        max_actions=args.max_actions,
        top_k=args.top_k,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("Optimization output created successfully.")


if __name__ == "__main__":
    main()

