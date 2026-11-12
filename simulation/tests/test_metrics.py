import unittest

from simulation.engine.metrics import safe_ratio, summarize_failure_steps


class FailureMetricsTests(unittest.TestCase):
    def test_safe_ratio_is_bounded(self) -> None:
        self.assertEqual(safe_ratio(80, 100), 0.8)
        self.assertEqual(safe_ratio(120, 100), 1.0)
        self.assertEqual(safe_ratio(-5, 100), 0.0)

    def test_summarizes_failure_steps(self) -> None:
        steps = [
            {
                "time_seconds": 0,
                "metrics": {
                    "service_availability": 1.0,
                    "pressure_violations": 0,
                    "affected_nodes": 0,
                    "leak_flowrate": 0.0,
                },
            },
            {
                "time_seconds": 3600,
                "metrics": {
                    "service_availability": 0.75,
                    "pressure_violations": 2,
                    "affected_nodes": 3,
                    "leak_flowrate": 0.01,
                },
            },
        ]

        summary = summarize_failure_steps(steps)

        self.assertEqual(summary["minimum_service_availability"], 0.75)
        self.assertEqual(summary["maximum_pressure_violations"], 2)
        self.assertEqual(summary["maximum_affected_nodes"], 3)
        self.assertEqual(summary["total_leakage_volume"], 18.0)


if __name__ == "__main__":
    unittest.main()
