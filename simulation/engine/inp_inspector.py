from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


NETWORK_SECTIONS = {
    "JUNCTIONS": "junctions",
    "RESERVOIRS": "reservoirs",
    "TANKS": "tanks",
    "PIPES": "pipes",
    "PUMPS": "pumps",
    "VALVES": "valves",
}


@dataclass(frozen=True)
class InpSummary:
    name: str
    path: str
    title: str
    junctions: int
    reservoirs: int
    tanks: int
    pipes: int
    pumps: int
    valves: int

    @property
    def total_nodes(self) -> int:
        return self.junctions + self.reservoirs + self.tanks

    @property
    def total_links(self) -> int:
        return self.pipes + self.pumps + self.valves

    def to_dict(self) -> dict[str, str | int]:
        return {
            **asdict(self),
            "total_nodes": self.total_nodes,
            "total_links": self.total_links,
        }


def inspect_inp(network_path: str | Path) -> InpSummary:
    path = Path(network_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy file mạng: {path}")
    if path.suffix.lower() != ".inp":
        raise ValueError("File mạng phải có định dạng EPANET INP")

    counts = {field_name: 0 for field_name in NETWORK_SECTIONS.values()}
    title_lines: list[str] = []
    current_section = ""

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(";"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].upper()
            continue
        if current_section == "TITLE":
            title_lines.append(line)
        if current_section in NETWORK_SECTIONS:
            counts[NETWORK_SECTIONS[current_section]] += 1

    return InpSummary(
        name=path.stem,
        path=str(path),
        title=" ".join(title_lines),
        **counts,
    )


def read_inp_elements(network_path: str | Path) -> dict[str, list[dict[str, Any]]]:
    path = Path(network_path).resolve()
    inspect_inp(path)
    sections: dict[str, list[list[str]]] = {}
    current_section = ""

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.split(";", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].upper()
            sections.setdefault(current_section, [])
            continue
        sections.setdefault(current_section, []).append(line.split())

    coordinates = {
        fields[0]: (float(fields[1]), float(fields[2]))
        for fields in sections.get("COORDINATES", [])
        if len(fields) >= 3
    }
    nodes: list[dict[str, Any]] = []
    for fields in sections.get("JUNCTIONS", []):
        x, y = coordinates.get(fields[0], (0.0, 0.0))
        nodes.append(
            {
                "id": fields[0],
                "type": "junction",
                "x": x,
                "y": y,
                "elevation": float(fields[1]),
                "base_demand": float(fields[2]) if len(fields) >= 3 else 0.0,
            }
        )
    for section, node_type, value_name in (
        ("RESERVOIRS", "reservoir", "base_head"),
        ("TANKS", "tank", "elevation"),
    ):
        for fields in sections.get(section, []):
            x, y = coordinates.get(fields[0], (0.0, 0.0))
            nodes.append(
                {
                    "id": fields[0],
                    "type": node_type,
                    "x": x,
                    "y": y,
                    value_name: float(fields[1]),
                }
            )

    links: list[dict[str, Any]] = []
    for fields in sections.get("PIPES", []):
        links.append(
            {
                "id": fields[0],
                "type": "pipe",
                "source": fields[1],
                "target": fields[2],
                "length": float(fields[3]),
                "diameter": float(fields[4]),
                "roughness": float(fields[5]),
                "status": fields[7].upper() if len(fields) >= 8 else "OPEN",
            }
        )
    for section, link_type in (("PUMPS", "pump"), ("VALVES", "valve")):
        for fields in sections.get(section, []):
            links.append(
                {
                    "id": fields[0],
                    "type": link_type,
                    "source": fields[1],
                    "target": fields[2],
                }
            )
    return {"nodes": nodes, "links": links}

