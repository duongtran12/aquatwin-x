from simulation.engine.valves import RecoveryAction, ValveRegistry


def build_isolation_baseline(
    registry: ValveRegistry,
    failed_pipe_id: str,
) -> list[RecoveryAction]:
    valves = sorted(
        (
            valve
            for valve in registry.valves
            if valve.link_id == failed_pipe_id
        ),
        key=lambda valve: valve.endpoint,
    )
    if len(valves) < 2:
        raise ValueError(
            f"Pipe '{failed_pipe_id}' cần ít nhất hai van để tạo baseline cô lập"
        )
    return [RecoveryAction(valve.valve_id, "CLOSED") for valve in valves]

