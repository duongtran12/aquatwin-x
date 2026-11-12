import argparse
import json
from pathlib import Path

from simulation.engine import (
    analyze_connectivity,
    inspect_inp,
    load_leak_scenario,
    load_recovery_actions,
    load_valve_registry,
    run_baseline,
    run_failure,
    run_manual_recovery,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NETWORK = PROJECT_ROOT / "simulation" / "networks" / "aquatwin_demo.inp"
DEFAULT_SCENARIO = PROJECT_ROOT / "simulation" / "scenarios" / "demo_pipe_leak.json"
DEFAULT_VALVES = PROJECT_ROOT / "simulation" / "valves" / "aquatwin_demo_valves.json"
DEFAULT_ACTIONS = (
    PROJECT_ROOT / "simulation" / "scenarios" / "demo_manual_recovery.json"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AquaTwin-X simulation command line")
    parser.add_argument(
        "command",
        choices=["inspect", "baseline", "failure", "topology", "recovery"],
        help="inspect, baseline, failure, topology check, or manual recovery",
    )
    parser.add_argument("--network", type=Path, default=DEFAULT_NETWORK)
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--valves", type=Path, default=DEFAULT_VALVES)
    parser.add_argument("--actions", type=Path, default=DEFAULT_ACTIONS)
    parser.add_argument("--output", type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output = args.output or PROJECT_ROOT / "simulation" / "outputs" / f"{args.command}.json"

    if args.command == "inspect":
        result = inspect_inp(args.network).to_dict()
    elif args.command == "baseline":
        result = run_baseline(args.network)
    elif args.command == "failure":
        scenario = load_leak_scenario(args.scenario)
        result = run_failure(args.network, scenario)
    elif args.command == "topology":
        registry = load_valve_registry(args.valves)
        actions = load_recovery_actions(args.actions)
        result = analyze_connectivity(args.network, registry, actions)
    else:
        scenario = load_leak_scenario(args.scenario)
        registry = load_valve_registry(args.valves)
        actions = load_recovery_actions(args.actions)
        result = run_manual_recovery(
            args.network,
            scenario,
            registry,
            actions,
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("Simulation output created successfully.")


if __name__ == "__main__":
    main()

