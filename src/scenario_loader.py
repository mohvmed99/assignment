from __future__ import annotations

from pathlib import Path

import yaml

from src.models import (
    BusInput,
    RouteConfig,
    Scenario,
    SimulationConfig,
    Weights,
)


def load_scenario(path: Path | str) -> Scenario:
    path = Path(path)
    raw = yaml.safe_load(path.read_text())

    route = raw["route"]
    simulation = raw["simulation"]
    weights = raw["weights"]

    return Scenario(
        schema_version=raw["schema_version"],
        id=raw["id"],
        name=raw["name"],
        description=raw.get("description", ""),
        simulation=SimulationConfig(
            speed_kmh=float(simulation["speed_kmh"]),
            battery_range_km=float(simulation["battery_range_km"]),
            charge_duration_min=int(simulation["charge_duration_min"]),
            charge_to_full=bool(simulation.get("charge_to_full", True)),
        ),
        route=RouteConfig(
            id=route["id"],
            stops=list(route["stops"]),
            segment_distances_km=[float(value) for value in route["segment_distances_km"]],
            scheduling_stations=list(route["scheduling_stations"]),
            stations=dict(route.get("stations", {})),
        ),
        operators=list(raw.get("operators", [])),
        weights=Weights(
            individual=float(weights["individual"]),
            operator=float(weights["operator"]),
            overall=float(weights["overall"]),
        ),
        buses=[
            BusInput(
                id=bus["id"],
                operator=bus["operator"],
                origin=bus["origin"],
                destination=bus["destination"],
                departure=bus["departure"],
                priority=int(bus.get("priority", 0)),
            )
            for bus in raw["buses"]
        ],
    )


def list_scenarios(directory: Path | str) -> list[Scenario]:
    directory = Path(directory)
    scenarios = []
    for path in sorted(directory.glob("scenario_*.yaml")):
        scenarios.append(load_scenario(path))
    return scenarios
