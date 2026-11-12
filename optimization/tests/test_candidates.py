import unittest
from pathlib import Path

from optimization.candidates import generate_closure_candidates
from simulation.engine.valves import load_valve_registry


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VALVE_PATH = PROJECT_ROOT / "simulation" / "valves" / "aquatwin_demo_valves.json"


class CandidateTests(unittest.TestCase):
    def test_generates_all_candidates_up_to_two_actions(self) -> None:
        registry = load_valve_registry(VALVE_PATH)

        candidates = generate_closure_candidates(registry, max_actions=2)

        self.assertEqual(len(candidates), 79)
        self.assertEqual(candidates[0], [])
        self.assertTrue(all(len(candidate) <= 2 for candidate in candidates))


if __name__ == "__main__":
    unittest.main()

