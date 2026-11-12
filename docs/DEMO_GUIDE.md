# COSC 329 demo guide

Suggested length: 4-5 minutes. This is a recording outline, not a claim that a recording has been completed.

## Before recording

- Open the repository root containing `requirements.txt` in VS Code.
- Activate `.venv`, or use `.\.venv\Scripts\python.exe` instead of `python` below.
- Run `python -m pytest -q`. The current result is 144 passing tests.
- Run `python -m study_planner.cli serve --port 8018`, then open http://127.0.0.1:8018 in a browser. Leave this terminal running.
- Keep a second terminal for the CLI demo. Do not display credential or token files.
- Use the offline `.ics` demonstration unless you intend to change your live calendar. The Google commands below replace today's planner-tagged sessions.

## 0:00-0:35 - Explain the problem

Say something like:

> The main aim of our project is to help a student decide how much studying makes sense for today. We use difficulty, quizzes, sleep, and days left before an exam. The Bayesian network estimates mastery, stress, and the chance of passing, then we compare four study actions using expected utility.

Show the network figure in `docs/figures/network.png`. Point out the mastery-to-quiz and stress-to-sleep arrows. Explain that observations update the hidden variables.

## 0:35-1:15 - Show the data and learning

Show `docs/figures/cpt_comparison.png` and explain:

> We generated 5,000 student records with a fixed seed. We learn nine CPTs using add-one smoothing. Most values stay close to the starting model, but stress with 4-10 days left changes from about 45% to 57%. That comes from the simulated data. It is not a result measured from real students.

Mention that the learned tables agree with pgmpy's K2 estimator and that the tests pass.

## 1:15-2:25 - Compare student profiles

In the dashboard, select each profile and click **Calculate today's plan**:

1. **Struggling:** intense, 5 hours. Show all four utility values; intense is 23.4 and light is 22.0 with the learned model.
2. **Advanced:** rest, 0 hours. Point out that no study session is scheduled.
3. **One weak spot:** focused, 2.5 hours on C3. Show its low mastery compared with C1 and C2.
4. **Burnt out:** light review despite the approaching exam, with a high stress estimate.

Say:

> From here, we can see that the same system makes different decisions when the evidence changes. It also shows the other action scores, because some recommendations win by a small margin.

Switch to the hand-crafted model and recalculate one profile. Expand the network inspector and show one CPT. Explain that the calendar is a preview for today, not a forecast of the whole week.

## 2:25-3:15 - Run the offline demo

In the second terminal:

```powershell
python -m study_planner.cli demo
```

Show the five-scenario summary, followed by the two-week struggling-student table. The summary has all four actions. The two-week struggling case starts with 14 days left and selects light review each day, totaling 14 hours; quiz evidence becomes high on day 4. The advanced case rests throughout.

Explain that simulated true mastery changes according to the programmed boost rule. The simulation illustrates behavior; it does not validate the study effects.

## 3:15-4:00 - Show the calendar integration

For an offline recording, show `docs/figures/google_calendar_live.png` and explain that it records the November 12 live test. Sultan subsequently confirmed that running the advanced scenario removed the block. Do not present this saved image as a newly performed live test.

For a new live demonstration, after OAuth setup, deliberately run:

```powershell
python -m study_planner.cli demo --scenario struggling --google
```

Open the created event in Google Calendar and show its duration and explanation. Then run:

```powershell
python -m study_planner.cli demo --scenario advanced --google
```

Refresh Calendar and show that the planner block is gone. Both commands affect today's `[BayesPlanner]` events. Untagged events are protected by the deletion guard.

## 4:00-4:40 - Explain the limits

> The main limitation is that the data and study effects are simulated. The action boosts and utility values are assumptions we chose, and some action scores are close. One improvement would be to test with real student records and check how recommendations change when we vary those assumptions. The scheduler also needs a better response when the day is full, because it currently falls back to 10:00.

## Submission steps still requiring a person

- Read the report and check that it reflects what you want to explain. Confirm names and any course-specific formatting, length, references, or AI-use requirements against the actual assignment instructions.
- Record the demo; watch it once to check that text is readable and the sound is clear.
- Commit and open the TI-00005 PR into `staging`, then wait for CI and review before merging.
- Open the final `staging` to `main` PR and submit the report/repository/demo in the required course location.

The actual course handout was not present in the repository when this guide was prepared. The report follows the sections and branch scope in `docs/PLAN.md` and `docs/MODEL.md`; exact submission rules still need checking.
