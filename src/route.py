from __future__ import annotations

from src.models import ChargingPlan, RouteConfig, SimulationConfig
from src.time_utils import travel_minutes


class RouteGraph:
    """Route geometry and valid charging plans for a given origin/destination pair."""

    def __init__(self, route: RouteConfig, simulation: SimulationConfig) -> None:
        self.route = route
        self.simulation = simulation
        self._stop_index = {stop: index for index, stop in enumerate(route.stops)}
        self._positions_km = self._build_positions()

    def _build_positions(self) -> dict[str, float]:
        positions = {self.route.stops[0]: 0.0}
        total = 0.0
        for index, distance in enumerate(self.route.segment_distances_km):
            total += distance
            positions[self.route.stops[index + 1]] = total
        return positions

    def distance_km(self, from_stop: str, to_stop: str) -> float:
        start = self._positions_km[from_stop]
        end = self._positions_km[to_stop]
        if start <= end:
            return end - start
        return start - end

    def travel_min(self, from_stop: str, to_stop: str) -> int:
        return travel_minutes(self.distance_km(from_stop, to_stop), self.simulation.speed_kmh)

    def stations_between(self, origin: str, destination: str) -> list[str]:
        origin_index = self._stop_index[origin]
        destination_index = self._stop_index[destination]
        if origin_index < destination_index:
            ordered = self.route.stops[origin_index + 1 : destination_index]
        else:
            ordered = list(reversed(self.route.stops[destination_index + 1 : origin_index]))
        return [stop for stop in ordered if stop in self.route.scheduling_stations]

    def enumerate_plans(self, origin: str, destination: str) -> list[ChargingPlan]:
        candidates = self.stations_between(origin, destination)
        range_km = self.simulation.battery_range_km
        plans: list[ChargingPlan] = []

        def search(start_stop: str, station_index: int, chosen: list[str]) -> None:
            distance_to_destination = self.distance_km(start_stop, destination)
            if distance_to_destination <= range_km:
                if chosen:
                    plans.append(ChargingPlan(tuple(chosen)))
                return

            for index in range(station_index, len(candidates)):
                station = candidates[index]
                leg = self.distance_km(start_stop, station)
                if leg > range_km:
                    continue
                chosen.append(station)
                search(station, index + 1, chosen)
                chosen.pop()

        search(origin, 0, [])
        plans.sort(key=lambda plan: (plan.stop_count, plan.stations))
        return plans
