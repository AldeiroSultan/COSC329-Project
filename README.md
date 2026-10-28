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

## Usage

```bash
python -m study_planner.cli simulate
python -m study_planner.cli learn
python -m study_planner.cli demo
python -m study_planner.cli serve
```

Google Calendar: see `docs/GOOGLE_SETUP.md` (written in TI-00003). Put
`credentials.json` in the repo root — it is git-ignored.
