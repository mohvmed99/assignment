from __future__ import annotations

from collections import defaultdict

from src.metrics import compute_metrics
from src.models import (
    BusInput,
    BusSchedule,
    ChargingPlan,
    Schedule,
    Scenario,
    StationChargeRecord,
    TimelineEvent,
)
from src.route import RouteGraph
from src.time_utils import parse_time


class Simulator:
    """Discrete-event charger queue simulation for fixed per-bus charging plans."""

    def __init__(self, scenario: Scenario) -> None:
        self.scenario = scenario
        self.graph = RouteGraph(scenario.route, scenario.simulation)

    def simulate(self, assignments: dict[str, ChargingPlan]) -> Schedule:
        station_records: dict[str, list[StationChargeRecord]] = defaultdict(list)
        charger_slots: dict[str, list[int]] = {
            station: [0] * self.scenario.route.charger_count(station)
            for station in self.scenario.route.scheduling_stations
        }
        bus_schedules: list[BusSchedule] = []

        buses = sorted(self.scenario.buses, key=lambda bus: parse_time(bus.departure))
        for bus in buses:
            plan = assignments[bus.id]
            bus_schedule = self._simulate_bus(bus, plan, charger_slots, station_records)
            bus_schedules.append(bus_schedule)

        metrics = compute_metrics(bus_schedules, self.scenario.weights)
        return Schedule(
            scenario_id=self.scenario.id,
            buses=bus_schedules,
            stations={
                station: sorted(records, key=lambda record: record.charge_start)
                for station, records in station_records.items()
            },
            metrics=metrics,
        )

    def _simulate_bus(
        self,
        bus: BusInput,
        plan: ChargingPlan,
        charger_slots: dict[str, list[int]],
        station_records: dict[str, list[StationChargeRecord]],
    ) -> BusSchedule:
        simulation = self.scenario.simulation
        graph = self.graph

        departure = parse_time(bus.departure)
        current_time = departure
        current_location = bus.origin
        total_wait = 0
        events: list[TimelineEvent] = [
            TimelineEvent(type="depart", location=bus.origin, time=departure)
        ]

        for station in plan.stations:
            travel = graph.travel_min(current_location, station)
            arrival = current_time + travel
            events.append(TimelineEvent(type="arrive", location=station, time=arrival))

            charge_start = self._allocate_charger(
                station, arrival, charger_slots, simulation.charge_duration_min
            )
            wait = charge_start - arrival
            total_wait += wait

            if wait > 0:
                events.append(
                    TimelineEvent(
                        type="wait_start",
                        location=station,
                        time=arrival,
                        wait_min=wait,
                    )
                )

            charge_end = charge_start + simulation.charge_duration_min
            events.append(
                TimelineEvent(
                    type="charge_start",
                    location=station,
                    time=charge_start,
                    wait_min=wait,
                )
            )
            events.append(
                TimelineEvent(
                    type="charge_end",
                    location=station,
                    time=charge_end,
                    duration_min=simulation.charge_duration_min,
                )
            )

            station_records[station].append(
                StationChargeRecord(
                    bus_id=bus.id,
                    arrival=arrival,
                    charge_start=charge_start,
                    charge_end=charge_end,
                    wait_min=wait,
                )
            )

            current_time = charge_end
            current_location = station

        final_travel = graph.travel_min(current_location, bus.destination)
        arrival = current_time + final_travel
        events.append(
            TimelineEvent(type="arrive_destination", location=bus.destination, time=arrival)
        )

        return BusSchedule(
            id=bus.id,
            operator=bus.operator,
            origin=bus.origin,
            destination=bus.destination,
            departure=departure,
            arrival=arrival,
            charging_stations=list(plan.stations),
            total_wait_min=total_wait,
            events=events,
        )

    @staticmethod
    def _allocate_charger(
        station: str,
        arrival: int,
        charger_slots: dict[str, list[int]],
        charge_duration_min: int,
    ) -> int:
        slots = charger_slots[station]
        earliest_index = min(range(len(slots)), key=lambda index: slots[index])
        charge_start = max(arrival, slots[earliest_index])
        slots[earliest_index] = charge_start + charge_duration_min
        return charge_start
