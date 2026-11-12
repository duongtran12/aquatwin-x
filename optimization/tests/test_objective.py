import unittest

from optimization.objective import score_recovery


FAILURE = {
    "minimum_service_availability": 0.6,
    "maximum_pressure_violations": 3,
    "maximum_affected_nodes": 4,
    "total_leakage_volume": 100.0,
}


class ObjectiveTests(unittest.TestCase):
    def test_better_recovery_receives_higher_score(self) -> None:
        weak = {
            "minimum_service_availability": 0.7,
            "maximum_pressure_violations": 2,
            "maximum_affected_nodes": 3,
            "total_leakage_volume": 70.0,
        }
        strong = {
            "minimum_service_availability": 0.95,
            "maximum_pressure_violations": 0,
            "maximum_affected_nodes": 1,
            "total_leakage_volume": 5.0,
        }

        weak_score = score_recovery(FAILURE, weak, 4, 1)["score"]
        strong_score = score_recovery(FAILURE, strong, 4, 2)["score"]

        self.assertGreater(strong_score, weak_score)

    def test_score_contains_normalized_components(self) -> None:
        recovery = {
            "minimum_service_availability": 1.0,
            "maximum_pressure_violations": 0,
            "maximum_affected_nodes": 0,
            "total_leakage_volume": 0.0,
        }

        result = score_recovery(FAILURE, recovery, 4, 2)

        self.assertLessEqual(result["score"], 100)
        self.assertEqual(result["components"]["leakage"], 1.0)


if __name__ == "__main__":
    unittest.main()

