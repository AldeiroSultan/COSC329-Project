"""Simulate student records and write them to CSV (branch MF-00002).

See docs/DATA.md for the generative process.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from study_planner import config as cfg

# Coefficients of the generative functions (docs/DATA.md).
MASTERY_INTERCEPT, MASTERY_SLOPE = 1.4, -1.3        # sigma(1.4 - 1.3 * difficulty_index)
QUIZ_NOISE_SD = 0.03                                 # jitter on the quiz probability
MAX_DAYS = 21                                        # days_until_exam ~ Uniform{1..21}
STRESS_INTERCEPT, STRESS_SLOPE = 1.6, -0.18          # sigma(1.6 - 0.18 * days)
EXAM_INTERCEPT, EXAM_PER_CONCEPT, EXAM_STRESS = -2.2, 1.6, -0.6

COLUMNS = (
    ["student_id"]
    + [cfg.NODE_DIFFICULTY[c] for c in cfg.CONCEPTS]
    + [cfg.NODE_MASTERY[c] for c in cfg.CONCEPTS]
    + [cfg.NODE_QUIZ[c] for c in cfg.CONCEPTS]
    + ["days_until_exam", cfg.NODE_DAYS, cfg.NODE_STRESS, cfg.NODE_SLEEP, cfg.NODE_EXAM]
)


def sigmoid(z: np.ndarray | float) -> np.ndarray | float:
    return 1.0 / (1.0 + np.exp(-z))


def _pick(states: list[str], is_second: np.ndarray) -> np.ndarray:
    """Map a boolean array to the 2-state names (False -> states[0], True -> states[1])."""
    return np.where(is_second, states[1], states[0])


def simulate_students(n: int = cfg.N_STUDENTS, seed: int = cfg.RANDOM_SEED) -> pd.DataFrame:
    """Generate n students following docs/DATA.md; columns in the documented order."""
    rng = np.random.default_rng(seed)
    data: dict[str, np.ndarray] = {"student_id": np.arange(1, n + 1)}

    # Per concept: Difficulty -> Mastery -> Quiz
    p_difficulty = [cfg.P_DIFFICULTY[s] for s in cfg.DIFFICULTY_STATES]
    mastered = np.zeros(n, dtype=int)
    for c in cfg.CONCEPTS:
        d_idx = rng.choice(len(cfg.DIFFICULTY_STATES), size=n, p=p_difficulty)
        p_mastery = sigmoid(MASTERY_INTERCEPT + MASTERY_SLOPE * d_idx)
        m_high = rng.random(n) < p_mastery
        p_quiz = np.where(m_high, cfg.P_QUIZ_HIGH_GIVEN_MASTERY["high"], cfg.P_QUIZ_HIGH_GIVEN_MASTERY["low"])
        p_quiz = np.clip(p_quiz + rng.normal(0.0, QUIZ_NOISE_SD, n), 0.01, 0.99)
        q_high = rng.random(n) < p_quiz

        data[cfg.NODE_DIFFICULTY[c]] = np.array(cfg.DIFFICULTY_STATES)[d_idx]
        data[cfg.NODE_MASTERY[c]] = _pick(cfg.MASTERY_STATES, m_high)
        data[cfg.NODE_QUIZ[c]] = _pick(cfg.QUIZ_STATES, q_high)
        mastered += m_high

    # DaysLeft -> Stress -> Sleep
    days = rng.integers(1, MAX_DAYS + 1, size=n)
    stress_high = rng.random(n) < sigmoid(STRESS_INTERCEPT + STRESS_SLOPE * days)
    p_poor = np.where(stress_high, cfg.P_SLEEP_POOR_GIVEN_STRESS["high"], cfg.P_SLEEP_POOR_GIVEN_STRESS["low"])
    sleep_poor = rng.random(n) < p_poor

    data["days_until_exam"] = days
    data[cfg.NODE_DAYS] = np.array([cfg.days_bucket(int(d)) for d in days])
    data[cfg.NODE_STRESS] = _pick(cfg.STRESS_STATES, stress_high)
    data[cfg.NODE_SLEEP] = _pick(cfg.SLEEP_STATES, ~sleep_poor)  # SLEEP_STATES = [poor, good]

    # Mastery (count) + Stress -> ExamSuccess
    z = EXAM_INTERCEPT + EXAM_PER_CONCEPT * mastered + EXAM_STRESS * stress_high
    passed = rng.random(n) < sigmoid(z)
    data[cfg.NODE_EXAM] = _pick(cfg.EXAM_STATES, passed)

    return pd.DataFrame(data)[COLUMNS]


def learned_cpt_parents() -> dict[str, tuple[str, list[str]]]:
    """Learned CPTs (docs/MODEL.md §2b) as {label: (child, parents)}."""
    cpts: dict[str, tuple[str, list[str]]] = {}
    for c in cfg.CONCEPTS:
        cpts[f"{cfg.NODE_MASTERY[c]} | {cfg.NODE_DIFFICULTY[c]}"] = (cfg.NODE_MASTERY[c], [cfg.NODE_DIFFICULTY[c]])
    for c in cfg.CONCEPTS:
        cpts[f"{cfg.NODE_QUIZ[c]} | {cfg.NODE_MASTERY[c]}"] = (cfg.NODE_QUIZ[c], [cfg.NODE_MASTERY[c]])
    cpts[f"{cfg.NODE_STRESS} | {cfg.NODE_DAYS}"] = (cfg.NODE_STRESS, [cfg.NODE_DAYS])
    cpts[f"{cfg.NODE_SLEEP} | {cfg.NODE_STRESS}"] = (cfg.NODE_SLEEP, [cfg.NODE_STRESS])
    exam_parents = [cfg.NODE_MASTERY[c] for c in cfg.CONCEPTS] + [cfg.NODE_STRESS]
    cpts[f"{cfg.NODE_EXAM} | {', '.join(exam_parents)}"] = (cfg.NODE_EXAM, exam_parents)
    return cpts


def parent_config_counts(df: pd.DataFrame) -> dict[str, pd.Series]:
    """Row count for every parent configuration of each learned CPT (data sufficiency check).

    Configurations that never occur in the data are listed with a count of 0.
    """
    from study_planner.network import state_names

    names = state_names()
    counts: dict[str, pd.Series] = {}
    for label, (_, parents) in learned_cpt_parents().items():
        if len(parents) == 1:  # plain Index so counts.loc["hard"] works
            full_index = pd.Index(names[parents[0]], name=parents[0])
        else:
            full_index = pd.MultiIndex.from_product([names[p] for p in parents], names=parents)
        observed = df.groupby(parents).size()
        counts[label] = observed.reindex(full_index, fill_value=0)
    return counts


def write_csv(df: pd.DataFrame, path: Path = cfg.STUDENTS_CSV) -> Path:
    """Write the dataframe to CSV, creating parent folders."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path
