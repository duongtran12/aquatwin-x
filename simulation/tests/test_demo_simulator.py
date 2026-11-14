from pathlib import Path

from simulation.engine import LeakScenario, RecoveryAction, load_valve_registry
from simulation.engine.demo import (
    run_demo_failure,
    run_demo_manual_recovery,
    run_demo_optimization,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
NETWORK = PROJECT_ROOT / "simulation" / "networks" / "aquatwin_demo.inp"
VALVES = PROJECT_ROOT / "simulation" / "valves" / "aquatwin_demo_valves.json"


def scenario() -> LeakScenario:
    return LeakScenario("P3", 0.0005, 7200, 43200)


def test_demo_failure_returns_complete_time_series() -> None:
    result = run_demo_failure(NETWORK, scenario())
    assert result["scenario"] == "pipe_leak"
    assert len(result["time_steps"]) == 25
    assert result["summary"]["maximum_affected_nodes"] > 0
    assert result["summary"]["total_leakage_volume"] > 0


def test_targeted_isolation_reduces_demo_leakage() -> None:
    registry = load_valve_registry(VALVES)
    actions = [
        RecoveryAction("V_P3_START", "CLOSED"),
        RecoveryAction("V_P3_END", "CLOSED"),
    ]
    result = run_demo_manual_recovery(NETWORK, scenario(), registry, actions)
    assert result["recovery"]["summary"]["total_leakage_volume"] < result["failure"]["summary"]["total_leakage_volume"]
    assert len(result["actions"]) == 2


def test_demo_ga_has_dashboard_compatible_history() -> None:
    registry = load_valve_registry(VALVES)
    result = run_demo_optimization(NETWORK, scenario(), registry, generations=8)
    assert result["best_candidate"]["score"] > 0
    assert len(result["history"]) == 8
    assert result["history"][-1]["best_score"] == result["best_candidate"]["score"]
