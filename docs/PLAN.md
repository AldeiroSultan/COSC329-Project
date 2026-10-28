# 2-Week Plan, Branches & Task Split

Team: **Sultan (~70%)**, **John (~30%)**
Window: **Wed Oct 28 → Tue Nov 10, 2026** (Nov 10 = buffer / submission day).

## Git flow

```
main      ← only receives merges from staging at milestones (graded version)
staging   ← integration branch; every PR targets staging
MF-0000N  ← main features   (branched from staging)
TI-0000N  ← tasks / support (branched from staging)
```

1. Tell Claude: *"Please do MF-00003"*. Claude puts you on that branch (merging
   staging in), makes the changes and leaves them **uncommitted** in Source Control.
2. Claude replies with the commit message and PR message.
3. You paste the commit message in VS Code, commit, push, and open the PR into
   **staging** with the PR message.
4. The other person skims the PR and merges.
5. Milestones: staging → main on **Nov 3** (end of week 1) and **Nov 9** (final).

---

## Branch specs

Each spec is what "done" means. Claude reads this section when you ask it to do a branch.

### MF-00001 — Bayesian network structure + hand-crafted CPTs · **Sultan** · Oct 28–29
* Implement `study_planner/network.py::build_handcrafted_model()` with all 13
  nodes and CPTs exactly as in `docs/MODEL.md` §1–2a, using pgmpy.
* `model.check_model()` passes.
* Fill `docs/REPORT.md` §2 (structure + CPT explanations).
* Un-skip and pass `tests/test_network.py`.
* Depends on: TI-00001.

### MF-00002 — Data simulation → CSV · **Sultan** · Oct 30–31
* Implement `study_planner/simulate_data.py` per `docs/DATA.md`.
* `python -m study_planner.cli simulate` writes `data/processed/students.csv` (5,000 rows, seed 329).
* Print/log parent-configuration counts (data sufficiency evidence).
* Fill `docs/REPORT.md` §3 (data source / simulation).
* Un-skip and pass `tests/test_simulate.py`.
* Depends on: MF-00001.

### MF-00003 — CPT learning with Laplace smoothing · **Sultan** · Nov 1–2
* Implement `study_planner/learning.py`: manual counting + Laplace (α=1) for the
  learned CPTs listed in `docs/MODEL.md` §2b; return pgmpy `TabularCPD`s.
* `build_learned_model(csv_path)` = hand-crafted structure + learned CPTs.
* Save learned CPTs to `data/processed/learned_cpts.json`.
* Cross-check one CPT against pgmpy `BayesianEstimator(prior_type="K2")` (K2 = add-1).
* `python -m study_planner.cli learn` works.
* Fill `docs/REPORT.md` §4 (learning + hand-crafted vs learned comparison table).
* Un-skip and pass `tests/test_learning.py`.
* Depends on: MF-00002.

### MF-00004 — Inference + decision engine (utility, expected utility) · **Sultan** · Nov 4–5
* Implement `study_planner/inference.py` (VariableElimination queries from `docs/MODEL.md` §3).
* Implement `study_planner/decision.py` (action effects §4, utility §5, EU, argmax).
* Re-check the scenario table in `docs/MODEL.md` §6 with the **learned** model;
  re-tune `config.py` if needed and document why.
* Fill `docs/REPORT.md` §5–6 (inference task, actions, utility, EU tables).
* Un-skip and pass `tests/test_inference.py`, `tests/test_decision.py`.
* Depends on: MF-00003.

### MF-00005 — Calendar API integration · **Sultan** · Nov 6
* Implement `study_planner/calendar_api/`:
  * `GoogleCalendarClient` (Google Calendar API v3, OAuth desktop flow,
    `credentials.json` / `token.json` git-ignored).
  * `IcsCalendarClient` (writes `.ics` file — works offline, import into any calendar).
  * `InMemoryCalendarClient` for tests.
* Implement `study_planner/planner.py::StudyPlanner.plan_today()`: read exams →
  compute DaysLeft → decide → create/clear events. Only events tagged
  `[BayesPlanner]` may be deleted.
* Un-skip and pass `tests/test_calendar.py`, `tests/test_planner.py`.
* Depends on: MF-00004, TI-00003.

### MF-00006 — Student scenarios + demo · **Sultan** · Nov 7
* Implement `study_planner/scenarios.py` (≥4 students from `docs/MODEL.md` §6).
* `python -m study_planner.cli demo` prints, per scenario: evidence, query
  results, EU of every action, chosen action; writes one `.ics` per scenario to
  `output/` (and to Google Calendar with `--google`).
* Show a **14-day run** for the struggling vs advanced student (days count down,
  quizzes improve after study days) to prove the plan adapts over time.
* Fill `docs/REPORT.md` §7 (results).
* Depends on: MF-00005.

### MF-00007 — Web dashboard · **John** · Nov 4–8
* `study_planner/api.py` (FastAPI): `GET /api/scenarios`, `POST /api/plan`,
  `GET /api/network` — serves `web/`.
* `web/index.html`, `web/app.js`, `web/styles.css`: form for difficulties /
  quizzes / sleep / exam date → shows posterior bars, EU bar chart, chosen action
  and a week calendar view of the scheduled sessions.
* Build against mock JSON (`web/mock/plan.json`) first, switch to the real API
  once MF-00004 is on staging.
* Depends on: TI-00001 (mock), MF-00004 (real data).

### TI-00001 — Environment & tooling · **John** · Oct 28
* Create venv, `pip install -r requirements.txt`, confirm `pytest` runs (all skipped).
* Confirm pgmpy imports on your Python version (see README troubleshooting).
* Add a GitHub Actions workflow `.github/workflows/tests.yml` running pytest on PRs to staging/main.

### TI-00002 — Unit tests · **John** · Oct 30–Nov 2
* Write extra tests as MF branches land: CPT rows sum to 1, Laplace never gives
  0 probability, learned ≈ hand-crafted within tolerance, CSV schema check.

### TI-00003 — Google Cloud / OAuth setup · **John** · Oct 29
* Create a Google Cloud project, enable Calendar API, create an OAuth "Desktop
  app" client, add both of you as test users, download `credentials.json`
  (never commit it). Write the steps into `docs/GOOGLE_SETUP.md`.

### TI-00004 — Visualizations · **John** · Nov 1–3
* `study_planner/viz.py`: network diagram (networkx/matplotlib), hand-crafted vs
  learned CPT bar charts, EU-per-action chart per scenario → `docs/figures/`.

### TI-00005 — Final report & demo recording · **Sultan + John** · Nov 8–9
* Complete `docs/REPORT.md` (John assembles + figures, Sultan writes model
  sections), record a short demo (CLI + dashboard + calendar), staging → main.

---

## Calendar

| Day | Date | Sultan | John |
|---|---|---|---|
| 1 | Wed Oct 28 | Read MODEL.md, start **MF-00001** | **TI-00001** env + CI |
| 2 | Thu Oct 29 | Finish **MF-00001** | **TI-00003** Google OAuth |
| 3 | Fri Oct 30 | **MF-00002** simulation | **TI-00002** tests (network) |
| 4 | Sat Oct 31 | Finish **MF-00002** | — |
| 5 | Sun Nov 1 | **MF-00003** learning | **TI-00004** viz (network diagram) |
| 6 | Mon Nov 2 | Finish **MF-00003** | **TI-00002** tests (sim + learning) |
| 7 | Tue Nov 3 | Buffer / review · **staging → main (M1)** | **TI-00004** CPT charts |
| 8 | Wed Nov 4 | **MF-00004** inference | **MF-00007** dashboard on mock data |
| 9 | Thu Nov 5 | Finish **MF-00004** + tuning | **MF-00007** |
| 10 | Fri Nov 6 | **MF-00005** calendar API | **MF-00007** connect to API |
| 11 | Sat Nov 7 | **MF-00006** scenarios + 14-day demo | **TI-00004** EU charts |
| 12 | Sun Nov 8 | **TI-00005** report model sections | **MF-00007** polish, **TI-00005** assembly |
| 13 | Mon Nov 9 | Full run-through · **staging → main (final)** | Record demo |
| 14 | Tue Nov 10 | Buffer / submit | Buffer / submit |

Rough effort: Sultan ≈ MF-00001…MF-00006 + half of TI-00005 (~70%);
John ≈ MF-00007 + TI-00001…TI-00004 + half of TI-00005 (~30%).
