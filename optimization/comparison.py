import json
from pathlib import Path
from typing import Any


def load_result(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).resolve().read_text(encoding="utf-8-sig"))


def compare_search_results(
    exhaustive: dict[str, Any],
    genetic: dict[str, Any],
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    exhaustive_best = exhaustive.get("best_candidate")
    genetic_best = genetic.get("best_candidate")
    if exhaustive_best is None or genetic_best is None:
        raise ValueError("Cả hai kết quả phải có best_candidate")

    exhaustive_score = float(exhaustive_best["score"])
    genetic_score = float(genetic_best["score"])
    return {
        "exhaustive": {
            "best_score": exhaustive_score,
            "actions": exhaustive_best["actions"],
            "evaluated_count": exhaustive.get("candidate_count"),
            "computation_time_seconds": exhaustive.get("computation_time_seconds"),
        },
        "genetic_algorithm": {
            "best_score": genetic_score,
            "actions": genetic_best["actions"],
            "evaluated_count": genetic.get("unique_evaluated_count"),
            "computation_time_seconds": genetic.get("computation_time_seconds"),
        },
        "score_gap": exhaustive_score - genetic_score,
        "ga_found_global_optimum": abs(exhaustive_score - genetic_score) <= tolerance,
    }

