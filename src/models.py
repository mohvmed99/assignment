from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SimulationConfig:
    speed_kmh: float
    battery_range_km: float
    charge_duration_min: int
    charge_to_full: bool = True


@dataclass(frozen=True)
class Weights:
    individual: float
    operator: float
    overall: float


@dataclass(frozen=True)
class BusInput:
    id: str
    operator: str
    origin: str
    destination: str
    departure: str
    priority: int = 0


@dataclass(frozen=True)
class RouteConfig:
    id: str
    stops: list[str]
    segment_distances_km: list[float]
    scheduling_stations: list[str]
    stations: dict[str, dict[str, Any]] = field(default_factory=dict)

    def charger_count(self, station_id: str) -> int:
        station = self.stations.get(station_id, {})
        return int(station.get("chargers", 1))


@dataclass
class Scenario:
    schema_version: str
    id: str
    name: str
    description: str
    simulation: SimulationConfig
    route: RouteConfig
    operators: list[str]
    weights: Weights
    buses: list[BusInput]


@dataclass(frozen=True)
class ChargingPlan:
    stations: tuple[str, ...]

    @property
    def stop_count(self) -> int:
        return len(self.stations)


@dataclass
class TimelineEvent:
    type: str
    location: str
    time: int
    duration_min: int | None = None
    wait_min: int | None = None


@dataclass
class StationChargeRecord:
    bus_id: str
    arrival: int
    charge_start: int
    charge_end: int
    wait_min: int


@dataclass
class BusSchedule:
    id: str
    operator: str
    origin: str
    destination: str
    departure: int
    arrival: int
    charging_stations: list[str]
    total_wait_min: int
    events: list[TimelineEvent]


@dataclass
class ScheduleMetrics:
    individual: float
    operator: float
    overall: float
    weighted_total: float


@dataclass
class Schedule:
    scenario_id: str
    buses: list[BusSchedule]
    stations: dict[str, list[StationChargeRecord]]
    metrics: ScheduleMetrics

    def to_dict(self) -> dict[str, Any]:
        from src.time_utils import format_time

        return {
            "scenario_id": self.scenario_id,
            "buses": [
                {
                    "id": bus.id,
                    "operator": bus.operator,
                    "origin": bus.origin,
                    "destination": bus.destination,
                    "departure": format_time(bus.departure),
                    "arrival": format_time(bus.arrival),
                    "charging_stations": bus.charging_stations,
                    "total_wait_min": bus.total_wait_min,
                    "events": [
                        {
                            "type": event.type,
                            "location": event.location,
                            "time": format_time(event.time),
                            **(
                                {"duration_min": event.duration_min}
                                if event.duration_min is not None
                                else {}
                            ),
                            **({"wait_min": event.wait_min} if event.wait_min is not None else {}),
                        }
                        for event in bus.events
                    ],
                }
                for bus in self.buses
            ],
            "stations": {
                station_id: {
                    "charge_order": [
                        {
                            "bus_id": record.bus_id,
                            "arrival": format_time(record.arrival),
                            "charge_start": format_time(record.charge_start),
                            "charge_end": format_time(record.charge_end),
                            "wait_min": record.wait_min,
                        }
                        for record in records
                    ]
                }
                for station_id, records in self.stations.items()
            },
            "metrics": {
                "individual": self.metrics.individual,
                "operator": self.metrics.operator,
                "overall": self.metrics.overall,
                "weighted_total": self.metrics.weighted_total,
            },
        }
