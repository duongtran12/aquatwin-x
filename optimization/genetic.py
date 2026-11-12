from dataclasses import asdict, dataclass
from math import comb
from random import Random
from statistics import mean
from typing import Any, Callable


Chromosome = tuple[int, ...]
ChromosomeEvaluator = Callable[[Chromosome], dict[str, Any]]


@dataclass(frozen=True)
class GeneticConfig:
    population_size: int = 20
    generations: int = 20
    crossover_rate: float = 0.8
    mutation_rate: float = 0.1
    tournament_size: int = 3
    elite_count: int = 2
    max_actions: int = 2
    seed: int = 42

    def __post_init__(self) -> None:
        if self.population_size < 2:
            raise ValueError("population_size phải từ 2 trở lên")
        if self.generations < 1:
            raise ValueError("generations phải từ 1 trở lên")
        if not 0 <= self.crossover_rate <= 1:
            raise ValueError("crossover_rate phải thuộc đoạn [0, 1]")
        if not 0 <= self.mutation_rate <= 1:
            raise ValueError("mutation_rate phải thuộc đoạn [0, 1]")
        if not 2 <= self.tournament_size <= self.population_size:
            raise ValueError("tournament_size không hợp lệ")
        if not 1 <= self.elite_count < self.population_size:
            raise ValueError("elite_count không hợp lệ")
        if self.max_actions < 0:
            raise ValueError("max_actions không được âm")

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


class GeneticOptimizer:
    def __init__(
        self,
        gene_count: int,
        evaluator: ChromosomeEvaluator,
        config: GeneticConfig | None = None,
        seed_chromosomes: list[Chromosome] | None = None,
    ) -> None:
        if gene_count <= 0:
            raise ValueError("gene_count phải lớn hơn 0")
        self.gene_count = gene_count
        self.evaluator = evaluator
        self.config = config or GeneticConfig()
        self.random = Random(self.config.seed)
        self.cache: dict[Chromosome, dict[str, Any]] = {}
        self.seed_chromosomes = [
            self._repair(chromosome)
            for chromosome in (seed_chromosomes or [])
            if len(chromosome) == gene_count
        ]

    def _repair(self, chromosome: Chromosome) -> Chromosome:
        genes = [1 if gene else 0 for gene in chromosome]
        selected = [index for index, gene in enumerate(genes) if gene]
        while len(selected) > self.config.max_actions:
            index = self.random.choice(selected)
            genes[index] = 0
            selected.remove(index)
        return tuple(genes)

    def _random_chromosome(self) -> Chromosome:
        action_count = self.random.randint(
            0,
            min(self.config.max_actions, self.gene_count),
        )
        selected = set(self.random.sample(range(self.gene_count), action_count))
        return tuple(1 if index in selected else 0 for index in range(self.gene_count))

    def _initial_population(self) -> list[Chromosome]:
        population = [tuple(0 for _ in range(self.gene_count))]
        population.extend(self.seed_chromosomes)
        unique_limit = sum(
            comb(self.gene_count, action_count)
            for action_count in range(
                min(self.config.max_actions, self.gene_count) + 1
            )
        )
        target_unique = min(self.config.population_size, unique_limit)
        unique = set(population)
        while len(unique) < target_unique:
            unique.add(self._random_chromosome())
        population = list(unique)
        while len(population) < self.config.population_size:
            population.append(self.random.choice(population))
        self.random.shuffle(population)
        return population[: self.config.population_size]

    def _evaluation(self, chromosome: Chromosome) -> dict[str, Any]:
        if chromosome not in self.cache:
            self.cache[chromosome] = self.evaluator(chromosome)
        return self.cache[chromosome]

    def _fitness(self, chromosome: Chromosome) -> float:
        evaluation = self._evaluation(chromosome)
        if not evaluation.get("feasible") or evaluation.get("score") is None:
            return float("-inf")
        return float(evaluation["score"])

    def _rank_key(self, chromosome: Chromosome) -> tuple[float, int]:
        return self._fitness(chromosome), -sum(chromosome)

    def _tournament(self, population: list[Chromosome]) -> Chromosome:
        contenders = self.random.sample(population, self.config.tournament_size)
        return max(contenders, key=self._rank_key)

    def _crossover(
        self,
        first: Chromosome,
        second: Chromosome,
    ) -> tuple[Chromosome, Chromosome]:
        if self.gene_count < 2 or self.random.random() > self.config.crossover_rate:
            return first, second
        point = self.random.randint(1, self.gene_count - 1)
        return (
            self._repair(first[:point] + second[point:]),
            self._repair(second[:point] + first[point:]),
        )

    def _mutate(self, chromosome: Chromosome) -> Chromosome:
        genes = list(chromosome)
        for index in range(self.gene_count):
            if self.random.random() < self.config.mutation_rate:
                genes[index] = 1 - genes[index]
        return self._repair(tuple(genes))

    def optimize(self) -> dict[str, Any]:
        population = self._initial_population()
        history = []
        best_chromosome: Chromosome | None = None

        for generation in range(self.config.generations):
            ranked = sorted(population, key=self._rank_key, reverse=True)
            feasible_scores = [
                self._fitness(chromosome)
                for chromosome in ranked
                if self._fitness(chromosome) != float("-inf")
            ]
            generation_best = ranked[0] if feasible_scores else None
            if generation_best is not None and (
                best_chromosome is None
                or self._rank_key(generation_best) > self._rank_key(best_chromosome)
            ):
                best_chromosome = generation_best

            history.append(
                {
                    "generation": generation,
                    "best_score": (
                        self._fitness(generation_best)
                        if generation_best is not None
                        else None
                    ),
                    "average_score": mean(feasible_scores) if feasible_scores else None,
                    "feasible_count": len(feasible_scores),
                    "unique_evaluated_count": len(self.cache),
                }
            )

            if generation == self.config.generations - 1:
                break

            next_population = ranked[: self.config.elite_count]
            while len(next_population) < self.config.population_size:
                first = self._tournament(population)
                second = self._tournament(population)
                first_child, second_child = self._crossover(first, second)
                next_population.append(self._mutate(first_child))
                if len(next_population) < self.config.population_size:
                    next_population.append(self._mutate(second_child))
            population = next_population

        return {
            "best_chromosome": best_chromosome,
            "best_evaluation": (
                self._evaluation(best_chromosome)
                if best_chromosome is not None
                else None
            ),
            "history": history,
            "evaluations": dict(self.cache),
        }

