# Data — Simulated Student Records

We **simulate** data (the spec allows this) because no public dataset records
per-concept mastery, quiz results, stress, sleep and exam outcome together.
The generator lives in `study_planner/simulate_data.py` (branch MF-00002).

Output: `data/processed/students.csv`, one row per simulated student, **N = 5,000**,
fixed random seed `329` so everyone gets the same file.

## Columns

`student_id, Difficulty_C1, Difficulty_C2, Difficulty_C3, Mastery_C1, Mastery_C2,
Mastery_C3, Quiz_C1, Quiz_C2, Quiz_C3, days_until_exam, DaysLeft, Stress, Sleep,
ExamSuccess`

All BN columns use the exact state names from `docs/MODEL.md`
(`easy/medium/hard`, `low/high`, `few/some/many`, `poor/good`, `fail/pass`).
`days_until_exam` is the raw integer kept for transparency; `DaysLeft` is its bucket.

## Generative process (the "reasonably meaningful mathematical function")

`σ(z) = 1 / (1 + e^(−z))` is the logistic function. `d ∈ {0,1,2}` is difficulty
index (easy, medium, hard). Each step draws a Bernoulli / categorical sample.

| Variable | Formula |
|---|---|
| `Difficulty_Ci` | Categorical(easy .3, medium .4, hard .3) |
| `Mastery_Ci = high` | p = σ(1.4 − 1.3·d) → easy ≈ .80, medium ≈ .52, hard ≈ .23 |
| `Quiz_Ci = high` | p = 0.85 if mastery high, 0.20 if low (+ N(0, 0.03) jitter, clipped) |
| `days_until_exam` | Uniform integer 1..21 |
| `DaysLeft` | few if ≤ 3, some if 4–10, many if > 10 |
| `Stress = high` | p = σ(1.6 − 0.18·days_until_exam) |
| `Sleep = poor` | p = 0.65 if stress high, 0.25 if low |
| `ExamSuccess = pass` | p = σ(−2.2 + 1.6·k − 0.6·[stress=high]), k = # concepts mastered |

Why these functions:
* Logistic curves keep probabilities in (0, 1) and give smooth, monotone effects
  ("harder → lower mastery", "closer exam → more stress").
* ExamSuccess grows with the number of mastered concepts and is hurt by stress,
  matching the hand-crafted CPT shape.
* The coefficients were chosen so the generated frequencies are close to (but not
  identical to) the hand-crafted CPTs — so the learned model is recognisably
  similar but genuinely comes from data.

## Data sufficiency

36 free parameters are learned (see `docs/MODEL.md` §2b). 5,000 rows gives
≈139 rows per parameter (> 10 required). `simulate_data.py` also prints the
row count of each parent configuration so we can show the smallest one in the report.

## Learning

`study_planner/learning.py` (MF-00003) counts frequencies from the CSV and applies
**Laplace smoothing (α = 1)**:

```
P(X = x | Pa = u) = (N(x, u) + 1) / (N(u) + |X|)
```

The learned CPTs are saved to `data/processed/learned_cpts.json` and compared
against the hand-crafted ones in the report.
