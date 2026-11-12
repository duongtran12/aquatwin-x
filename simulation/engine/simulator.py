import math
from pathlib import Path
from typing import Any

from simulation.engine.inp_inspector import inspect_inp
from simulation.engine.metrics import safe_ratio, summarize_failure_steps
from simulation.engine.scenario import LeakScenario
from simulation.engine.topology import analyze_connectivity
from simulation.engine.valves import RecoveryAction, ValveRegistry, validate_actions


def _number(value: Any) -> float | None:
    number = float(value)
    return number if math.isfinite(number) else None


def _load_wntr() -> Any:
    try:
        import wntr
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "WNTR is not installed. Run: pip install -r backend/requirements.txt"
        ) from exc
    except ImportError as exc:
        raise RuntimeError(
            "WNTR is installed but could not load a native dependency. "
            "Check the original DLL or application-control error."
        ) from exc
    return wntr


def _network_elements(network: Any) -> dict[str, list[dict[str, Any]]]:
    nodes = []
    for node_name, node in network.nodes():
        x, y = node.coordinates
        node_payload: dict[str, Any] = {
            "id": node_name,
            "type": node.__class__.__name__.lower(),
            "x": _number(x),
            "y": _number(y),
        }
        for attribute in ("elevation", "base_head", "init_level"):
            if hasattr(node, attribute):
                node_payload[attribute] = _number(getattr(node, attribute))
        if hasattr(node, "base_demand"):
            node_payload["base_demand"] = _number(node.base_demand)
        nodes.append(node_payload)

    links = []
    for link_name, link in network.links():
        link_payload: dict[str, Any] = {
            "id": link_name,
            "type": link.__class__.__name__.lower(),
            "source": link.start_node_name,
            "target": link.end_node_name,
        }
        for attribute in ("length", "diameter", "roughness"):
            if hasattr(link, attribute):
                link_payload[attribute] = _number(getattr(link, attribute))
        links.append(link_payload)

    return {"nodes": nodes, "links": links}


def run_baseline(network_path: str | Path) -> dict[str, Any]:
    path = Path(network_path).resolve()
    source = inspect_inp(path)
    wntr = _load_wntr()
    network = wntr.network.WaterNetworkModel(str(path))

    network.options.hydraulic.demand_model = "PDD"
    simulator = wntr.sim.WNTRSimulator(network)
    results = simulator.run_sim()

    pressure = results.node["pressure"]
    demand = results.node["demand"]
    flowrate = results.link["flowrate"]
    velocity = results.link.get("velocity")
    status = results.link.get("status")
    junction_names = network.junction_name_list

    time_steps = []
    for time_seconds in pressure.index:
        node_values = [
            {
                "id": node_name,
                "pressure": _number(pressure.at[time_seconds, node_name]),
                "demand": _number(demand.at[time_seconds, node_name]),
            }
            for node_name in network.node_name_list
        ]
        link_values = []
        for link_name in network.link_name_list:
            payload = {
                "id": link_name,
                "flowrate": _number(flowrate.at[time_seconds, link_name]),
            }
            if velocity is not None:
                payload["velocity"] = _number(velocity.at[time_seconds, link_name])
            if status is not None:
                payload["status"] = _number(status.at[time_seconds, link_name])
            link_values.append(payload)

        junction_pressures = pressure.loc[time_seconds, junction_names]
        time_steps.append(
            {
                "time_seconds": int(time_seconds),
                "metrics": {
                    "minimum_pressure": _number(junction_pressures.min()),
                    "average_pressure": _number(junction_pressures.mean()),
                    "delivered_demand": _number(
                        demand.loc[time_seconds, junction_names].sum()
                    ),
                },
                "nodes": node_values,
                "links": link_values,
            }
        )

    return {
        "scenario": "baseline",
        "network": source.to_dict(),
        "elements": _network_elements(network),
        "time_steps": time_steps,
    }


def _add_pipe_leak(network: Any, wntr: Any, scenario: LeakScenario) -> tuple[Any, str]:
    if scenario.pipe_id not in network.pipe_name_list:
        raise ValueError(f"Không tìm thấy pipe_id '{scenario.pipe_id}' trong mạng")
    if scenario.end_time > network.options.time.duration:
        raise ValueError("end_time vượt quá thời lượng mô phỏng của mạng")

    leak_node_name = f"{scenario.pipe_id}_LEAK_NODE"
    leak_pipe_name = f"{scenario.pipe_id}_LEAK_SEGMENT"
    network = wntr.morph.split_pipe(
        network,
        scenario.pipe_id,
        leak_pipe_name,
        leak_node_name,
        split_at_point=scenario.split_position,
        return_copy=True,
    )
    leak_node = network.get_node(leak_node_name)
    leak_node.add_leak(
        network,
        area=scenario.leak_area,
        discharge_coeff=scenario.discharge_coefficient,
        start_time=scenario.start_time,
        end_time=scenario.end_time,
    )
    return network, leak_node_name


def _build_impact_steps(
    baseline_network: Any,
    baseline_results: Any,
    state_network: Any,
    state_results: Any,
    leak_node_name: str,
    scenario: LeakScenario,
) -> list[dict[str, Any]]:
    baseline_pressure = baseline_results.node["pressure"]
    baseline_demand = baseline_results.node["demand"]
    state_pressure = state_results.node["pressure"]
    state_demand = state_results.node["demand"]
    leak_demand = state_results.node.get("leak_demand")
    state_flowrate = state_results.link["flowrate"]
    junction_names = baseline_network.junction_name_list
    required_pressure = float(state_network.options.hydraulic.required_pressure)

    time_steps = []
    for time_seconds in baseline_pressure.index:
        baseline_delivered = float(
            baseline_demand.loc[time_seconds, junction_names].sum()
        )
        state_delivered = float(
            state_demand.loc[time_seconds, junction_names].sum()
        )
        node_values = []
        pressure_violations = 0
        affected_nodes = 0

        for node_name in junction_names:
            normal_pressure = float(baseline_pressure.at[time_seconds, node_name])
            current_pressure = float(state_pressure.at[time_seconds, node_name])
            pressure_change = current_pressure - normal_pressure
            if current_pressure < required_pressure:
                pressure_violations += 1
            if normal_pressure - current_pressure >= scenario.pressure_drop_threshold:
                affected_nodes += 1
            node_values.append(
                {
                    "id": node_name,
                    "baseline_pressure": _number(normal_pressure),
                    "state_pressure": _number(current_pressure),
                    "pressure_change": _number(pressure_change),
                    "state_demand": _number(
                        state_demand.at[time_seconds, node_name]
                    ),
                }
            )

        current_leak_flow = 0.0
        if leak_demand is not None:
            current_leak_flow = float(
                leak_demand.at[time_seconds, leak_node_name]
            )

        time_steps.append(
            {
                "time_seconds": int(time_seconds),
                "metrics": {
                    "service_availability": safe_ratio(
                        state_delivered,
                        baseline_delivered,
                    ),
                    "baseline_delivered_demand": _number(baseline_delivered),
                    "delivered_demand": _number(state_delivered),
                    "minimum_pressure": _number(
                        state_pressure.loc[time_seconds, junction_names].min()
                    ),
                    "pressure_violations": pressure_violations,
                    "affected_nodes": affected_nodes,
                    "leak_flowrate": _number(current_leak_flow),
                },
                "nodes": node_values,
                "links": [
                    {
                        "id": link_name,
                        "flowrate": _number(
                            state_flowrate.at[time_seconds, link_name]
                        ),
                    }
                    for link_name in state_network.link_name_list
                ],
            }
        )
    return time_steps


def _new_pdd_network(wntr: Any, path: Path) -> Any:
    network = wntr.network.WaterNetworkModel(str(path))
    network.options.hydraulic.demand_model = "PDD"
    return network


def run_failure(
    network_path: str | Path,
    scenario: LeakScenario,
) -> dict[str, Any]:
    path = Path(network_path).resolve()
    source = inspect_inp(path)
    wntr = _load_wntr()

    baseline_network = _new_pdd_network(wntr, path)
    baseline_results = wntr.sim.WNTRSimulator(baseline_network).run_sim()

    failure_network = _new_pdd_network(wntr, path)
    failure_network, leak_node_name = _add_pipe_leak(
        failure_network,
        wntr,
        scenario,
    )
    failure_results = wntr.sim.WNTRSimulator(failure_network).run_sim()
    time_steps = _build_impact_steps(
        baseline_network,
        baseline_results,
        failure_network,
        failure_results,
        leak_node_name,
        scenario,
    )

    return {
        "scenario": "pipe_leak",
        "configuration": scenario.to_dict(),
        "network": source.to_dict(),
        "leak_node_id": leak_node_name,
        "elements": _network_elements(failure_network),
        "summary": summarize_failure_steps(time_steps),
        "time_steps": time_steps,
    }


def _apply_recovery_actions(
    network: Any,
    registry: ValveRegistry,
    actions: list[RecoveryAction],
    leak_pipe_id: str,
) -> list[dict[str, str]]:
    validate_actions(registry, actions)
    leak_segment_id = f"{leak_pipe_id}_LEAK_SEGMENT"
    applied_actions = []

    for action in actions:
        link_id = registry.resolve_link_id(
            action.valve_id,
            leak_pipe_id,
            leak_segment_id,
        )
        if link_id not in network.link_name_list:
            raise ValueError(f"Không tìm thấy link '{link_id}' để thao tác van")
        network.get_link(link_id).initial_status = 0 if action.status == "CLOSED" else 1
        applied_actions.append(
            {
                "valve_id": action.valve_id,
                "link_id": link_id,
                "status": action.status,
            }
        )

    return applied_actions


def run_manual_recovery(
    network_path: str | Path,
    scenario: LeakScenario,
    registry: ValveRegistry,
    actions: list[RecoveryAction],
) -> dict[str, Any]:
    path = Path(network_path).resolve()
    source = inspect_inp(path)
    if registry.network_name != source.name:
        raise ValueError("Danh sách van không thuộc mạng đang mô phỏng")

    wntr = _load_wntr()
    baseline_network = _new_pdd_network(wntr, path)
    baseline_results = wntr.sim.WNTRSimulator(baseline_network).run_sim()

    failure_network = _new_pdd_network(wntr, path)
    failure_network, failure_leak_node = _add_pipe_leak(
        failure_network,
        wntr,
        scenario,
    )
    failure_results = wntr.sim.WNTRSimulator(failure_network).run_sim()
    failure_steps = _build_impact_steps(
        baseline_network,
        baseline_results,
        failure_network,
        failure_results,
        failure_leak_node,
        scenario,
    )

    recovery_network = _new_pdd_network(wntr, path)
    recovery_network, recovery_leak_node = _add_pipe_leak(
        recovery_network,
        wntr,
        scenario,
    )
    applied_actions = _apply_recovery_actions(
        recovery_network,
        registry,
        actions,
        scenario.pipe_id,
    )
    recovery_results = wntr.sim.WNTRSimulator(recovery_network).run_sim()
    recovery_steps = _build_impact_steps(
        baseline_network,
        baseline_results,
        recovery_network,
        recovery_results,
        recovery_leak_node,
        scenario,
    )

    failure_summary = summarize_failure_steps(failure_steps)
    recovery_summary = summarize_failure_steps(recovery_steps)
    topology = analyze_connectivity(path, registry, actions)
    return {
        "scenario": "manual_recovery",
        "configuration": scenario.to_dict(),
        "network": source.to_dict(),
        "actions": applied_actions,
        "topology": topology,
        "failure": {
            "summary": failure_summary,
            "time_steps": failure_steps,
        },
        "recovery": {
            "summary": recovery_summary,
            "time_steps": recovery_steps,
        },
        "improvement": {
            "service_availability_gain": (
                recovery_summary["minimum_service_availability"]
                - failure_summary["minimum_service_availability"]
            ),
            "pressure_violations_reduced": (
                failure_summary["maximum_pressure_violations"]
                - recovery_summary["maximum_pressure_violations"]
            ),
            "affected_nodes_reduced": (
                failure_summary["maximum_affected_nodes"]
                - recovery_summary["maximum_affected_nodes"]
            ),
            "leakage_volume_reduced": (
                failure_summary["total_leakage_volume"]
                - recovery_summary["total_leakage_volume"]
            ),
        },
    }

