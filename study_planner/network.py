"""Bayesian network structure and hand-crafted CPTs (branch MF-00001).

See docs/MODEL.md §1-2a.
"""

from __future__ import annotations

from pgmpy.factors.discrete import TabularCPD

try:  # pgmpy >= 0.1.26
    from pgmpy.models import DiscreteBayesianNetwork as BayesNet
except ImportError:  # older pgmpy
    from pgmpy.models import BayesianNetwork as BayesNet

from study_planner import config as cfg


def network_edges() -> list[tuple[str, str]]:
    """Return the 13-node DAG as (parent, child) edges."""
    edges: list[tuple[str, str]] = []
    for c in cfg.CONCEPTS:
        edges.append((cfg.NODE_DIFFICULTY[c], cfg.NODE_MASTERY[c]))
        edges.append((cfg.NODE_MASTERY[c], cfg.NODE_QUIZ[c]))
        edges.append((cfg.NODE_MASTERY[c], cfg.NODE_EXAM))
    edges.append((cfg.NODE_DAYS, cfg.NODE_STRESS))
    edges.append((cfg.NODE_STRESS, cfg.NODE_SLEEP))
    edges.append((cfg.NODE_STRESS, cfg.NODE_EXAM))
    return edges


def state_names() -> dict[str, list[str]]:
    """Map every node to its ordered list of states."""
    names: dict[str, list[str]] = {}
    for c in cfg.CONCEPTS:
        names[cfg.NODE_DIFFICULTY[c]] = cfg.DIFFICULTY_STATES
        names[cfg.NODE_MASTERY[c]] = cfg.MASTERY_STATES
        names[cfg.NODE_QUIZ[c]] = cfg.QUIZ_STATES
    names[cfg.NODE_DAYS] = cfg.DAYS_STATES
    names[cfg.NODE_STRESS] = cfg.STRESS_STATES
    names[cfg.NODE_SLEEP] = cfg.SLEEP_STATES
    names[cfg.NODE_EXAM] = cfg.EXAM_STATES
    return names


def handcrafted_cpds() -> list[TabularCPD]:
    """Build every TabularCPD from the hand-crafted values in config.py.

    TODO(MF-00001): one TabularCPD per node; use state_names() for state_names=.
    ExamSuccess has parents [Mastery_C1, Mastery_C2, Mastery_C3, Stress]; fill each
    column from cfg.P_PASS_GIVEN_K_STRESS using k = number of 'high' masteries.
    """
    raise NotImplementedError("MF-00001")


def build_handcrafted_model() -> BayesNet:
    """Return the full network with hand-crafted CPTs; must pass check_model().

    TODO(MF-00001)
    """
    raise NotImplementedError("MF-00001")
