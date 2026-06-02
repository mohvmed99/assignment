# Architecture

## Overview

The scheduler is a small Python engine with a Streamlit front end. Each scenario YAML file fully describes one world (route, buses, weights). The engine:

1. Builds a route graph and enumerates valid charging plans per bus.
2. Assigns a plan to each bus using greedy search plus local refinement.
3. Simulates charger queues with a discrete-event model (multi-charger aware).
4. Scores the result with three tunable weighted metrics.

```
data/scenarios/*.yaml
        │
        ▼
 scenario_loader ──► Scenario
        │
        ▼
    RouteGraph ──► valid ChargingPlan options per bus
        │
        ▼
     Planner ──► plan assignment (greedy + local search)
        │
        ▼
    Simulator ──► Schedule (timelines + station queues)
        │
        ▼
     metrics ──► weighted cost
        │
        ▼
      app.py (Streamlit UI)
```

## Framework choice

**Plan assignment + discrete-event simulation** fits this problem because:

- Hard constraints (range, route order, charger capacity) are enforced by plan enumeration and simulation.
- Soft goals (individual / operator / overall waits) are handled in a separate scoring layer.
- The same simulator works for any scenario loaded from data.

Alternative considered: full mixed-integer programming. Rejected for this assignment because the plan search space is small (≤7 plans per bus) and a lightweight heuristic is easier to extend live in an interview.

## Data structure design

### Input (`Scenario`)

| Section | Purpose |
|---------|---------|
| `simulation` | Physical constants (speed, range, charge duration) |
| `route` | Stops, segment distances, scheduling stations, charger counts |
| `weights` | Tunable objective weights in one place |
| `buses` | Per-bus operator, origin, destination, departure |

Direction is expressed as `origin` / `destination` rather than an enum so new routes do not require code changes.

### Output (`Schedule`)

| Section | Purpose |
|---------|---------|
| `buses[]` | Per-bus timeline events, charging stations, total wait, arrival |
| `stations{}` | Per-station ordered charge records |
| `metrics` | Raw and weighted cost breakdown |

## Scoring model

All costs are **lower is better**.

- **Individual:** `max(bus_wait) + 0.25 × mean(bus_wait)` — penalizes worst-off bus.
- **Operator:** For each operator, `max(wait) + 0.5 × spread(wait)`; averaged across operators.
- **Overall:** Sum of all bus wait times.

```
weighted_total = w_ind × individual + w_op × operator + w_overall × overall
```

Weights are read from the scenario file only (`weights` block).

## Anticipated future changes

| Change | How the design handles it |
|--------|---------------------------|
| New scenario | Add `scenario_XX.yaml` — no code change |
| Change a weight | Edit `weights` in scenario YAML |
| New operator | Add to `operators` and bus records |
| New station on route | Extend `stops`, `segment_distances_km`, `scheduling_stations` |
| More chargers at a station | Set `stations.X.chargers: N` — simulator already uses N slots |
| New route | New `route` block with different stops/distances |
| Priority buses | Optional `priority` field on buses; add a queue rule class |
| Time-of-day electricity cost | Add `pricing` block to scenario; add cost term in `metrics.py` |
| Multiple routes sharing stations | Split into route configs referenced by scenario (future `routes:` map) |
| Driver shift limits | Add `rules:` list with shift constraint class |

## Change a weight

Edit the scenario file:

```yaml
weights:
  individual: 1.0
  operator: 2.0   # ← Scenario 4 uses this
  overall: 1.0
```

No code change required. Re-run the app to see a different schedule.

## Add a new rule

Example: deprioritize long waits above 120 minutes with a penalty.

1. Add a rule module, e.g. `src/rules/max_wait_penalty.py`:

```python
def penalty(bus_waits: list[int], threshold: int = 120) -> float:
    return sum(max(0, wait - threshold) for wait in bus_waits)
```

2. Register it in `src/metrics.py`:

```python
overall = sum(waits) + penalty(waits)
```

Hard constraints (must charge, no backtracking) stay in `route.py` and `simulator.py`. Soft rules stay in `metrics.py`.

## Assumptions

1. Travel speed is constant at **60 km/h** (1 km = 1 minute).
2. Time is tracked in integer minutes; trips may cross midnight.
3. Buses leave origin fully charged; endpoints are not scheduling stations.
4. Charging is always to full in exactly 25 minutes.
5. Queue discipline is **FCFS** by arrival time at a station.
6. Planner prefers fewer charge stops when costs tie (sorted plan enumeration).
7. Local search runs 3 passes over plan swaps; sufficient for 20-bus scenarios.

## Module map

| Module | Responsibility |
|--------|----------------|
| `scenario_loader.py` | YAML → `Scenario` |
| `route.py` | Distances, valid plan enumeration |
| `planner.py` | Plan assignment optimization |
| `simulator.py` | Charger queues and timelines |
| `metrics.py` | Weighted objective |
| `scheduler.py` | Single entry point |
| `app.py` | Streamlit UI |
