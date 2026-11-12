import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LeakScenario:
    pipe_id: str
    leak_area: float
    start_time: int
    end_time: int
    split_position: float = 0.5
    discharge_coefficient: float = 0.75
    pressure_drop_threshold: float = 2.0

    def __post_init__(self) -> None:
        if not self.pipe_id.strip():
            raise ValueError("pipe_id không được để trống")
        if self.leak_area <= 0:
            raise ValueError("leak_area phải lớn hơn 0")
        if self.start_time < 0:
            raise ValueError("start_time không được âm")
        if self.end_time <= self.start_time:
            raise ValueError("end_time phải lớn hơn start_time")
        if not 0.05 <= self.split_position <= 0.95:
            raise ValueError("split_position phải nằm trong đoạn 0.05 đến 0.95")
        if not 0 < self.discharge_coefficient <= 1:
            raise ValueError("discharge_coefficient phải thuộc đoạn (0, 1]")
        if self.pressure_drop_threshold < 0:
            raise ValueError("pressure_drop_threshold không được âm")

    def to_dict(self) -> dict[str, str | int | float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LeakScenario":
        return cls(
            pipe_id=str(data["pipe_id"]),
            leak_area=float(data["leak_area"]),
            start_time=int(data["start_time"]),
            end_time=int(data["end_time"]),
            split_position=float(data.get("split_position", 0.5)),
            discharge_coefficient=float(data.get("discharge_coefficient", 0.75)),
            pressure_drop_threshold=float(data.get("pressure_drop_threshold", 2.0)),
        )


def load_leak_scenario(scenario_path: str | Path) -> LeakScenario:
    path = Path(scenario_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy file kịch bản: {path}")

    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("Nội dung kịch bản phải là một JSON object")
    return LeakScenario.from_dict(data)

