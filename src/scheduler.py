from __future__ import annotations

from src.models import Schedule, Scenario
from src.planner import Planner


def run_scheduler(scenario: Scenario) -> Schedule:
    return Planner(scenario).build_schedule()
