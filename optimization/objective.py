from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ObjectiveWeights:
    service: float = 0.40
    pressure: float = 0.20
    leakage: float = 0.20
    affected_nodes: float = 0.15
    actions: float = 0.05

    def __post_init__(self) -> None:
        if min(asdict(self).values()) < 0:
            raise ValueError("Trọng số hàm mục tiêu không được âm")
        if sum(asdict(self).values()) <= 0:
            raise ValueError("Tổng trọng số hàm mục tiêu phải lớn hơn 0")

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


def _bounded_compliance(violations: int, node_count: int) -> float:
    if node_count <= 0:
        return 1.0
    return max(0.0, 1.0 - min(violations / node_count, 1.0))


def score_recovery(
    failure_summary: dict[str, Any],
    recovery_summary: dict[str, Any],
    node_count: int,
    action_count: int,
    weights: ObjectiveWeights | None = None,
) -> dict[str, Any]:
    objective_weights = weights or ObjectiveWeights()
    failure_leakage = float(failure_summary["total_leakage_volume"])
    recovery_leakage = float(recovery_summary["total_leakage_volume"])
    if failure_leakage <= 0:
        leakage_control = 1.0 if recovery_leakage <= 0 else 0.0
    else:
        leakage_control = max(
            0.0,
            1.0 - min(recovery_leakage / failure_leakage, 1.0),
        )

    components = {
        "service": max(
            0.0,
            min(float(recovery_summary["minimum_service_availability"]), 1.0),
        ),
        "pressure": _bounded_compliance(
            int(recovery_summary["maximum_pressure_violations"]),
            node_count,
        ),
        "leakage": leakage_control,
        "affected_nodes": _bounded_compliance(
            int(recovery_summary["maximum_affected_nodes"]),
            node_count,
        ),
        "actions": 1.0 / (1.0 + action_count),
    }
    weight_values = objective_weights.to_dict()
    total_weight = sum(weight_values.values())
    score = sum(
        components[name] * weight_values[name]
        for name in components
    ) / total_weight
    return {
        "score": round(score * 100, 6),
        "components": components,
        "weights": weight_values,
    }

