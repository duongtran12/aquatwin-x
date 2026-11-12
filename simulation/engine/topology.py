from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from simulation.engine.valves import RecoveryAction, ValveRegistry, validate_actions


NODE_SECTIONS = {"JUNCTIONS", "RESERVOIRS", "TANKS"}
LINK_SECTIONS = {"PIPES", "PUMPS", "VALVES"}


def _read_topology(path: str | Path) -> tuple[set[str], set[str], dict[str, tuple[str, str]]]:
    nodes: set[str] = set()
    sources: set[str] = set()
    links: dict[str, tuple[str, str]] = {}
    current_section = ""

    for raw_line in Path(path).resolve().read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.split(";", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].upper()
            continue

        fields = line.split()
        if current_section in NODE_SECTIONS:
            nodes.add(fields[0])
            if current_section in {"RESERVOIRS", "TANKS"}:
                sources.add(fields[0])
        elif current_section in LINK_SECTIONS and len(fields) >= 3:
            links[fields[0]] = (fields[1], fields[2])

    return nodes, sources, links


def analyze_connectivity(
    network_path: str | Path,
    registry: ValveRegistry,
    actions: list[RecoveryAction],
) -> dict[str, Any]:
    validate_actions(registry, actions)
    nodes, sources, links = _read_topology(network_path)
    closed_links = {
        registry.get(action.valve_id).link_id
        for action in actions
        if action.status == "CLOSED"
    }

    adjacency: dict[str, set[str]] = defaultdict(set)
    for link_id, (start_node, end_node) in links.items():
        if link_id in closed_links:
            continue
        adjacency[start_node].add(end_node)
        adjacency[end_node].add(start_node)

    reachable = set(sources)
    queue = deque(sources)
    while queue:
        node = queue.popleft()
        for neighbor in adjacency[node]:
            if neighbor not in reachable:
                reachable.add(neighbor)
                queue.append(neighbor)

    isolated_nodes = sorted(nodes - reachable)
    return {
        "sources": sorted(sources),
        "closed_links": sorted(closed_links),
        "reachable_nodes": sorted(reachable),
        "isolated_nodes": isolated_nodes,
        "is_fully_connected": not isolated_nodes,
    }

