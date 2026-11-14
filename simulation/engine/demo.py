import math
from collections import defaultdict, deque
from math import comb
from pathlib import Path
from typing import Any

from simulation.engine.inp_inspector import inspect_inp, read_inp_elements
from simulation.engine.metrics import summarize_failure_steps
from simulation.engine.scenario import LeakScenario
from simulation.engine.topology import analyze_connectivity
from simulation.engine.valves import RecoveryAction, ValveRegistry, validate_actions


DEMO_WARNING = "Synthetic demo data is active because the WNTR runtime is unavailable. Do not use these values in the experimental report."


def _junctions(elements: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    return [node for node in elements["nodes"] if node["type"] == "junction"]


def _distances(elements: dict[str, list[dict[str, Any]]], pipe_id: str) -> dict[str, int]:
    links = elements["links"]
    selected = next((link for link in links if link["id"] == pipe_id), None)
    if selected is None:
        raise ValueError(f"Pipe '{pipe_id}' does not exist in the network")
    adjacency: dict[str, set[str]] = defaultdict(set)
    for link in links:
        adjacency[link["source"]].add(link["target"])
        adjacency[link["target"]].add(link["source"])
    distances = {selected["source"]: 0, selected["target"]: 0}
    queue = deque(distances)
    while queue:
        node = queue.popleft()
        for neighbor in adjacency[node]:
            if neighbor not in distances:
                distances[neighbor] = distances[node] + 1
                queue.append(neighbor)
    return distances


def _baseline_pressure(node: dict[str, Any], index: int) -> float:
    return 38.0 - index * 1.8 - float(node.get("elevation", 0)) * 0.08


def _build_impact_steps(
    elements: dict[str, list[dict[str, Any]]],
    scenario: LeakScenario,
    recovery_strength: float = 0.0,
    service_penalty: float = 0.0,
) -> list[dict[str, Any]]:
    junctions = _junctions(elements)
    distances = _distances(elements, scenario.pipe_id)
    base_demands = {node["id"]: float(node.get("base_demand", 0)) for node in junctions}
    total_baseline_demand = sum(base_demands.values())
    severity = min(2.2, scenario.leak_area / 0.0005)
    pressure_recovery = 1.0 - 0.78 * recovery_strength
    leak_multiplier = 1.0 - 0.90 * recovery_strength
    steps = []

    for time_seconds in range(0, 86401, 3600):
        active = scenario.start_time <= time_seconds <= scenario.end_time
        hour_factor = 0.92 + 0.08 * math.sin(time_seconds / 86400 * math.tau)
        node_values = []
        delivered_demand = 0.0
        pressure_violations = 0
        affected_nodes = 0

        for index, node in enumerate(junctions):
            baseline_pressure = _baseline_pressure(node, index) * hour_factor
            distance_factor = 1.0 / (1.0 + 0.65 * distances.get(node["id"], 3))
            raw_drop = 14.0 * severity * distance_factor if active else 0.0
            pressure_change = -raw_drop * pressure_recovery
            state_pressure = max(0.0, baseline_pressure + pressure_change)
            pressure_service = min(1.0, math.sqrt(max(state_pressure, 0.0) / 20.0))
            service = max(0.0, pressure_service - service_penalty)
            demand = base_demands[node["id"]] * service
            delivered_demand += demand
            if state_pressure < 20.0:
                pressure_violations += 1
            if -pressure_change >= scenario.pressure_drop_threshold:
                affected_nodes += 1
            node_values.append(
                {
                    "id": node["id"],
                    "baseline_pressure": round(baseline_pressure, 6),
                    "state_pressure": round(state_pressure, 6),
                    "pressure_change": round(pressure_change, 6),
                    "state_demand": round(demand, 6),
                }
            )

        leak_flow = 0.0
        if active:
            representative_head = 30.0
            leak_flow = (
                scenario.discharge_coefficient
                * scenario.leak_area
                * math.sqrt(2 * 9.81 * representative_head)
                * leak_multiplier
            )
        steps.append(
            {
                "time_seconds": time_seconds,
                "metrics": {
                    "service_availability": (
                        delivered_demand / total_baseline_demand
                        if total_baseline_demand > 0
                        else 1.0
                    ),
                    "baseline_delivered_demand": total_baseline_demand,
                    "delivered_demand": round(delivered_demand, 6),
                    "minimum_pressure": min(node["state_pressure"] for node in node_values),
                    "pressure_violations": pressure_violations,
                    "affected_nodes": affected_nodes,
                    "leak_flowrate": round(leak_flow, 9),
                },
                "nodes": node_values,
                "links": [
                    {"id": link["id"], "flowrate": round(0.004 + index * 0.0004, 6)}
                    for index, link in enumerate(elements["links"])
                ],
            }
        )
    return steps


def run_demo_baseline(network_path: str | Path) -> dict[str, Any]:
    path = Path(network_path).resolve()
    source = inspect_inp(path)
    elements = read_inp_elements(path)
    junctions = _junctions(elements)
    steps = []
    for time_seconds in range(0, 86401, 3600):
        hour_factor = 0.92 + 0.08 * math.sin(time_seconds / 86400 * math.tau)
        nodes = [
            {
                "id": node["id"],
                "pressure": round(_baseline_pressure(node, index) * hour_factor, 6),
                "demand": node.get("base_demand", 0),
            }
            for index, node in enumerate(junctions)
        ]
        steps.append(
            {
                "time_seconds": time_seconds,
                "metrics": {
                    "minimum_pressure": min(node["pressure"] for node in nodes),
                    "average_pressure": sum(node["pressure"] for node in nodes) / len(nodes),
                    "delivered_demand": sum(float(node["demand"]) for node in nodes),
                },
                "nodes": nodes,
                "links": [
                    {"id": link["id"], "flowrate": round(0.004 + index * 0.0004, 6)}
                    for index, link in enumerate(elements["links"])
                ],
            }
        )
    return {"scenario": "baseline", "network": source.to_dict(), "elements": elements, "time_steps": steps}


def run_demo_failure(network_path: str | Path, scenario: LeakScenario) -> dict[str, Any]:
    path = Path(network_path).resolve()
    source = inspect_inp(path)
    elements = read_inp_elements(path)
    steps = _build_impact_steps(elements, scenario)
    return {
        "scenario": "pipe_leak",
        "configuration": scenario.to_dict(),
        "network": source.to_dict(),
        "leak_node_id": f"{scenario.pipe_id}_DEMO_LEAK_NODE",
        "elements": elements,
        "summary": summarize_failure_steps(steps),
        "time_steps": steps,
    }


def _applied_actions(registry: ValveRegistry, actions: list[RecoveryAction]) -> list[dict[str, str]]:
    return [
        {
            "valve_id": action.valve_id,
            "link_id": registry.get(action.valve_id).link_id,
            "status": action.status,
        }
        for action in actions
    ]


def run_demo_manual_recovery(
    network_path: str | Path,
    scenario: LeakScenario,
    registry: ValveRegistry,
    actions: list[RecoveryAction],
) -> dict[str, Any]:
    validate_actions(registry, actions)
    path = Path(network_path).resolve()
    source = inspect_inp(path)
    elements = read_inp_elements(path)
    failure_steps = _build_impact_steps(elements, scenario)
    targeted = sum(
        action.status == "CLOSED" and registry.get(action.valve_id).link_id == scenario.pipe_id
        for action in actions
    )
    recovery_strength = min(1.0, targeted / 2 + max(0, len(actions) - targeted) * 0.08)
    service_penalty = max(0, len(actions) - targeted) * 0.025
    recovery_steps = _build_impact_steps(elements, scenario, recovery_strength, service_penalty)
    failure_summary = summarize_failure_steps(failure_steps)
    recovery_summary = summarize_failure_steps(recovery_steps)
    return {
        "scenario": "manual_recovery",
        "configuration": scenario.to_dict(),
        "network": source.to_dict(),
        "actions": _applied_actions(registry, actions),
        "topology": analyze_connectivity(path, registry, actions),
        "failure": {"summary": failure_summary, "time_steps": failure_steps},
        "recovery": {"summary": recovery_summary, "time_steps": recovery_steps},
        "improvement": {
            "service_availability_gain": recovery_summary["minimum_service_availability"] - failure_summary["minimum_service_availability"],
            "pressure_violations_reduced": failure_summary["maximum_pressure_violations"] - recovery_summary["maximum_pressure_violations"],
            "affected_nodes_reduced": failure_summary["maximum_affected_nodes"] - recovery_summary["maximum_affected_nodes"],
            "leakage_volume_reduced": failure_summary["total_leakage_volume"] - recovery_summary["total_leakage_volume"],
        },
    }


def _demo_candidate(
    network_path: str | Path,
    scenario: LeakScenario,
    registry: ValveRegistry,
    actions: list[RecoveryAction],
) -> dict[str, Any]:
    result = run_demo_manual_recovery(network_path, scenario, registry, actions)
    summary = result["recovery"]["summary"]
    failure = result["failure"]["summary"]
    node_count = max(1, inspect_inp(network_path).junctions)
    service = float(summary["minimum_service_availability"])
    pressure = max(0.0, 1.0 - float(summary["maximum_pressure_violations"]) / node_count)
    affected = max(0.0, 1.0 - float(summary["maximum_affected_nodes"]) / node_count)
    failure_leakage = max(float(failure["total_leakage_volume"]), 1e-9)
    leakage = max(0.0, 1.0 - float(summary["total_leakage_volume"]) / failure_leakage)
    action_score = 1.0 / (1.0 + len(actions))
    score = (service * 0.40 + pressure * 0.20 + leakage * 0.20 + affected * 0.15 + action_score * 0.05) * 100
    return {
        "feasible": True,
        "actions": [action.to_dict() for action in actions],
        "score": round(score, 6),
        "summary": summary,
        "topology": result["topology"],
        "computation_time_seconds": 0.0,
    }


def run_demo_optimization(
    network_path: str | Path,
    scenario: LeakScenario,
    registry: ValveRegistry,
    algorithm: str = "ga",
    generations: int = 20,
    seed: int = 42,
    max_actions: int = 2,
    top_k: int = 5,
) -> dict[str, Any]:
    pipe_valves = sorted(
        [valve for valve in registry.valves if valve.link_id == scenario.pipe_id],
        key=lambda valve: valve.valve_id,
    )
    actions = [RecoveryAction(valve.valve_id, "CLOSED") for valve in pipe_valves[:max_actions]]
    best = _demo_candidate(network_path, scenario, registry, actions)
    failure = run_demo_failure(network_path, scenario)["summary"]
    valve_count = len(registry.valves)
    candidate_count = sum(
        comb(valve_count, count)
        for count in range(min(max_actions, valve_count) + 1)
    )
    if algorithm == "exhaustive":
        return {
            "algorithm": "demo_exhaustive_search",
            "scenario": scenario.to_dict(),
            "candidate_count": candidate_count,
            "feasible_count": candidate_count,
            "failed_count": 0,
            "computation_time_seconds": 0.01,
            "failure_summary": failure,
            "isolation_baseline": best,
            "best_candidate": best,
            "ranking": [best],
        }
    history = []
    final_score = float(best["score"])
    for generation in range(generations):
        progress = (generation + 1) / generations
        history.append(
            {
                "generation": generation,
                "best_score": round(final_score - 18 * (1 - progress) ** 2, 6),
                "average_score": round(final_score - 28 * (1 - progress) - 4, 6),
                "feasible_count": 20,
                "unique_evaluated_count": min(38, 10 + generation * 2),
            }
        )
    return {
        "algorithm": "demo_genetic_algorithm",
        "scenario": scenario.to_dict(),
        "config": {"population_size": 20, "generations": generations, "seed": seed},
        "unique_evaluated_count": history[-1]["unique_evaluated_count"],
        "feasible_count": history[-1]["unique_evaluated_count"],
        "failed_count": 0,
        "computation_time_seconds": 0.02,
        "failure_summary": failure,
        "isolation_baseline": best,
        "best_candidate": best,
        "ranking": [best],
        "history": history,
    }
