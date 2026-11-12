from dataclasses import asdict, dataclass
from pathlib import Path


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

