import unittest

from optimization.genetic import GeneticConfig, GeneticOptimizer


class GeneticOptimizerTests(unittest.TestCase):
    def test_finds_target_chromosome(self) -> None:
        target = (1, 0, 1, 0)

        def evaluate(chromosome: tuple[int, ...]) -> dict[str, object]:
            matches = sum(
                gene == expected
                for gene, expected in zip(chromosome, target)
            )
            return {"feasible": True, "score": float(matches)}

        optimizer = GeneticOptimizer(
            gene_count=4,
            evaluator=evaluate,
            config=GeneticConfig(
                population_size=10,
                generations=10,
                mutation_rate=0.2,
                max_actions=2,
                seed=7,
            ),
        )

        result = optimizer.optimize()

        self.assertEqual(result["best_chromosome"], target)
        self.assertEqual(result["best_evaluation"]["score"], 4.0)
        self.assertEqual(len(result["history"]), 10)

    def test_respects_maximum_action_count(self) -> None:
        evaluated = []

        def evaluate(chromosome: tuple[int, ...]) -> dict[str, object]:
            evaluated.append(chromosome)
            return {"feasible": True, "score": float(sum(chromosome))}

        optimizer = GeneticOptimizer(
            gene_count=8,
            evaluator=evaluate,
            config=GeneticConfig(
                population_size=12,
                generations=5,
                mutation_rate=0.5,
                max_actions=2,
                seed=11,
            ),
        )

        optimizer.optimize()

        self.assertTrue(all(sum(chromosome) <= 2 for chromosome in evaluated))

    def test_reports_progress_after_each_generation(self) -> None:
        updates = []
        optimizer = GeneticOptimizer(
            gene_count=4,
            evaluator=lambda chromosome: {
                "feasible": True,
                "score": float(sum(chromosome)),
            },
            config=GeneticConfig(
                population_size=6,
                generations=4,
                max_actions=2,
                seed=3,
            ),
        )

        optimizer.optimize(lambda completed, total, message: updates.append(
            (completed, total, message)
        ))

        self.assertEqual(len(updates), 4)
        self.assertEqual(updates[0], (1, 4, "Generation 1 of 4"))
        self.assertEqual(updates[-1], (4, 4, "Generation 4 of 4"))


if __name__ == "__main__":
    unittest.main()

