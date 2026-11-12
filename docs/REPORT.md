# Bayesian Study Planner — Project Report

**COSC 329 · 2-person option** · Sultan, John

> Each section names the branch that fills it in. Delete these notes before submitting.

## 1. Overview
_(TI-00005)_ Problem, what the system does, how to run it.

## 2. Network structure & hand-crafted CPTs

_(Diagram: `docs/figures/network.png`, added in TI-00004.)_

The network has **13 discrete nodes** and is built in `study_planner/network.py`
(`build_handcrafted_model()`) with pgmpy. The 9 core nodes model the student's
situation, and 4 extra observable nodes (practice quizzes and sleep) are things a
student can actually report. These let the system infer hidden mastery and stress
instead of guessing from difficulty alone.

| Node | States | Parents | Type |
|---|---|---|---|
| Difficulty_C1, C2, C3 | easy, medium, hard | — | Evidence (entered by the student) |
| Mastery_C1, C2, C3 | low, high | Difficulty_Ci | Hidden, queried |
| Quiz_C1, C2, C3 | low, high | Mastery_Ci | Observable |
| DaysLeft | few (≤3), some (4–10), many (>10) | — | Evidence (from the calendar) |
| Stress | low, high | DaysLeft | Hidden, queried |
| Sleep | poor, good | Stress | Observable |
| ExamSuccess | fail, pass | Mastery_C1..3, Stress | Queried (outcome) |

**Edges and their meaning.**
* Difficulty → Mastery: harder concepts are less likely to be mastered.
* Mastery → Quiz: the quiz result is caused by mastery. When we observe a quiz,
  inference runs backwards (diagnostic reasoning) to update our belief about mastery.
* DaysLeft → Stress: stress rises as the exam gets closer (last-minute cramming).
* Stress → Sleep: stressed students sleep worse, so poor sleep is evidence of stress.
* Mastery_C1..3 + Stress → ExamSuccess: knowing the material helps; stress hurts.

### Hand-crafted CPTs

| CPT | Values | Justification |
|---|---|---|
| P(Difficulty_Ci) | easy .30, medium .40, hard .30 | Uninformative-ish prior; in practice always set as evidence. |
| P(DaysLeft) | few .20, some .40, many .40 | Prior over a ~3-week planning window; always set as evidence. |
| P(Mastery=high \| Difficulty) | easy .80, medium .55, hard .25 | Most students master easy material; under a quarter master hard material without targeted study. |
| P(Quiz=high \| Mastery) | high .85, low .20 | A quiz is a good but noisy test: strong students sometimes slip (15%), weak students sometimes get lucky (20%). |
| P(Stress=high \| DaysLeft) | few .80, some .45, many .20 | Captures cramming stress growing as the exam approaches. |
| P(Sleep=poor \| Stress) | high .65, low .25 | Stress is a well-known cause of poor sleep, but sleep has other causes too (25% baseline). |
| P(ExamSuccess=pass \| Mastery_C1..3, Stress) | table below | Depends on how many of the 3 concepts are mastered (k); high stress lowers each value. |

| k concepts mastered | Stress = low | Stress = high |
|---|---|---|
| 0 | .10 | .05 |
| 1 | .35 | .25 |
| 2 | .70 | .55 |
| 3 | .95 | .85 |

Writing ExamSuccess in terms of k keeps its 16 parent configurations
(2·2·2 mastery × 2 stress) explainable with 8 numbers: the three concepts are
treated as equally important. The full 16-column CPT is generated from this table
in `_exam_cpd()`.

These hand-crafted CPTs are the starting model. In §4, 9 of them (Mastery, Quiz,
Stress, Sleep, ExamSuccess) are re-learned from simulated data, and the two
versions are compared.

## 3. Data source / simulation

**Why simulated.** We could not find a public dataset that records, for the same
student, per-concept mastery, practice-quiz results, stress, sleep and exam outcome.
So we generate **5,000 synthetic students** with a documented mathematical process
(`study_planner/simulate_data.py`, fixed seed `329`, reproducible). The result is
`data/processed/students.csv` (regenerate with `python -m study_planner.cli simulate`).

**Columns.** `student_id`, the 13 network variables (`Difficulty_C1..3`,
`Mastery_C1..3`, `Quiz_C1..3`, `DaysLeft`, `Stress`, `Sleep`, `ExamSuccess`), plus the
raw `days_until_exam` (1–21) that `DaysLeft` is bucketed from. All state names match
the network exactly.

**Generative process.** `σ(z) = 1/(1+e^-z)`; `d` = difficulty index (easy 0, medium 1, hard 2);
`k` = number of mastered concepts.

| Variable | How it is generated |
|---|---|
| Difficulty_Ci | Categorical: easy .3, medium .4, hard .3 |
| Mastery_Ci = high | Bernoulli(σ(1.4 − 1.3·d)) |
| Quiz_Ci = high | Bernoulli(.85 if mastered, .20 if not), plus N(0, .03) noise on that probability |
| days_until_exam | Uniform integer 1..21; DaysLeft = few (≤3), some (4–10), many (>10) |
| Stress = high | Bernoulli(σ(1.6 − 0.18·days)) |
| Sleep = poor | Bernoulli(.65 if stress high, .25 if low) |
| ExamSuccess = pass | Bernoulli(σ(−2.2 + 1.6·k − 0.6·[stress high])) |

Logistic functions keep probabilities in (0, 1) and give smooth, monotone effects:
harder concepts lower mastery, a closer exam raises stress, more mastered concepts
raise the pass rate and stress lowers it. The coefficients were chosen to land near
our hand-crafted CPTs without copying them, so the learning step in §4 has something
real to estimate.

**Resulting frequencies** (vs. the hand-crafted values from §2):

| Quantity | Simulated data | Hand-crafted |
|---|---|---|
| P(Mastery=high \| easy / medium / hard) | .79 / .53 / .24 | .80 / .55 / .25 |
| P(Quiz=high \| mastery high / low) | .85 / .20 | .85 / .20 |
| P(Stress=high \| few / some / many) | .78 / .57 / .24 | .80 / .45 / .20 |
| P(Sleep=poor \| stress high / low) | .65 / .24 | .65 / .25 |
| P(pass \| k=3, stress low / high) | .94 / .85 | .95 / .85 |

The one visible gap is Stress given DaysLeft = "some": the data gives .57 because
the stress curve is steeper than our hand-crafted guess near the 4-day end of that
bucket. This is the kind of correction learning from data should make.

**Is there enough data?** 36 free CPT parameters are learned (see §4). With 5,000
rows that is **139 rows per parameter**, against the requirement of more than 10.
Looking at the sparsest case instead of the average, every parent configuration of
every learned CPT has many rows: the smallest is 236 rows (an ExamSuccess parent
combination), and the smallest for any other CPT is 776 (Stress given DaysLeft = few).
`python -m study_planner.cli simulate` prints this table.

## 4. Learning CPTs with Laplace smoothing

_(Chart: `docs/figures/cpt_comparison.png`, added in TI-00004.)_

**What is learned.** From `students.csv` (§3) we learn the CPTs of **9 variables**,
i.e. **36 free parameters**: `Mastery_C1..3`, `Quiz_C1..3`, `Stress`, `Sleep` and
`ExamSuccess`. The root priors `Difficulty_Ci` and `DaysLeft` stay hand-crafted,
because they are always overridden by evidence at decision time.

**Estimator.** For each variable X with parents Pa we count how often each value of X
occurs with each parent configuration u, and add a pseudo-count α = 1 to every cell
(Laplace smoothing):

```
P(X = x | Pa = u) = (N(x, u) + α) / (N(u) + α·|X|)
```

Smoothing guarantees that no probability is ever exactly 0, even for a combination that
never appears in the data (such a parent configuration gets the uniform distribution),
so one unlucky missing cell can never rule an outcome out. With 5,000 rows the counts
are large (§3), so α = 1 barely moves the estimates; it matters only for sparse data.
The implementation is `laplace_cpd()` in `study_planner/learning.py`, with columns
ordered the way pgmpy expects. `python -m study_planner.cli learn` runs it and writes
`data/processed/learned_cpts.json`.

**Worked example.** Sleep given Stress = high: suppose a student sample had 1,000
stressed students of whom 650 slept poorly. Then
P(poor | high) = (650 + 1) / (1000 + 2) = 0.6497.

**Validation against pgmpy.** We cross-checked all 9 learned CPTs against pgmpy's
`BayesianEstimator` with `prior_type="K2"`, which is add-one smoothing. The largest
difference over every cell is **0** (up to floating point), so our counting
implementation agrees with the library.

**Hand-crafted vs learned** (probability of the second state; full table printed by
the `learn` command):

| CPT | Parent | Hand-crafted | Learned |
|---|---|---|---|
| Mastery_C1 = high | easy / medium / hard | .80 / .55 / .25 | .79 / .53 / .24 |
| Quiz_C1 = high | mastery low / high | .20 / .85 | .20 / .85 |
| Stress = high | DaysLeft few / some / many | .80 / **.45** / .20 | .78 / **.57** / .24 |
| Sleep = good | stress low / high | .75 / .35 | .76 / .35 |
| ExamSuccess = pass | 3 mastered, stress low / high | .95 / .85 | .94 / .85 |
| ExamSuccess = pass | 0 mastered, stress low / high | .10 / .05 | .08 / .05 |

Over all 72 cells of the 9 CPTs the mean absolute difference is **0.020** and the
largest is **0.120**. Almost everything agrees to within a few percentage points,
which is expected because the data was generated from functions close to our
hand-crafted guesses. The one clear correction is P(Stress = high | DaysLeft = some):
the data says **.57**, our guess was **.45**. A student with 4–10 days left is more
stressed than we assumed, which makes the system a little more cautious about
recommending an intense session in the middle of the planning window (§6).

`build_learned_model()` returns the same network as §2 with these learned CPTs
swapped in; this is the model the decision engine uses by default.

## 5. Inference task

**Evidence** `e` (what we know about the student today): the difficulty of each
concept (`Difficulty_C1..3`), `DaysLeft` (computed from the exam date in the
calendar), and, when the student has them, the practice-quiz results
(`Quiz_C1..3`) and last night's `Sleep`.

**Query variables:**
* `P(Mastery_Ci = high | e)` for each concept: which concept is weakest?
* `P(Stress = high | e)`: how stressed is the student likely to be?
* `P(ExamSuccess = pass | e)`: the chance of passing if nothing changes.

**Algorithm.** Exact inference with pgmpy's `VariableElimination`
(`study_planner/inference.py`, function `query()`). Evidence flows in both directions
through the network: difficulty pushes mastery *down* the arrows (causal reasoning),
while a quiz result or poor sleep pushes belief *up* against the arrows
(diagnostic reasoning) to update the hidden mastery and stress.

**Example** (hand-crafted model; `tests/test_inference.py`). A student with an easy
concept: P(Mastery = high) = .80 from difficulty alone. If their practice quiz was
high, Bayes' rule gives .8·.85 / (.8·.85 + .2·.2) = **.944**; a low quiz drops it
the other way. Poor sleep raises P(Stress = high) above the value given by the
calendar alone, and fewer days left lowers P(pass).

## 6. Actions, utility & decision

**Actions** (`config.ACTIONS`; the calendar effect is described in §7):

| Action | What it schedules | Hours | Mastery boost | Stress change |
|---|---|---|---|---|
| `intense` | Mandatory 5-hour block today, all concepts | 5.0 | +0.35 | +0.20 |
| `focused` | 2.5-hour block on the weakest concept only | 2.5 | +0.50 (weakest) | +0.03 |
| `light` | 1-hour light review | 1.0 | +0.20 | −0.04 |
| `rest` | Clear planner sessions, rest day | 0.0 | 0 | −0.08 |

**Effect model.** An action changes the posteriors from §5 before they are scored.
Studying closes a fraction of the gap to full mastery, scaled by how urgent it is
(urgency is 1.0 with few days left, 0.7 with some, 0.3 with many):
`P'(M = high) = P + boost·urgency·(1 − P)`. Stress moves by the action's stress change
and is clipped to [0, 1].

**Utility** `U(ExamSuccess, Stress)`, which depends on the query variables, plus a
cost of 1 point per study hour:

| | Stress low | Stress high |
|---|---|---|
| pass | 100 | 85 |
| fail | 10 | 0 |

Passing is worth the most, but passing while burnt out is worth less than passing
calmly, and failing calmly is worth more than failing in distress. This is how the
function trades exam success against stress.

**Expected utility.** For each action `a`,

```
EU(a) = Σ_{m1,m2,m3,s} Π_i P'(Mi) · P'(s) · [ P(pass|m,s)·U(pass,s) + P(fail|m,s)·U(fail,s) ]  −  1·hours(a)
```

with `P(pass | m1,m2,m3, s)` read from the model's ExamSuccess CPD, so the same code
runs on the hand-crafted and the learned network. The mastery marginals are treated
as independent given the evidence, an approximation noted in §9. The system takes
`argmax_a EU(a)` (`decide()` in `study_planner/decision.py`).

**Worked example** (struggling student: all concepts hard, all quizzes low, 2 days left).
P(Mastery = high) is only .06 for each concept and P(Stress = high) = .80, so the
baseline P(pass) is .10:

| Action | EU hand-crafted | EU learned |
|---|---|---|
| intense | **22.4** | **23.4** |
| light | 21.8 | 22.0 |
| focused | 16.4 | 15.9 |
| rest | 11.7 | 11.2 |

The system picks `intense`: with the exam two days away and almost nothing mastered,
the extra mastery from five hours outweighs the added stress.

**No re-tuning was needed.** The five demo students from `docs/MODEL.md` §6 were
first checked with the hand-crafted CPTs and then with the learned ones (where
P(Stress = high | some days) rose from .45 to .57). The chosen action is the same
for both models for every student, so `config.py` is unchanged. See §8 for the results
across student types.

## 7. Calendar integration

The decision from §6 becomes real calendar events through a small abstraction,
`CalendarClient` (`study_planner/calendar_api/`), with three interchangeable backends:

| Backend | Use |
|---|---|
| `GoogleCalendarClient` | Google Calendar API v3 (OAuth "Desktop app" flow; `credentials.json` and `token.json` stay out of git). Reads existing events, creates study sessions, deletes planner sessions. |
| `IcsCalendarClient` | Offline fallback: reads an `.ics` export (e.g. from Google/Outlook) to find exams and writes the plan to an `.ics` file that imports into any calendar. |
| `InMemoryCalendarClient` | Used by the tests and the dashboard. |

**How a day is planned** (`StudyPlanner.plan_today` in `study_planner/planner.py`):

1. **Read the exam** from the calendar: events whose title contains "exam", "midterm" or
   "final" are exams. `DaysLeft` is computed from the exam date, so the evidence
   always reflects today's date.
2. **Decide** with §5–6: query the network, compute the expected utility of each action
   and take the best.
3. **Write the calendar.** Any earlier planner session for today is removed first, so
   running the planner again replaces the plan instead of stacking sessions. Then:
   * `intense` → a mandatory 5-hour `[BayesPlanner]` block, `focused` → 2.5 hours (the
     description names the weakest concept), `light` → a 1-hour review;
   * `rest` → no session is created, which together with step 3's clearing means the
     planner's sessions for the day are cleared ("clear the calendar for a rest day").
4. **Find a free slot.** The session starts at the earliest free 30-minute step after
   10:00 that overlaps none of the student's existing events and ends by 22:00. If the
   day is completely booked it falls back to 10:00.

Each session's description records the exam, days left, P(pass), P(stress) and the
expected utility of every action, so the student can see *why* the planner chose it.

**Safety rule.** The planner only ever deletes events whose title starts with
`[BayesPlanner]`. Every backend refuses to delete anything else (`PermissionError`),
so a bug can never remove a lecture or an exam from a student's calendar.

**Several exams.** `plan_upcoming` plans every exam in the next 60 days, nearest first,
matching each to the student's evidence by course name. Each exam gets its own decision
and session; today's old sessions are cleared once, so a rest day for one exam never
deletes the session planned for another.

**Testing.** The Google client is tested against a fake service that records the
requests it would send (event body, time zone, pagination, delete calls), and the `.ics`
client against hand-written exports with all-day and UTC events. The real Google API
needs the OAuth credentials from TI-00003, so the live round trip is verified in the
demo (§8) rather than in the automated tests.

## 8. Results: different students → different actions

_(Chart: `docs/figures/expected_utility.png`, added in TI-00004. Calendar screenshots to be added by hand.)_

`python -m study_planner.cli demo` runs five simulated students through the same
system (learned CPTs) and writes one `.ics` calendar per student to `output/`.

### Live Google Calendar verification

On November 12, 2026, Sultan completed the desktop OAuth flow and tested the
Google Calendar backend with the demo scenarios. The struggling scenario created
`[BayesPlanner] Intense 5-hour mandatory study block` from 10:00 to 15:00.
Its description showed P(pass) = 9%, P(high stress) = 78%, mastery probabilities
of 6%, 5%, and 5%, and expected utilities of intense 23.4, focused 15.9,
light 22.0, and rest 11.2. These are simulated scenario results, not estimates
of Sultan's own exam performance.

Running the advanced scenario afterward removed the study block, as confirmed
by Sultan in Google Calendar. This manually verifies authentication, event
creation, and rest-day cleanup against the live API. Automated deletion-guard
tests provide separate coverage for protecting untagged events. Setup and
reproduction steps are in `docs/GOOGLE_SETUP.md`; the calendar screenshot was
provided during verification and still needs to be added to the final report.

### One day, five students

| Student | Evidence | Beliefs: mastery / stress / pass | Chosen action | Expected utility (runner-up) |
|---|---|---|---|---|
| Struggling | all hard, all quizzes low, 2 days left | 6% / 78% / 9% | **intense** 5 h block | 23.4 (light 22.0) |
| Advanced | all easy, all quizzes high, 14 days | 94% / 24% / 87% | **rest** day | 87.2 (light 85.5) |
| One weak spot | 2 easy + 1 hard (quiz low), 7 days | 79%, 79%, **5%** / 57% / 51% | **focused** 2.5 h on C3 | 54.1 (light 53.8) |
| Average, early | all medium, no quizzes, slept well, 18 days | 53% / 12% / 54% | **light** 1 h review | 59.2 (rest 58.7) |
| Burnt-out | medium, quizzes fine, slept poorly, 3 days | 82% / 91% / 71% | **light** 1 h review | 64.4 (rest 63.9) |

Four different actions appear across the five students, and each choice follows from
the evidence: the student who has mastered almost nothing with two days to go is told to
cram; the student who is already well prepared is told to rest; a single weak concept
earns a session aimed at that concept only; and a student who is prepared but stressed
and sleeping badly gets only a gentle review rather than another long session. The
margins between the best and second-best action are small for some students (§6), but
the choices are stable under both the hand-crafted and the learned model.

### Fourteen days, two students

To show the plan adapts over time, the planner is run once per day for 14 days
(`simulate_two_weeks`). A simulated student has a hidden *true mastery* per concept.
Each day the planner sees the evidence (including the latest practice quizzes) and
picks an action, which is written to the calendar. Then the student studies and true
mastery rises by the action's boost (`m' = m + boost·(1 − m)`), and tomorrow's quizzes
come back "high" once true mastery reaches 0.5. The simulation is deterministic.

| | Struggling student | Advanced student |
|---|---|---|
| Actions over 14 days | light review every day | rest every day |
| Total study time | **14 h** (14 × 1 h) | **0 h** |
| Quizzes | low on days 1–3, high from day 4 | high throughout |
| Expected utility | 21.6 → **59.3** on day 4, then 54.6 → 51.8 | 87.2 → 74.8 (stress rises as the exam nears) |
| P(pass) | 12% → **56%** on day 4, then 52% → 50% | 87% → 82% |

The struggling student is *not* told to cram. With two weeks to go, one hour a day closes
enough of the gap that their quizzes turn around on day 4, the evidence changes, and the
planner's expected utility and pass estimate jump. They never need an intense day,
because the early light sessions already did the work. For comparison, the same student
arriving at the one-day scenario with only two days left has a 9% pass estimate and the
only sensible plan is a 5-hour block. This is the intended effect of the utility function:
trading a small amount of effort now for less last-minute cramming stress. The advanced student
is never given a study session, and the other students adapt on the same principle: for
example the burnt-out student rests until the exam is three days away and only then eases
back in with 1-hour reviews (checked in `tests/test_scenarios.py`).

**Assumptions to keep in mind.** The simulated student is our own model, not real data:
true mastery rises by the same boost the planner assumes, a quiz is "high" at 0.5 mastery,
and the effect of an action on stress is priced on the day it is taken but not carried to
the next day. The network is a snapshot of one day and does not remember past sessions; only
the quiz results carry the improvement forward. That is why the struggling student's
estimated pass chance (about 50%) stays conservative even when their true mastery is 0.95.

## 9. Limitations & future work
_(TI-00005)_ e.g. mastery marginals treated as independent in the action model,
simulated rather than real data, action effects hand-set.
