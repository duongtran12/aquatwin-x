from pathlib import Path
from time import perf_counter
from typing import Any

from optimization.baseline import build_isolation_baseline
from optimization.candidates import generate_closure_candidates
from optimization.objective import ObjectiveWeights, score_recovery
from simulation.engine import (
    LeakScenario,
    RecoveryEvaluator,
    ValveRegistry,
)
from simulation.engine.valves import RecoveryAction


def _evaluate_candidate(
    evaluator: RecoveryEvaluator,
    actions: list[RecoveryAction],
    node_count: int,
    weights: ObjectiveWeights,
) -> dict[str, Any]:
    started_at = perf_counter()
    try:
        result = evaluator.evaluate(actions, include_time_steps=False)
        objective = score_recovery(
            result["failure"]["summary"],
            result["recovery"]["summary"],
            node_count,
            len(actions),
            weights,
        )
        return {
            "feasible": True,
            "actions": [action.to_dict() for action in actions],
            "score": objective["score"],
            "objective": objective,
            "topology": result["topology"],
            "summary": result["recovery"]["summary"],
            "computation_time_seconds": perf_counter() - started_at,
        }
    except Exception as exc:
        return {
            "feasible": False,
            "actions": [action.to_dict() for action in actions],
            "score": None,
            "error": str(exc),
            "computation_time_seconds": perf_counter() - started_at,
        }


def run_exhaustive_search(
    network_path: str | Path,
    scenario: LeakScenario,
    registry: ValveRegistry,
    max_actions: int = 2,
    top_k: int = 5,
    weights: ObjectiveWeights | None = None,
) -> dict[str, Any]:
    if top_k <= 0:
        raise ValueError("top_k phải lớn hơn 0")

    objective_weights = weights or ObjectiveWeights()
    evaluator = RecoveryEvaluator(network_path, scenario, registry)
    candidates = generate_closure_candidates(registry, max_actions)
    evaluations = [
        _evaluate_candidate(
            evaluator,
            actions,
            evaluator.source.junctions,
            objective_weights,
        )
        for actions in candidates
    ]
    feasible = [evaluation for evaluation in evaluations if evaluation["feasible"]]
    feasible.sort(
        key=lambda evaluation: (
            -float(evaluation["score"]),
            len(evaluation["actions"]),
        )
    )

    baseline_actions = build_isolation_baseline(registry, scenario.pipe_id)
    baseline_ids = [action.to_dict() for action in baseline_actions]
    baseline = next(
        (
            evaluation
            for evaluation in evaluations
            if evaluation["actions"] == baseline_ids
        ),
        None,
    )
    return {
        "algorithm": "exhaustive_search",
        "network": evaluator.source.to_dict(),
        "scenario": scenario.to_dict(),
        "weights": objective_weights.to_dict(),
        "max_actions": max_actions,
        "candidate_count": len(candidates),
        "feasible_count": len(feasible),
        "failed_count": len(evaluations) - len(feasible),
        "failure_summary": evaluator.failure_summary,
        "isolation_baseline": baseline,
        "best_candidate": feasible[0] if feasible else None,
        "ranking": feasible[:top_k],
        "failed_candidates": [
            evaluation for evaluation in evaluations if not evaluation["feasible"]
        ],
    }

