"""Learn CPTs from the simulated CSV with Laplace smoothing (branch MF-00003).

P(X = x | Pa = u) = (N(x, u) + alpha) / (N(u) + alpha * |X|)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from pgmpy.factors.discrete import TabularCPD

from study_planner import config as cfg
from study_planner.network import BayesNet


def learned_variables() -> list[str]:
    """Nodes whose CPTs are learned from data (docs/MODEL.md §2b)."""
    return (
        [cfg.NODE_MASTERY[c] for c in cfg.CONCEPTS]
        + [cfg.NODE_QUIZ[c] for c in cfg.CONCEPTS]
        + [cfg.NODE_STRESS, cfg.NODE_SLEEP, cfg.NODE_EXAM]
    )


def laplace_cpd(
    df: pd.DataFrame,
    child: str,
    parents: list[str],
    alpha: float = cfg.LAPLACE_ALPHA,
) -> TabularCPD:
    """Count frequencies of child given parents and apply Laplace smoothing.

    TODO(MF-00003): iterate parent configurations in pgmpy column order
    (itertools.product over parents' states, last parent varying fastest).
    """
    raise NotImplementedError("MF-00003")


def learn_cpds(csv_path: Path = cfg.STUDENTS_CSV) -> list[TabularCPD]:
    """Learn every CPD in learned_variables() from the CSV.

    TODO(MF-00003)
    """
    raise NotImplementedError("MF-00003")


def build_learned_model(csv_path: Path = cfg.STUDENTS_CSV) -> BayesNet:
    """Hand-crafted model with learned CPDs swapped in; must pass check_model().

    TODO(MF-00003)
    """
    raise NotImplementedError("MF-00003")


def save_cpds(cpds: list[TabularCPD], path: Path = cfg.LEARNED_CPTS_JSON) -> Path:
    """Save CPDs as JSON {variable: {parents, states, values}} for the report/dashboard.

    TODO(MF-00003)
    """
    raise NotImplementedError("MF-00003")
