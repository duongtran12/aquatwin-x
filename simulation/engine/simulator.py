import math
from pathlib import Path
from typing import Any

from simulation.engine.inp_inspector import inspect_inp
from simulation.engine.metrics import safe_ratio, summarize_failure_steps
from simulation.engine.scenario import LeakScenario


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


def run_failure(
    network_path: str | Path,
    scenario: LeakScenario,
) -> dict[str, Any]:
    path = Path(network_path).resolve()
    source = inspect_inp(path)
    wntr = _load_wntr()

    baseline_network = wntr.network.WaterNetworkModel(str(path))
    baseline_network.options.hydraulic.demand_model = "PDD"
    baseline_results = wntr.sim.WNTRSimulator(baseline_network).run_sim()

    failure_network = wntr.network.WaterNetworkModel(str(path))
    failure_network.options.hydraulic.demand_model = "PDD"
    failure_network, leak_node_name = _add_pipe_leak(
        failure_network,
        wntr,
        scenario,
    )
    failure_results = wntr.sim.WNTRSimulator(failure_network).run_sim()

    baseline_pressure = baseline_results.node["pressure"]
    baseline_demand = baseline_results.node["demand"]
    failure_pressure = failure_results.node["pressure"]
    failure_demand = failure_results.node["demand"]
    leak_demand = failure_results.node.get("leak_demand")
    failure_flowrate = failure_results.link["flowrate"]
    junction_names = baseline_network.junction_name_list
    required_pressure = float(failure_network.options.hydraulic.required_pressure)

    time_steps = []
    for time_seconds in baseline_pressure.index:
        baseline_delivered = float(
            baseline_demand.loc[time_seconds, junction_names].sum()
        )
        failure_delivered = float(
            failure_demand.loc[time_seconds, junction_names].sum()
        )
        node_values = []
        pressure_violations = 0
        affected_nodes = 0

        for node_name in junction_names:
            normal_pressure = float(baseline_pressure.at[time_seconds, node_name])
            current_pressure = float(failure_pressure.at[time_seconds, node_name])
            pressure_change = current_pressure - normal_pressure
            if current_pressure < required_pressure:
                pressure_violations += 1
            if normal_pressure - current_pressure >= scenario.pressure_drop_threshold:
                affected_nodes += 1
            node_values.append(
                {
                    "id": node_name,
                    "baseline_pressure": _number(normal_pressure),
                    "failure_pressure": _number(current_pressure),
                    "pressure_change": _number(pressure_change),
                    "failure_demand": _number(
                        failure_demand.at[time_seconds, node_name]
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
                        failure_delivered,
                        baseline_delivered,
                    ),
                    "baseline_delivered_demand": _number(baseline_delivered),
                    "delivered_demand": _number(failure_delivered),
                    "minimum_pressure": _number(
                        failure_pressure.loc[time_seconds, junction_names].min()
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
                            failure_flowrate.at[time_seconds, link_name]
                        ),
                    }
                    for link_name in failure_network.link_name_list
                ],
            }
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

