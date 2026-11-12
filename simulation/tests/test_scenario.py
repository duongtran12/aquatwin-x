import json
import tempfile
import unittest
from pathlib import Path

from simulation.engine.scenario import LeakScenario, load_leak_scenario


class LeakScenarioTests(unittest.TestCase):
    def test_loads_valid_scenario(self) -> None:
        scenario = LeakScenario(
            pipe_id="P3",
            leak_area=0.0005,
            start_time=7200,
            end_time=43200,
        )

        self.assertEqual(scenario.pipe_id, "P3")
        self.assertEqual(scenario.split_position, 0.5)
        self.assertEqual(scenario.discharge_coefficient, 0.75)

    def test_rejects_invalid_time_range(self) -> None:
        with self.assertRaises(ValueError):
            LeakScenario(
                pipe_id="P3",
                leak_area=0.0005,
                start_time=7200,
                end_time=3600,
            )

    def test_reads_json_file(self) -> None:
        payload = {
            "pipe_id": "P2",
            "leak_area": 0.0003,
            "start_time": 3600,
            "end_time": 10800,
        }
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            path = Path(directory) / "scenario.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            scenario = load_leak_scenario(path)

        self.assertEqual(scenario.pipe_id, "P2")
        self.assertEqual(scenario.end_time, 10800)


if __name__ == "__main__":
    unittest.main()
