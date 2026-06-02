from __future__ import annotations

from collections import defaultdict

from src.models import BusSchedule, ScheduleMetrics, Weights


def compute_metrics(buses: list[BusSchedule], weights: Weights) -> ScheduleMetrics:
    waits = [bus.total_wait_min for bus in buses]
    individual = max(waits) + 0.25 * (sum(waits) / len(waits))

    operator_groups: dict[str, list[int]] = defaultdict(list)
    for bus in buses:
        operator_groups[bus.operator].append(bus.total_wait_min)

    operator_scores = []
    for operator_waits in operator_groups.values():
        operator_max = max(operator_waits)
        operator_spread = max(operator_waits) - min(operator_waits)
        operator_scores.append(operator_max + 0.5 * operator_spread)
    operator = sum(operator_scores) / len(operator_scores)

    overall = float(sum(waits))

    weighted_total = (
        weights.individual * individual
        + weights.operator * operator
        + weights.overall * overall
    )

    return ScheduleMetrics(
        individual=individual,
        operator=operator,
        overall=overall,
        weighted_total=weighted_total,
    )
