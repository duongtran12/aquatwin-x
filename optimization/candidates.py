from itertools import combinations

from simulation.engine.valves import RecoveryAction, ValveRegistry


def generate_closure_candidates(
    registry: ValveRegistry,
    max_actions: int = 2,
) -> list[list[RecoveryAction]]:
    if max_actions < 0:
        raise ValueError("max_actions không được âm")

    valve_ids = sorted(valve.valve_id for valve in registry.valves)
    candidates: list[list[RecoveryAction]] = []
    for action_count in range(min(max_actions, len(valve_ids)) + 1):
        for selected_valves in combinations(valve_ids, action_count):
            candidates.append(
                [
                    RecoveryAction(valve_id=valve_id, status="CLOSED")
                    for valve_id in selected_valves
                ]
            )
    return candidates

