from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from src.scheduler import run_scheduler
from src.scenario_loader import list_scenarios, load_scenario
from src.time_utils import format_time

SCENARIO_DIR = Path(__file__).parent / "data" / "scenarios"


@st.cache_data(show_spinner=False)
def load_all_scenarios() -> list[dict]:
    scenarios = list_scenarios(SCENARIO_DIR)
    return [
        {
            "id": scenario.id,
            "name": scenario.name,
            "description": scenario.description,
            "path": str(SCENARIO_DIR / f"{scenario.id}.yaml"),
        }
        for scenario in scenarios
    ]


@st.cache_data(show_spinner="Running scheduler...")
def run_for_scenario(scenario_path: str):
    scenario = load_scenario(scenario_path)
    schedule = run_scheduler(scenario)
    return scenario, schedule


def scenario_input_table(scenario) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Bus ID": bus.id,
                "Operator": bus.operator,
                "Origin": bus.origin,
                "Destination": bus.destination,
                "Departure": bus.departure,
            }
            for bus in scenario.buses
        ]
    )


def bus_timetable(schedule) -> pd.DataFrame:
    rows = []
    for bus in schedule.buses:
        for event in bus.events:
            rows.append(
                {
                    "Bus ID": bus.id,
                    "Operator": bus.operator,
                    "Event": event.type,
                    "Location": event.location,
                    "Time": format_time(event.time),
                    "Wait (min)": event.wait_min,
                    "Duration (min)": event.duration_min,
                }
            )
        rows.append(
            {
                "Bus ID": bus.id,
                "Operator": bus.operator,
                "Event": "summary",
                "Location": "→".join([bus.origin, *bus.charging_stations, bus.destination]),
                "Time": format_time(bus.arrival),
                "Wait (min)": bus.total_wait_min,
                "Duration (min)": None,
            }
        )
    return pd.DataFrame(rows)


def station_view(schedule, station_id: str) -> pd.DataFrame:
    records = schedule.stations.get(station_id, [])
    return pd.DataFrame(
        [
            {
                "Order": index + 1,
                "Bus ID": record.bus_id,
                "Arrival": format_time(record.arrival),
                "Charge Start": format_time(record.charge_start),
                "Charge End": format_time(record.charge_end),
                "Wait (min)": record.wait_min,
            }
            for index, record in enumerate(records)
        ]
    )


def main() -> None:
    st.set_page_config(page_title="Bus Charging Scheduler", layout="wide")
    st.title("Bus Charging Scheduler")
    st.caption("Electric bus charging plans for the Bengaluru ↔ Kochi corridor")

    scenarios = load_all_scenarios()
    if not scenarios:
        st.error("No scenarios found in data/scenarios.")
        return

    labels = {scenario["id"]: f"{scenario['name']} ({scenario['id']})" for scenario in scenarios}
    selected_id = st.selectbox(
        "Scenario",
        options=[scenario["id"] for scenario in scenarios],
        format_func=lambda scenario_id: labels[scenario_id],
    )

    selected = next(item for item in scenarios if item["id"] == selected_id)
    scenario, schedule = run_for_scenario(selected["path"])

    st.subheader("Scenario input")
    st.write(selected["description"])
    with st.expander("Raw scenario data", expanded=False):
        st.code(yaml.safe_load(Path(selected["path"]).read_text()), language="yaml")
    st.dataframe(scenario_input_table(scenario), width="stretch", hide_index=True)

    metric_cols = st.columns(4)
    metric_cols[0].metric("Individual cost", f"{schedule.metrics.individual:.1f}")
    metric_cols[1].metric("Operator cost", f"{schedule.metrics.operator:.1f}")
    metric_cols[2].metric("Overall cost", f"{schedule.metrics.overall:.1f}")
    metric_cols[3].metric("Weighted total", f"{schedule.metrics.weighted_total:.1f}")

    st.subheader("Per-bus timetable")
    st.dataframe(bus_timetable(schedule), width="stretch", hide_index=True)

    st.subheader("Per-station charge order")
    station_tabs = st.tabs(list(scenario.route.scheduling_stations))
    for tab, station_id in zip(station_tabs, scenario.route.scheduling_stations):
        with tab:
            table = station_view(schedule, station_id)
            if table.empty:
                st.info(f"No charging activity at station {station_id}.")
            else:
                st.dataframe(table, width="stretch", hide_index=True)


if __name__ == "__main__":
    main()
