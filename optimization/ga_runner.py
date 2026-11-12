from pathlib import Path
from time import perf_counter
from typing import Any

from optimization.baseline import build_isolation_baseline
from optimization.genetic import Chromosome, GeneticConfig, GeneticOptimizer
from optimization.objective import ObjectiveWeights
from optimization.runner import evaluate_candidate
from simulation.engine import LeakScenario, RecoveryEvaluator, ValveRegistry
from simulation.engine.valves import RecoveryAction


def run_genetic_search(
    network_path: str | Path,
    scenario: LeakScenario,
    registry: ValveRegistry,
    config: GeneticConfig | None = None,
    top_k: int = 5,
    weights: ObjectiveWeights | None = None,
) -> dict[str, Any]:
    if top_k <= 0:
        raise ValueError("top_k phải lớn hơn 0")

    started_at = perf_counter()
    ga_config = config or GeneticConfig()
    objective_weights = weights or ObjectiveWeights()
    recovery_evaluator = RecoveryEvaluator(network_path, scenario, registry)
    valves = sorted(registry.valves, key=lambda valve: valve.valve_id)

    def chromosome_to_actions(chromosome: Chromosome) -> list[RecoveryAction]:
        return [
            RecoveryAction(valve.valve_id, "CLOSED")
            for gene, valve in zip(chromosome, valves)
            if gene
        ]

    def evaluate(chromosome: Chromosome) -> dict[str, Any]:
        return evaluate_candidate(
            recovery_evaluator,
            chromosome_to_actions(chromosome),
            recovery_evaluator.source.junctions,
            objective_weights,
        )

    baseline_actions = build_isolation_baseline(registry, scenario.pipe_id)
    baseline_ids = {action.valve_id for action in baseline_actions}
    baseline_chromosome = tuple(
        1 if valve.valve_id in baseline_ids else 0
        for valve in valves
    )
    optimizer = GeneticOptimizer(
        gene_count=len(valves),
        evaluator=evaluate,
        config=ga_config,
        seed_chromosomes=[baseline_chromosome],
    )
    result = optimizer.optimize()
    evaluations = list(result["evaluations"].values())
    feasible = [evaluation for evaluation in evaluations if evaluation["feasible"]]
    feasible.sort(
        key=lambda evaluation: (
            -float(evaluation["score"]),
            len(evaluation["actions"]),
        )
    )

    return {
        "algorithm": "genetic_algorithm",
        "network": recovery_evaluator.source.to_dict(),
        "scenario": scenario.to_dict(),
        "weights": objective_weights.to_dict(),
        "config": ga_config.to_dict(),
        "unique_evaluated_count": len(evaluations),
        "feasible_count": len(feasible),
        "failed_count": len(evaluations) - len(feasible),
        "computation_time_seconds": perf_counter() - started_at,
        "failure_summary": recovery_evaluator.failure_summary,
        "isolation_baseline": result["evaluations"].get(baseline_chromosome),
        "best_candidate": result["best_evaluation"],
        "ranking": feasible[:top_k],
        "history": result["history"],
        "failed_candidates": [
            evaluation for evaluation in evaluations if not evaluation["feasible"]
        ],
    }

