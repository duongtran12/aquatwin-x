import unittest
from pathlib import Path

from optimization.baseline import build_isolation_baseline
from simulation.engine.valves import load_valve_registry


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VALVE_PATH = PROJECT_ROOT / "simulation" / "valves" / "aquatwin_demo_valves.json"


class BaselineTests(unittest.TestCase):
    def test_builds_two_valve_isolation_baseline(self) -> None:
        registry = load_valve_registry(VALVE_PATH)

        actions = build_isolation_baseline(registry, "P3")

        self.assertEqual(len(actions), 2)
        self.assertEqual(
            {action.valve_id for action in actions},
            {"V_P3_START", "V_P3_END"},
        )


if __name__ == "__main__":
    unittest.main()

