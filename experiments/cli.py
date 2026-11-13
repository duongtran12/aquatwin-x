import argparse
from pathlib import Path

from experiments.benchmark import BenchmarkConfig, run_benchmark


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "experiments" / "configs" / "week8_demo.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "benchmark" / "week8_demo"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the AquaTwin-X recovery benchmark")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = BenchmarkConfig.from_json(args.config)
    result = run_benchmark(config, args.output_dir)
    ga_summary = result["summary"]["genetic_algorithm"]
    print(f"Completed {result['configuration']['scenario_count']} scenarios.")
    print(f"GA global optimum hit rate: {ga_summary['global_optimum_hit_rate']:.1%}")
    print(f"JSON: {result['output_files']['json']}")
    print(f"CSV: {result['output_files']['csv']}")


if __name__ == "__main__":
    main()
