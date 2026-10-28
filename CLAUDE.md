# CLAUDE.md — Bayesian Study Planner (COSC 329, 2-person project)

Team: **Sultan** and **John**. Python 3.11+ project: a Bayesian network (pgmpy)
decides today's study action and writes it to a calendar (Google Calendar API / .ics).

## Read these first
* `docs/MODEL.md` — network, CPTs, inference task, actions, utility. **Source of truth.**
* `docs/DATA.md` — simulated data + Laplace learning.
* `docs/PLAN.md` — branch specs (definition of done), owners, dates.
* `study_planner/config.py` — every number from MODEL.md lives here. Never hard-code
  states or numbers elsewhere.

## "Please do MF-0000N" — the workflow

When a teammate says *"Please do MF-00003"* / *"Please do branch MF-00003"* (or any
`MF-0000N` / `TI-0000N`), Claude **only makes file changes**. The teammate commits,
pushes and opens the PR from VS Code / GitHub.

1. **Find the spec** for that branch in `docs/PLAN.md` → "Branch specs". If it
   isn't there, stop and ask.
2. **Make sure we're on the right branch.** Run `git status --short --branch`.
   * If the working tree has uncommitted changes from another branch, stop and
     tell the user (don't stash or discard their work).
   * If not on `<BRANCH>`, switch to it and bring it up to date:
     ```
     git fetch origin
     git checkout <BRANCH>            # or: git checkout -b <BRANCH> origin/staging if it doesn't exist
     git merge origin/staging         # falls back to local staging if no remote branch yet
     ```
     Tell the user which branch they were on and that you moved them.
   * If the merge conflicts, stop and explain the conflict instead of guessing.
   * Check the spec's "Depends on" branches are already in staging; if not, warn the user.
3. **Implement** everything in the spec. Replace `raise NotImplementedError` stubs,
   keep the existing function names/signatures (other branches rely on them),
   remove `pytest.mark.skip` from the tests the spec names and make them pass.
4. **Verify**: `.venv\Scripts\python -m pytest -q` must pass. Run the CLI command the spec
   mentions and include its output summary in the PR message.
5. **Docs**: fill the `docs/REPORT.md` section the spec names; if you changed any
   number in `config.py`, update `docs/MODEL.md` too.
6. **Leave everything uncommitted** so it shows up in VS Code's Source Control
   panel. **Never** `git add`, `git commit`, `git push`, open PRs, or merge.
7. **Reply in chat** with the commit message and the PR message (template below)
   in separate code blocks, ready to copy-paste. Also save them to
   `.pr-drafts/<BRANCH>.md` (git-ignored) as a backup.

## Commit / PR message template

````markdown
## Commit message
```
[<BRANCH>] <type>(<scope>): <short imperative summary, ≤ 72 chars>

- <what changed, bullet per meaningful change>
- <why, if not obvious>
```

## PR title
[<BRANCH>] <Human readable title>

## PR description
**Base:** `staging` ← **Compare:** `<BRANCH>`

### Summary
<2–4 sentences: what this branch adds and how it fits the project>

### Changes
- `path/file.py` — <what>

### How to test
```bash
python -m pytest -q
<CLI command from the spec>
```

### Results
<test summary line + key output, e.g. EU table / row counts>

### Checklist
- [ ] Tests pass locally
- [ ] docs/REPORT.md section updated
- [ ] docs/MODEL.md matches config.py
````

`<type>` is one of `feat`, `fix`, `test`, `docs`, `chore`, `refactor`.

## Conventions
* Package: `study_planner/`. Entry point: `python -m study_planner.cli <simulate|learn|demo|serve>`.
* Node and state names come from `config.py` (`NODE_*`, `*_STATES`). State order
  in every CPT = the order in config.
* pgmpy: use `DiscreteBayesianNetwork` (falls back to `BayesianNetwork` on older
  pgmpy — see `study_planner/network.py`), `TabularCPD`, `VariableElimination`.
* Docstrings on public functions; type hints everywhere; no notebooks as the only
  place logic lives.
* Never commit secrets: `credentials.json`, `token.json`, `.env` are git-ignored.
* Calendar safety: the planner may only delete events whose summary starts with
  `config.EVENT_TAG` (`[BayesPlanner]`).
* Frontend (`web/`) is plain HTML/CSS/JS, no build step; charts via Chart.js CDN.

## Commands
```bash
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt
python -m pytest -q
python -m study_planner.cli simulate                 # -> data/processed/students.csv
python -m study_planner.cli learn                    # -> data/processed/learned_cpts.json
python -m study_planner.cli demo [--google]          # scenarios -> output/*.ics
python -m study_planner.cli serve                    # dashboard at http://127.0.0.1:8000
```
