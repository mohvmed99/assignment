from __future__ import annotations

import random
from copy import deepcopy

from src.models import ChargingPlan, Scenario
from src.route import RouteGraph
from src.simulator import Simulator


class Planner:
    """Assign charging plans per bus, then refine with local search."""

    def __init__(self, scenario: Scenario, seed: int = 42) -> None:
        self.scenario = scenario
        self.graph = RouteGraph(scenario.route, scenario.simulation)
        self.simulator = Simulator(scenario)
        self.random = random.Random(seed)
        self.plan_options = self._build_plan_options()

    def _build_plan_options(self) -> dict[str, list[ChargingPlan]]:
        options: dict[str, list[ChargingPlan]] = {}
        for bus in self.scenario.buses:
            plans = self.graph.enumerate_plans(bus.origin, bus.destination)
            if not plans:
                raise ValueError(f"No valid charging plan for bus {bus.id}")
            options[bus.id] = plans
        return options

    def build_schedule(self) -> "Schedule":
        from src.models import Schedule

        assignments = self._greedy_assignment()
        schedule = self.simulator.simulate(assignments)
        improved = self._local_search(assignments, schedule.metrics.weighted_total)
        return self.simulator.simulate(improved)

    def _complete_assignments(self, partial: dict[str, ChargingPlan]) -> dict[str, ChargingPlan]:
        completed = dict(partial)
        for bus in self.scenario.buses:
            if bus.id not in completed:
                completed[bus.id] = self.plan_options[bus.id][0]
        return completed

    def _greedy_assignment(self) -> dict[str, ChargingPlan]:
        assignments: dict[str, ChargingPlan] = {}
        buses = sorted(self.scenario.buses, key=lambda bus: bus.departure)

        for bus in buses:
            best_plan = self.plan_options[bus.id][0]
            best_cost = float("inf")
            for plan in self.plan_options[bus.id]:
                trial = self._complete_assignments({**assignments, bus.id: plan})
                cost = self.simulator.simulate(trial).metrics.weighted_total
                if cost < best_cost:
                    best_cost = cost
                    best_plan = plan
            assignments[bus.id] = best_plan

        return assignments

    def _local_search(
        self,
        assignments: dict[str, ChargingPlan],
        initial_cost: float,
        max_passes: int = 3,
    ) -> dict[str, ChargingPlan]:
        current = deepcopy(assignments)
        best_cost = initial_cost

        for _ in range(max_passes):
            improved = False
            bus_ids = [bus.id for bus in self.scenario.buses]
            self.random.shuffle(bus_ids)

            for bus_id in bus_ids:
                current_plan = current[bus_id]
                for plan in self.plan_options[bus_id]:
                    if plan == current_plan:
                        continue
                    trial = {**current, bus_id: plan}
                    cost = self.simulator.simulate(trial).metrics.weighted_total
                    if cost + 1e-9 < best_cost:
                        current[bus_id] = plan
                        best_cost = cost
                        improved = True
                        break

            if not improved:
                break

        return current
