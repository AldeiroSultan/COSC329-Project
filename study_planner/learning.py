"""Learn CPTs from the simulated CSV with Laplace smoothing (branch MF-00003).

P(X = x | Pa = u) = (N(x, u) + alpha) / (N(u) + alpha * |X|)
"""

from __future__ import annotations

import itertools
import json
from collections import Counter
from pathlib import Path

import pandas as pd
from pgmpy.factors.discrete import TabularCPD

try:  # pgmpy >= 1.1 (the old pgmpy.estimators path is deprecated)
    from pgmpy.parameter_estimator import DiscreteBayesianEstimator
except ImportError:  # older pgmpy
    DiscreteBayesianEstimator = None
    from pgmpy.estimators import BayesianEstimator

from study_planner import config as cfg
from study_planner.network import (
    BayesNet,
    exam_parents,
    handcrafted_cpds,
    network_edges,
    state_names,
)


def learned_variables() -> list[str]:
    """Nodes whose CPTs are learned from data (docs/MODEL.md §2b)."""
    return (
        [cfg.NODE_MASTERY[c] for c in cfg.CONCEPTS]
        + [cfg.NODE_QUIZ[c] for c in cfg.CONCEPTS]
        + [cfg.NODE_STRESS, cfg.NODE_SLEEP, cfg.NODE_EXAM]
    )


def parents_of(node: str) -> list[str]:
    """Parents of a node in the order its CPD uses (ExamSuccess: Mastery_C1..3, Stress)."""
    if node == cfg.NODE_EXAM:
        return exam_parents()
    return [parent for parent, child in network_edges() if child == node]


def laplace_cpd(
    df: pd.DataFrame,
    child: str,
    parents: list[str],
    alpha: float = cfg.LAPLACE_ALPHA,
) -> TabularCPD:
    """Count frequencies of child given parents and apply Laplace smoothing.

    Columns follow pgmpy's order: itertools.product over the parents' states,
    last parent varying fastest. A parent configuration that never occurs in the
    data gets a uniform column, because (0 + alpha) / (0 + alpha * |X|) = 1 / |X|
    (also enforced for alpha = 0, where the formula would divide by zero).
    """
    names = state_names()
    nodes = [child] + parents
    for node in nodes:
        unknown = set(df[node]) - set(names[node])
        if unknown:
            raise ValueError(f"{node} has states not in the network: {sorted(unknown)}")

    counts = Counter(zip(*(df[n] for n in parents), df[child]))
    child_states = names[child]
    columns = []
    for config in itertools.product(*(names[p] for p in parents)):
        cell = [counts[(*config, s)] + alpha for s in child_states]
        total = sum(cell)
        if total == 0:  # only possible when alpha == 0 and the configuration is unseen
            columns.append([1 / len(child_states)] * len(child_states))
        else:
            columns.append([c / total for c in cell])

    values = [[col[i] for col in columns] for i in range(len(child_states))]
    return TabularCPD(
        child,
        len(child_states),
        values,
        evidence=parents or None,
        evidence_card=[len(names[p]) for p in parents] or None,
        state_names={n: names[n] for n in nodes},
    )


def learn_cpds(csv_path: Path = cfg.STUDENTS_CSV) -> list[TabularCPD]:
    """Learn every CPD in learned_variables() from the CSV."""
    df = pd.read_csv(csv_path)
    return [laplace_cpd(df, node, parents_of(node)) for node in learned_variables()]


def build_learned_model(csv_path: Path = cfg.STUDENTS_CSV) -> BayesNet:
    """Hand-crafted model with learned CPDs swapped in; passes check_model().

    The root priors (Difficulty_Ci, DaysLeft) stay hand-crafted: they are always
    overridden by evidence, so there is nothing useful to learn there.
    """
    learned = learn_cpds(csv_path)
    learned_nodes = set(learned_variables())
    kept = [cpd for cpd in handcrafted_cpds() if cpd.variable not in learned_nodes]
    model = BayesNet(network_edges())
    model.add_cpds(*kept, *learned)
    model.check_model()
    return model


def cpd_as_dict(cpd: TabularCPD) -> dict[tuple, float]:
    """{(child_state, parent states in parents_of() order): probability}."""
    parents = parents_of(cpd.variable)
    names = state_names()
    table = {}
    for config in itertools.product(*(names[p] for p in parents)):
        for state in names[cpd.variable]:
            query = {cpd.variable: state, **dict(zip(parents, config))}
            table[(state, config)] = float(cpd.get_value(**query))
    return table


def compare_cpds(learned: list[TabularCPD]) -> pd.DataFrame:
    """Long table of hand-crafted vs learned probabilities for every learned CPD cell."""
    handcrafted = {cpd.variable: cpd for cpd in handcrafted_cpds()}
    rows = []
    for cpd in learned:
        hand = cpd_as_dict(handcrafted[cpd.variable])
        for (state, config), p_learned in cpd_as_dict(cpd).items():
            rows.append({
                "cpt": cpd.variable,
                "parents": ", ".join(f"{p}={v}" for p, v in zip(parents_of(cpd.variable), config)),
                "state": state,
                "handcrafted": hand[(state, config)],
                "learned": p_learned,
            })
    table = pd.DataFrame(rows)
    table["abs_diff"] = (table["learned"] - table["handcrafted"]).abs()
    return table


def pgmpy_k2_cpd(df: pd.DataFrame, child: str) -> TabularCPD:
    """The same CPD from pgmpy's BayesianEstimator; K2 prior = add-1 (Laplace, alpha=1)."""
    model = BayesNet(network_edges())
    data = df[list(model.nodes())]
    if DiscreteBayesianEstimator is not None:
        fitted = DiscreteBayesianEstimator(state_names=state_names(), prior_type="K2").fit(model, data)
        return next(cpd for cpd in fitted.parameters_ if cpd.variable == child)
    return BayesianEstimator(model, data, state_names=state_names()).estimate_cpd(child, prior_type="K2")


def crosscheck_with_pgmpy(df: pd.DataFrame, child: str) -> float:
    """Largest absolute difference between our Laplace CPD and pgmpy's K2 CPD for `child`."""
    ours = cpd_as_dict(laplace_cpd(df, child, parents_of(child)))
    theirs = cpd_as_dict(pgmpy_k2_cpd(df, child))
    return max(abs(ours[key] - theirs[key]) for key in ours)


def save_cpds(cpds: list[TabularCPD], path: Path = cfg.LEARNED_CPTS_JSON) -> Path:
    """Save CPDs as JSON {variable: {parents, states, parent_states, values}} for the report/dashboard.

    values[i][j] = P(states[i] | j-th parent configuration), configurations in the
    order itertools.product(*parent_states) (last parent varies fastest).
    """
    names = state_names()
    out = {}
    for cpd in cpds:
        parents = parents_of(cpd.variable)
        out[cpd.variable] = {
            "parents": parents,
            "states": names[cpd.variable],
            "parent_states": {p: names[p] for p in parents},
            "values": [[float(v) for v in row] for row in cpd.get_values()],
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return path
