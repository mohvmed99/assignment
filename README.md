# Bus Charging Scheduler

Python + Streamlit take-home assignment: schedule electric bus charging along the Bengaluru ↔ Kochi corridor.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the URL shown in the terminal (usually http://localhost:8501).

## Change a weight

Edit the `weights` block in any scenario file under `data/scenarios/`:

```yaml
weights:
  individual: 1.0
  operator: 2.0
  overall: 1.0
```

Reload the app and pick the scenario again. No code changes needed.

## Add a new scenario

Create `data/scenarios/scenario_06.yaml` following the same shape as the existing files. It will appear automatically in the dropdown.

## Add a new rule

See [ARCHITECTURE.md](ARCHITECTURE.md) for how soft rules plug into `src/metrics.py` without rewriting the simulator.

## Project layout

```
app.py                  Streamlit entry point
src/                    Scheduler engine
data/scenarios/         Five encoded scenarios
schemas/                JSON Schema for input/output
ARCHITECTURE.md         Design decisions and extensibility notes
```

## Deploy (Streamlit Community Cloud)

1. Push this repo to public GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io).
3. New app → select repo → main file: `app.py`.
4. Deploy. Streamlit installs from `requirements.txt` automatically.

## Assumptions

Documented in [ARCHITECTURE.md](ARCHITECTURE.md).
