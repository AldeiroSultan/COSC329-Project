# Model Design — Bayesian Study Planner

This is the single source of truth for the network, the inference task, the
actions and the utility function. Code in `study_planner/` must match this file.
If you change a number in `study_planner/config.py`, update this file in the
same branch.

---

## 1. Network structure (13 nodes)

```
 Difficulty_C1   Difficulty_C2   Difficulty_C3          DaysLeft
       │               │               │                    │
       ▼               ▼               ▼                    ▼
  Mastery_C1      Mastery_C2      Mastery_C3             Stress ──────► Sleep (obs)
   │      │        │      │        │      │                 │
   ▼      └────────┼──────┴────────┼──────┴──────┐          │
 Quiz_C1 (obs)  Quiz_C2 (obs)   Quiz_C3 (obs)    ▼          │
                                             ExamSuccess ◄──┘
```

| Node | States | Parents | Role |
|---|---|---|---|
| `Difficulty_Ci` (i=1..3) | easy, medium, hard | — | Evidence. Entered by the user per concept. |
| `Mastery_Ci` | low, high | `Difficulty_Ci` | **Hidden / queried.** The student's real grasp of the concept. |
| `Quiz_Ci` | low, high | `Mastery_Ci` | Observable (2-person extension). Practice-quiz result; noisy signal of mastery. |
| `DaysLeft` | few (≤3), some (4–10), many (>10) | — | Evidence. Computed from the exam date in the calendar. |
| `Stress` | low, high | `DaysLeft` | **Queried.** Student stress. |
| `Sleep` | poor, good | `Stress` | Observable (2-person extension). Self-reported sleep last night. |
| `ExamSuccess` | fail, pass | `Mastery_C1..3`, `Stress` | **Queried.** Outcome we want to maximise. |

Core network (1-person spec) = the 9 nodes without `Quiz_*` and `Sleep`.
The 2-person extension adds the 4 observable nodes `Quiz_C1..3` and `Sleep`,
which let the system *infer* mastery and stress from things the student can
actually report, instead of guessing from difficulty alone.

### Why this structure
* Difficulty → Mastery: harder concepts are less likely to be mastered.
* Mastery → Quiz: quiz score is caused by mastery (diagnostic reasoning flows
  backwards when we observe a quiz).
* DaysLeft → Stress: stress rises as the exam approaches (cramming stress).
* Stress → Sleep: stressed students sleep worse, so poor sleep is evidence of stress.
* Mastery + Stress → ExamSuccess: knowing the material helps; high stress hurts.

---

## 2. CPTs

### 2a. Hand-crafted (MF-00001) — used as the prior / fallback model

| CPT | Values | Rationale |
|---|---|---|
| P(Difficulty_Ci) | easy .3, medium .4, hard .3 | Root prior; always overridden by evidence. |
| P(DaysLeft) | few .2, some .4, many .4 | Root prior; always overridden by evidence. |
| P(Mastery=high \| Difficulty) | easy .80, medium .55, hard .25 | Harder → less mastery. |
| P(Quiz=high \| Mastery) | high .85, low .20 | Quiz is a good but noisy test. |
| P(Stress=high \| DaysLeft) | few .80, some .45, many .20 | Cramming stress. |
| P(Sleep=poor \| Stress) | high .65, low .25 | |
| P(ExamSuccess=pass \| #mastered, Stress) | see table | |

ExamSuccess hand-crafted table (depends on how many of the 3 concepts are mastered):

| # concepts mastered | Stress=low | Stress=high |
|---|---|---|
| 0 | .10 | .05 |
| 1 | .35 | .25 |
| 2 | .70 | .55 |
| 3 | .95 | .85 |

### 2b. Learned from data (MF-00003) — 4+ variables

We learn these CPTs from `data/processed/students.csv` with **Laplace (add-1)
smoothing**:

1. `Mastery_Ci | Difficulty_Ci` (×3)
2. `Quiz_Ci | Mastery_Ci` (×3)
3. `Stress | DaysLeft`
4. `Sleep | Stress`
5. `ExamSuccess | Mastery_C1, Mastery_C2, Mastery_C3, Stress`

Estimator for each row of a CPT:

```
P(X = x | Pa = u) = (N(x, u) + α) / (N(u) + α·|X|)        α = 1 (Laplace)
```

Parameter count / data check (must be > 10 rows of data per learned parameter):

| CPT | free params | rows needed (×10) |
|---|---|---|
| Mastery_Ci \| Difficulty (×3) | 3 each → 9 | 90 |
| Quiz_Ci \| Mastery (×3) | 2 each → 6 | 60 |
| Stress \| DaysLeft | 3 | 30 |
| Sleep \| Stress | 2 | 20 |
| ExamSuccess \| M1,M2,M3,Stress | 16 | 160 |
| **Total** | **36** | **360** |

We simulate **N = 5,000** students (≈139 rows per parameter), well above the
requirement — and still enough that the rarest parent configuration of
ExamSuccess has dozens of rows.

---

## 3. Inference task (document this in the report!)

**Evidence** `e` (whatever is known about the student today):
`Difficulty_C1..3`, `DaysLeft`, and when available `Quiz_C1..3`, `Sleep`.

**Query variables:**
* `P(Mastery_Ci | e)` for i = 1..3 → which concept is weakest
* `P(Stress | e)` → how stressed the student probably is
* `P(ExamSuccess | e)` → baseline chance of passing if nothing changes

**Algorithm:** pgmpy `VariableElimination` (exact inference, built-in).

---

## 4. Actions (decision alternatives)

| Key | Calendar effect | Hours | Mastery boost | Stress change |
|---|---|---|---|---|
| `intense` | Mandatory 5-hour study block today, all concepts | 5.0 | +0.35 × urgency on **every** concept | +0.20 |
| `focused` | 2.5-hour block on the **weakest** concept only | 2.5 | +0.50 × urgency on weakest concept | +0.03 |
| `light` | 1-hour light review | 1.0 | +0.20 × urgency on every concept | −0.04 |
| `rest` | Clear planner study blocks today, rest day | 0.0 | 0 | −0.08 |

"Mastery boost" moves probability mass: `P'(Mi=high) = P(Mi=high) + boost·(1 − P(Mi=high))`.
"Stress change" is additive on `P(Stress=high)`, clipped to [0, 1].

Urgency (studying today matters more when the exam is close):

| DaysLeft | few | some | many |
|---|---|---|---|
| urgency | 1.0 | 0.7 | 0.3 |

**Rest day safety:** "clear the calendar" only deletes events the planner created
(tagged `[BayesPlanner]`). It never deletes the student's own events.

---

## 5. Utility function

Utility depends on the two outcome variables `ExamSuccess` and `Stress`:

| | Stress=low | Stress=high |
|---|---|---|
| **ExamSuccess=pass** | 100 | 85 |
| **ExamSuccess=fail** | 10 | 0 |

Plus a small time cost of **1 utility point per study hour** (studying isn't free).

Expected utility of action `a`:

```
EU(a) = Σ_{x∈{pass,fail}} Σ_{s∈{low,high}} P'_a(ExamSuccess=x, Stress=s) · U(x, s)  −  1·hours(a)
```

where `P'_a` is computed by:
1. Query the BN for `P(Mastery_Ci | e)` and `P(Stress | e)`.
2. Apply the action's effect (section 4) to get `P'_a(Mastery_Ci)` and `P'_a(Stress)`.
3. Push those through the ExamSuccess CPT:
   `P'_a(pass, s) = Σ_{m1,m2,m3} P(pass | m1,m2,m3,s) · Π_i P'_a(Mi=mi) · P'_a(Stress=s)`
   (mastery marginals treated as independent given the evidence — an
   approximation we state in the report).

The system picks `a* = argmax_a EU(a)` and writes it to the calendar.

---

## 6. Expected behaviour (what the demo must show)

With the **hand-crafted** CPTs and the numbers above, a quick hand calculation
gives (EU values in brackets):

| Scenario | Evidence | Action picked |
|---|---|---|
| Struggling student | all hard, all quizzes low, few days | `intense` (22.4 vs light 21.8) |
| Advanced student | all easy, all quizzes high, many days | `rest` (88.8 vs light 87.1) |
| One weak spot | easy, easy, hard; quiz on C3 low; some days | `focused` (56.6 vs light 56.3) |
| Average, early | all medium, no quizzes, many days, good sleep | `light` (61.0 vs rest 60.7) |
| Burnt-out | all medium, quizzes high, few days, poor sleep | `light` (64.5 vs rest 64.0) |

The margins are thin. After MF-00003 swaps in the **learned** CPTs the numbers
will move, so MF-00004 re-checks these scenarios and, if needed, re-tunes
`config.py` (update this file too and explain the tuning in the report).
