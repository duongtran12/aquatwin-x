from typing import Any


def safe_ratio(value: float, reference: float) -> float:
    if reference <= 0:
        return 1.0 if value >= reference else 0.0
    return max(0.0, min(value / reference, 1.0))


def summarize_failure_steps(time_steps: list[dict[str, Any]]) -> dict[str, float | int]:
    if not time_steps:
        return {
            "minimum_service_availability": 0.0,
            "maximum_pressure_violations": 0,
            "maximum_affected_nodes": 0,
            "peak_leak_flowrate": 0.0,
            "total_leakage_volume": 0.0,
        }

    total_leakage_volume = 0.0
    for index in range(1, len(time_steps)):
        previous = time_steps[index - 1]
        current = time_steps[index]
        elapsed = current["time_seconds"] - previous["time_seconds"]
        previous_flow = previous["metrics"]["leak_flowrate"] or 0.0
        current_flow = current["metrics"]["leak_flowrate"] or 0.0
        total_leakage_volume += (previous_flow + current_flow) * elapsed / 2

    metrics = [step["metrics"] for step in time_steps]
    return {
        "minimum_service_availability": min(
            metric["service_availability"] for metric in metrics
        ),
        "maximum_pressure_violations": max(
            metric["pressure_violations"] for metric in metrics
        ),
        "maximum_affected_nodes": max(metric["affected_nodes"] for metric in metrics),
        "peak_leak_flowrate": max(metric["leak_flowrate"] or 0.0 for metric in metrics),
        "total_leakage_volume": total_leakage_volume,
    }

