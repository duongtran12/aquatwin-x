import unittest

from optimization.comparison import compare_search_results


class ComparisonTests(unittest.TestCase):
    def test_detects_global_optimum(self) -> None:
        exhaustive = {
            "best_candidate": {"score": 91.5, "actions": []},
            "candidate_count": 79,
            "computation_time_seconds": 12.0,
        }
        genetic = {
            "best_candidate": {"score": 91.5, "actions": []},
            "unique_evaluated_count": 35,
            "computation_time_seconds": 5.0,
        }

        result = compare_search_results(exhaustive, genetic)

        self.assertTrue(result["ga_found_global_optimum"])
        self.assertEqual(result["score_gap"], 0.0)
        self.assertEqual(result["genetic_algorithm"]["evaluated_count"], 35)


if __name__ == "__main__":
    unittest.main()

