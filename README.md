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
python -m study_planner.cli figures
```

Without any setup, `demo` writes `.ics` calendars to `output/` that import into any
calendar. To write to your real Google Calendar instead, follow
[docs/GOOGLE_SETUP.md](docs/GOOGLE_SETUP.md) (one-time, about 20 minutes), then run
`python -m study_planner.cli demo --scenario struggling --google`. `credentials.json`
and `token.json` stay in the repo root and are git-ignored.

The `figures` command regenerates the three report PNGs in `docs/figures/` from
the student CSV (run `simulate` first if it is missing). Use `figures --out PATH`
to save elsewhere. The charts include all 13 network nodes, all nine learned CPTs,
and all four action utilities for each of the five demo students. No Google login
is needed.

## Web dashboard

From the repository root (the folder containing `requirements.txt`), run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m study_planner.cli serve
```

Open http://127.0.0.1:8000 in your browser. Keep the terminal running; Ctrl+C
stops the server. If port 8000 is busy, use `serve --port 8018` and open
http://127.0.0.1:8018 instead.

Choose one of the five student profiles or enter custom difficulty, quiz, sleep,
and exam-date evidence, then click **Calculate today's plan**. The dashboard
shows mastery/stress/pass probabilities, all four action utilities, the chosen
session, and a seven-day calendar containing today's preview. Expand **Inside
the model** to inspect the network and conditional probability tables. The model
selector switches between learned and hand-crafted probabilities.

This preview uses an isolated in-memory calendar; it does not read OAuth tokens
or modify Google Calendar. Future days are not forecast. Dates and times use
America/Vancouver. Learned models are cached until server restart: restart after
changing the student CSV. If the CSV is missing, run `simulate` or select the
hand-crafted model. Chart.js loads from a CDN; the numeric utility table remains
available without it. See [dashboard design notes](docs/DASHBOARD.md) for design
references and scope.
