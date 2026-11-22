# Bayesian Study Planner

COSC 329 project (2-person option) — Sultan Aldeiro & John Kwon.
Repository: https://github.com/AldeiroSultan/COSC329-Project

A Bayesian network estimates a student's mastery of 3 course concepts, their
stress and their chance of passing; a utility function trading exam success
against stress picks today's action (intense 5h block / focused 2.5h session /
light 1h review / rest day) and writes it to Google Calendar or an `.ics` file.

* Report: [docs/REPORT.md](docs/REPORT.md) (PDF: [docs/Bayesian_Study_Planner_Report.pdf](docs/Bayesian_Study_Planner_Report.pdf))
* Design: [docs/MODEL.md](docs/MODEL.md)
* Data: [docs/DATA.md](docs/DATA.md)
* Plan & branches: [docs/PLAN.md](docs/PLAN.md)
* Demo recording guide: [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md)

## Project status

Every feature of the 2-person option is implemented, demonstrated and tested.
**152 automated tests pass** and the `Tests` workflow is green on `main`.

| Feature | Status | Where | Tests |
|---|---|---|---|
| Bayesian network, 13 nodes, hand-crafted CPTs | Done | `network.py`, `config.py`, [MODEL.md](docs/MODEL.md) | `test_network.py` (5) |
| Simulated student data -> CSV (5,000 rows, seed 329) | Done | `simulate_data.py`, `data/processed/students.csv`, [DATA.md](docs/DATA.md) | `test_simulate.py` (10) |
| Learn 9 CPTs (36 parameters) with Laplace smoothing | Done | `learning.py`, `data/processed/learned_cpts.json` | `test_learning.py` (24) |
| Inference task (exact variable elimination) | Done | `inference.py` | `test_inference.py` (9) |
| 4 actions, utility function, expected utility, best action | Done | `decision.py`, `config.py` | `test_decision.py` (29) |
| Calendar API: Google Calendar, `.ics`, in-memory | Done (live Google run verified once, Nov 12) | `calendar_api/`, `planner.py`, [GOOGLE_SETUP.md](docs/GOOGLE_SETUP.md) | `test_calendar.py` (12), `test_planner.py` (13) |
| Student scenarios and 14-day adaptation demo | Done | `scenarios.py`, `demo.py` | `test_scenarios.py` (16) |
| Sensitivity analysis of the decisions | Done | `sensitivity.py` | `test_sensitivity.py` (8) |
| Web dashboard (extra) | Done | `api.py`, `web/`, [DASHBOARD.md](docs/DASHBOARD.md) | `test_api.py` (25) |
| Report figures | Done | `viz.py`, `docs/figures/` | `test_viz.py` (1) |

**Bugs.** No failing tests and no open bugs are known. The items below are known
limitations, not defects:

* **Simulated data.** The 5,000 students are generated, not real. The learned CPTs recover
  the simulation, so they say nothing about the accuracy for real students.
* **Hand-set decision assumptions.** Action boosts, urgency factors and utilities are our
  choices. Run `python -m study_planner.cli sensitivity`: a 25% change that makes
  studying less valuable changes 4 of the 5 demo decisions (the advanced student never changes).
  The best and second-best action are only 0.3 to 1.7 utility points apart.
* **Full day.** If no free slot exists the scheduler falls back to 10:00 and may overlap an event.
* **One-day model.** The network has no memory of past sessions; improvement reaches it only
  through new quiz results.
* **Dashboard.** Previews today only and never writes to Google Calendar. The learned model is
  cached until the server restarts. Chart.js loads from a CDN (the numeric table works without it).
* **Google Calendar.** Verified live once (Sultan's account, Nov 12); the automated tests use a
  fake service. While the OAuth app is in Testing mode, sign-ins expire after about 7 days
  (delete `token.json`). `demo --google` requires `--scenario NAME`.
* **Warning.** pgmpy prints a `FutureWarning` about `StructureScore` when imported. It comes from the
  library and is harmless.

## Tech stack

| Part | Tool |
|---|---|
| Language | Python 3.11+ (tested on 3.14) |
| Bayes net, inference | [pgmpy](https://pgmpy.org) (`TabularCPD`, `VariableElimination`) |
| Data simulation / CSV | numpy, pandas |
| CPT learning | own Laplace-smoothed counting (checked against pgmpy's K2 estimator) |
| Calendar | Google Calendar API v3 (`google-api-python-client`), `.ics` fallback (`icalendar`) |
| Dashboard | FastAPI + plain HTML/CSS/JS + Chart.js |
| Figures | matplotlib, networkx |
| Tests | pytest |

## Setup

Run these from the repository root (the folder containing `requirements.txt`).
Tested on Windows with Python 3.14 and, in CI, on Ubuntu with Python 3.14.

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest -q
```

If PowerShell blocks the activation script, skip it and call the interpreter directly,
for example `.\.venv\Scripts\python.exe -m pytest -q`.

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
```

If pgmpy fails to install on your Python version, use Python 3.12 instead
(`py -3.12 -m venv .venv` on Windows, `python3.12 -m venv .venv` elsewhere).
Expected result: `152 passed` (plus one harmless warning).

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
Section 8 of the [report](docs/REPORT.md) lists every test file, the data each one
uses and the pass criteria.

## Usage

```bash
python -m study_planner.cli simulate
python -m study_planner.cli learn
python -m study_planner.cli demo
python -m study_planner.cli sensitivity
python -m study_planner.cli serve
python -m study_planner.cli figures
```

Without any setup, `demo` writes `.ics` calendars to `output/` that import into any
calendar. To write to your real Google Calendar instead, follow
[docs/GOOGLE_SETUP.md](docs/GOOGLE_SETUP.md) (one-time, about 20 minutes), then run
`python -m study_planner.cli demo --scenario struggling --google`. `credentials.json`
and `token.json` stay in the repo root and are git-ignored.

`sensitivity` changes one hand-set assumption at a time (time cost, stress utility,
intense-block stress, mastery boosts, urgency) and prints which of the five students'
decisions change. Add `--handcrafted` to use the hand-crafted probabilities.

To rebuild the report PDF (`docs/Bayesian_Study_Planner_Report.pdf`) from `docs/REPORT.md`, run
`pip install markdown` once, then `python scripts/build_report_pdf.py`. It needs Microsoft Edge or
Google Chrome installed, which does the PDF rendering.

The `figures` command regenerates the three report PNGs in `docs/figures/` from
the student CSV (run `simulate` first if it is missing). Use `figures --out PATH`
to save elsewhere. The charts include all 13 network nodes, all nine learned CPTs,
and all four action utilities for each of the five demo students. No Google login
is needed.

## File structure

```text
.
├── README.md, requirements.txt, pytest.ini
├── CLAUDE.md                       notes for the AI coding assistant we used (branch -> PR workflow)
├── .github/workflows/tests.yml     CI: runs the tests on every PR and push to staging / main
├── study_planner/                  the program
│   ├── config.py                   all constants: states, hand-crafted CPT values, actions, utility
│   ├── network.py                  network structure + hand-crafted CPTs          (feature: Bayes net)
│   ├── simulate_data.py            generates the 5,000-student CSV                (feature: data)
│   ├── learning.py                 Laplace-smoothed CPT learning, pgmpy K2 check  (feature: learning)
│   ├── inference.py                variable-elimination queries                   (feature: inference)
│   ├── decision.py                 actions, utility, expected utility, argmax     (feature: decision)
│   ├── sensitivity.py              one-at-a-time assumption changes               (feature: discussion)
│   ├── calendar_api/               base, google_calendar, ics_calendar, memory_calendar
│   ├── planner.py                  exam -> decision -> calendar event             (feature: calendar)
│   ├── scenarios.py, demo.py       5 student types + 14-day simulation, console demo
│   ├── api.py                      FastAPI backend for the dashboard
│   ├── viz.py                      report figures
│   └── cli.py                      entry point: simulate | learn | demo | sensitivity | serve | figures
├── scripts/build_report_pdf.py     renders docs/REPORT.md to the PDF
├── web/                            dashboard front end (index.html, app.js, styles.css)
├── data/processed/                 students.csv (5,000 rows), learned_cpts.json
├── tests/                          152 tests, one file per feature (see Project status)
├── docs/                           MODEL, DATA, PLAN, REPORT (.md and .pdf), GOOGLE_SETUP, DEMO_GUIDE,
│                                   DASHBOARD, and figures/
└── output/                         generated .ics calendars (git-ignored)
```

`data/raw/` is intentionally empty: all data is simulated. The branch plan that produced
this layout (MF-0000N main features, TI-0000N tasks) is in [docs/PLAN.md](docs/PLAN.md).

## Web dashboard

From the repository root (the folder containing `requirements.txt`), run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m study_planner.cli serve
```

On macOS / Linux use `.venv/bin/python` instead of `.\.venv\Scripts\python.exe`.
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
