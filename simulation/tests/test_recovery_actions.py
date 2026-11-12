import unittest
from pathlib import Path

from simulation.engine.topology import analyze_connectivity
from simulation.engine.valves import (
    RecoveryAction,
    load_recovery_actions,
    load_valve_registry,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
NETWORK_PATH = PROJECT_ROOT / "simulation" / "networks" / "aquatwin_demo.inp"
VALVE_PATH = PROJECT_ROOT / "simulation" / "valves" / "aquatwin_demo_valves.json"
ACTION_PATH = PROJECT_ROOT / "simulation" / "scenarios" / "demo_manual_recovery.json"


class RecoveryActionTests(unittest.TestCase):
    def test_loads_manual_recovery_actions(self) -> None:
        registry = load_valve_registry(VALVE_PATH)
        actions = load_recovery_actions(ACTION_PATH)

        self.assertEqual(len(registry.valves), 12)
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[0].status, "CLOSED")
        self.assertEqual(
            registry.resolve_link_id("V_P3_END", "P3", "P3_LEAK_SEGMENT"),
            "P3_LEAK_SEGMENT",
        )

    def test_p3_isolation_preserves_source_connectivity(self) -> None:
        registry = load_valve_registry(VALVE_PATH)
        actions = load_recovery_actions(ACTION_PATH)

        result = analyze_connectivity(NETWORK_PATH, registry, actions)

        self.assertTrue(result["is_fully_connected"])
        self.assertEqual(result["closed_links"], ["P3"])

    def test_closing_source_pipe_isolates_demand_nodes(self) -> None:
        registry = load_valve_registry(VALVE_PATH)
        actions = [RecoveryAction("V_P1_START", "CLOSED")]

        result = analyze_connectivity(NETWORK_PATH, registry, actions)

        self.assertFalse(result["is_fully_connected"])
        self.assertEqual(result["isolated_nodes"], ["J1", "J2", "J3", "J4"])


if __name__ == "__main__":
    unittest.main()
