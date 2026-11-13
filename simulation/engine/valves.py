import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


ValveEndpoint = Literal["start", "end"]
ValveStatus = Literal["OPEN", "CLOSED"]


@dataclass(frozen=True)
class IsolationValve:
    valve_id: str
    link_id: str
    endpoint: ValveEndpoint

    def to_dict(self) -> dict[str, str]:
        return {
            "valve_id": self.valve_id,
            "link_id": self.link_id,
            "endpoint": self.endpoint,
        }


@dataclass(frozen=True)
class RecoveryAction:
    valve_id: str
    status: ValveStatus

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RecoveryAction":
        status = str(data["status"]).upper()
        if status not in {"OPEN", "CLOSED"}:
            raise ValueError("Trạng thái van chỉ nhận OPEN hoặc CLOSED")
        return cls(valve_id=str(data["valve_id"]), status=status)

    def to_dict(self) -> dict[str, str]:
        return {"valve_id": self.valve_id, "status": self.status}


class ValveRegistry:
    def __init__(self, network_name: str, valves: list[IsolationValve]) -> None:
        self.network_name = network_name
        self._valves = {valve.valve_id: valve for valve in valves}
        if len(self._valves) != len(valves):
            raise ValueError("Danh sách van có valve_id bị trùng")

    @property
    def valves(self) -> list[IsolationValve]:
        return list(self._valves.values())

    def get(self, valve_id: str) -> IsolationValve:
        try:
            return self._valves[valve_id]
        except KeyError as exc:
            raise ValueError(f"Không tìm thấy valve_id '{valve_id}'") from exc

    def resolve_link_id(
        self,
        valve_id: str,
        leak_pipe_id: str,
        leak_segment_id: str,
    ) -> str:
        valve = self.get(valve_id)
        if valve.link_id == leak_pipe_id and valve.endpoint == "end":
            return leak_segment_id
        return valve.link_id


def load_valve_registry(path: str | Path) -> ValveRegistry:
    file_path = Path(path).resolve()
    data = json.loads(file_path.read_text(encoding="utf-8-sig"))
    valves = [
        IsolationValve(
            valve_id=str(item["valve_id"]),
            link_id=str(item["link_id"]),
            endpoint=str(item["endpoint"]).lower(),
        )
        for item in data["valves"]
    ]
    if any(valve.endpoint not in {"start", "end"} for valve in valves):
        raise ValueError("endpoint của van chỉ nhận start hoặc end")
    return ValveRegistry(str(data["network"]), valves)


def load_recovery_actions(path: str | Path) -> list[RecoveryAction]:
    file_path = Path(path).resolve()
    data = json.loads(file_path.read_text(encoding="utf-8-sig"))
    actions = [RecoveryAction.from_dict(item) for item in data["actions"]]
    action_ids = [action.valve_id for action in actions]
    if len(action_ids) != len(set(action_ids)):
        raise ValueError("Một van chỉ được xuất hiện một lần trong danh sách hành động")
    return actions


def validate_actions(
    registry: ValveRegistry,
    actions: list[RecoveryAction],
) -> None:
    for action in actions:
        registry.get(action.valve_id)

