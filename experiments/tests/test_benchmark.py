import json
import tempfile
from pathlib import Path

from experiments.benchmark import BenchmarkConfig, build_scenarios, run_benchmark


PROJECT_ROOT = Path(__file__).resolve().parents[2]
NETWORK = PROJECT_ROOT / "simulation" / "networks" / "aquatwin_demo.inp"
VALVES = PROJECT_ROOT / "simulation" / "valves" / "aquatwin_demo_valves.json"


def candidate(score: float, valve_id: str = "V_P1_START") -> dict:
    return {
        "score": score,
        "actions": [{"valve_id": valve_id, "status": "CLOSED"}],
        "summary": {
            "minimum_service_availability": 0.9,
            "maximum_pressure_violations": 1,
            "maximum_affected_nodes": 1,
            "total_leakage_volume": 4.5,
        },
        "computation_time_seconds": 0.2,
    }


def test_builds_all_pipe_and_leak_combinations() -> None:
    config = BenchmarkConfig(
        network_path=NETWORK,
        valve_path=VALVES,
        pipe_ids=("P1", "P2"),
        leak_areas=(0.0003, 0.0007),
        seeds=(42,),
    )
    scenarios = build_scenarios(config)
    assert [item[0] for item in scenarios] == ["P1_L1", "P1_L2", "P2_L1", "P2_L2"]
    assert scenarios[-1][1].leak_area == 0.0007


def test_loads_paths_relative_to_config_file() -> None:
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
        folder = Path(directory)
        payload = {
            "network_path": str(NETWORK),
            "valve_path": str(VALVES),
            "pipe_ids": ["P1"],
            "leak_areas": [0.0003],
            "seeds": [7, 42],
        }
        path = folder / "config.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        config = BenchmarkConfig.from_json(path)
    assert config.network_path == NETWORK.resolve()
    assert config.seeds == (7, 42)


def test_runs_benchmark_and_writes_report_files() -> None:
    config = BenchmarkConfig(
        network_path=NETWORK,
        valve_path=VALVES,
        pipe_ids=("P1",),
        leak_areas=(0.0003,),
        seeds=(7, 42),
    )

    def fake_exhaustive(*args, **kwargs):
        return {
            "best_candidate": candidate(90),
            "isolation_baseline": candidate(80, "V_P1_END"),
            "candidate_count": 79,
            "computation_time_seconds": 4.0,
            "failure_summary": {
                "minimum_service_availability": 0.5,
                "maximum_pressure_violations": 3,
                "maximum_affected_nodes": 4,
                "total_leakage_volume": 20.0,
            },
        }

    def fake_ga(*args, **kwargs):
        seed = kwargs["config"].seed
        return {
            "best_candidate": candidate(90 if seed == 7 else 88),
            "unique_evaluated_count": 30,
            "computation_time_seconds": 2.0,
        }

    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
        result = run_benchmark(config, directory, fake_exhaustive, fake_ga)
        json_path = Path(result["output_files"]["json"])
        csv_path = Path(result["output_files"]["csv"])
        assert json_path.is_file()
        assert csv_path.is_file()
        assert len(result["runs"]) == 4
        assert result["summary"]["genetic_algorithm"]["global_optimum_hit_rate"] == 0.5
        assert result["runs"][0]["failure_maximum_affected_nodes"] == 4
