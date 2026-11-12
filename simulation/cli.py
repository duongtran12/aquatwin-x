import argparse
import json
from pathlib import Path

from simulation.engine import inspect_inp, run_baseline


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NETWORK = PROJECT_ROOT / "simulation" / "networks" / "aquatwin_demo.inp"
DEFAULT_OUTPUT = PROJECT_ROOT / "simulation" / "outputs" / "baseline.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AquaTwin-X simulation command line")
    parser.add_argument(
        "command",
        choices=["inspect", "baseline"],
        help="inspect đọc metadata, baseline chạy mô phỏng bình thường",
    )
    parser.add_argument("--network", type=Path, default=DEFAULT_NETWORK)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "inspect":
        result = inspect_inp(args.network).to_dict()
    else:
        result = run_baseline(args.network)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("Simulation output created successfully.")


if __name__ == "__main__":
    main()

