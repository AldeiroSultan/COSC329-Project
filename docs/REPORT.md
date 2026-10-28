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
_(MF-00002)_ Why simulated, the generating functions, N, seed, parent-configuration
counts showing > 10 rows per learned parameter.

## 4. Learning CPTs with Laplace smoothing
_(MF-00003)_ The 4+ learned variables, the estimator formula, hand-crafted vs learned
comparison table (`docs/figures/cpt_comparison.png`), cross-check with pgmpy K2.

## 5. Inference task
_(MF-00004)_ Evidence variables, query variables, algorithm (Variable Elimination),
example posteriors.

## 6. Actions, utility & decision
_(MF-00004)_ The 4 actions and their effect model, utility table, EU formula,
any tuning and why.

## 7. Calendar integration
_(MF-00005)_ Google Calendar API flow, .ics fallback, safety rule for deleting events.

## 8. Results: different students → different actions
_(MF-00006)_ Scenario table (evidence, posteriors, EU per action, chosen action),
`docs/figures/expected_utility.png`, 14-day simulation for struggling vs advanced,
calendar screenshots.

## 9. Limitations & future work
_(TI-00005)_ e.g. mastery marginals treated as independent in the action model,
simulated rather than real data, action effects hand-set.
