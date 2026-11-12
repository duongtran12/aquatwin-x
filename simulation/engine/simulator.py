import math
from pathlib import Path
from typing import Any

from simulation.engine.inp_inspector import inspect_inp


def _number(value: Any) -> float | None:
    number = float(value)
    return number if math.isfinite(number) else None


def _load_wntr() -> Any:
    try:
        import wntr
    except ImportError as exc:
        raise RuntimeError(
            "WNTR chưa được cài đặt. Hãy chạy pip install -r backend/requirements.txt"
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

