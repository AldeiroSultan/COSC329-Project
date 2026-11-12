# Bayesian Study Planner

COSC 329 project (2-person option) — Sultan & John.

A Bayesian network estimates a student's mastery of 3 course concepts, their
stress and their chance of passing; a utility function trading exam success
against stress picks today's action (intense 5h block / focused 2.5h session /
light 1h review / rest day) and writes it to Google Calendar or an `.ics` file.

* Design: [docs/MODEL.md](docs/MODEL.md)
* Data: [docs/DATA.md](docs/DATA.md)
* Plan & branches: [docs/PLAN.md](docs/PLAN.md)
* Report: [docs/REPORT.md](docs/REPORT.md)

## Tech stack

| Part | Tool |
|---|---|
| Language | Python 3.11+ (tested on 3.14) |
| Bayes net, inference | [pgmpy](https://pgmpy.org) (`TabularCPD`, `VariableElimination`) |
| Data simulation / CSV | numpy, pandas |
| CPT learning | own Laplace-smoothed counting (checked against pgmpy `BayesianEstimator`) |
| Calendar | Google Calendar API v3 (`google-api-python-client`), `.ics` fallback (`icalendar`) |
| Dashboard | FastAPI + plain HTML/CSS/JS + Chart.js |
| Figures | matplotlib, networkx |
| Tests | pytest |

## Setup (Windows)

```bash
python -m venv .venv
```
```bash
.venv\Scripts\activate
```
```bash
pip install -r requirements.txt
```
```bash
python -m pytest -q
```

Tested with Python 3.14 on Windows. If pgmpy fails to install on your Python
version, install Python 3.12 and use `py -3.12 -m venv .venv` instead.

## Automated tests

The `Tests` GitHub Actions workflow runs `python -m pytest -q` on pull requests
into `staging` or `main`, and on pushes to either branch. It installs dependencies
from `requirements.txt` on Ubuntu with Python 3.14, caches pip downloads, and
checks dependency compatibility before running the suite.

After opening a PR, check **Checks → Python 3.14 tests** and wait for it to pass
before merging. Google Calendar tests use a fake service; CI needs no Google
credentials or access to a real calendar. Run the same suite locally with
`python -m pytest -q` from the repository root.

The model/data tests cover CPT normalization, nonzero Laplace probabilities,
missing parent configurations, agreement with pgmpy's K2 estimator, and learned
versus hand-crafted CPT tolerances (including the documented Stress correction).
They also validate the committed CSV's schema and fixed-seed reproducibility,
and check that the committed learned-CPT JSON matches that CSV. If you deliberately
change the simulation, regenerate both artifacts with `simulate` and `learn`.

## Usage

```bash
python -m study_planner.cli simulate
python -m study_planner.cli learn
python -m study_planner.cli demo
python -m study_planner.cli serve
```

Without any setup, `demo` writes `.ics` calendars to `output/` that import into any
calendar. To write to your real Google Calendar instead, follow
[docs/GOOGLE_SETUP.md](docs/GOOGLE_SETUP.md) (one-time, about 20 minutes), then run
`python -m study_planner.cli demo --scenario struggling --google`. `credentials.json`
and `token.json` stay in the repo root and are git-ignored.
