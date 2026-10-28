"""Bayesian network structure and hand-crafted CPTs (branch MF-00001).

See docs/MODEL.md §1-2a.
"""

from __future__ import annotations

import itertools

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


def exam_parents() -> list[str]:
    """Parents of ExamSuccess, in the column order used by its CPD."""
    return [cfg.NODE_MASTERY[c] for c in cfg.CONCEPTS] + [cfg.NODE_STRESS]


def _root_cpd(node: str, prior: dict[str, float]) -> TabularCPD:
    states = state_names()[node]
    return TabularCPD(node, len(states), [[prior[s]] for s in states], state_names={node: states})


def _binary_child_cpd(
    child: str, parent: str, p_second_state: dict[str, float]
) -> TabularCPD:
    """CPD for a 2-state child with one parent.

    p_second_state[parent_state] = P(child = child_states[1] | parent_state), e.g.
    P(Mastery=high | Difficulty). Column order follows the parent's state order.
    """
    names = state_names()
    parent_states = names[parent]
    second = [p_second_state[ps] for ps in parent_states]
    return TabularCPD(
        child,
        2,
        [[1 - p for p in second], second],
        evidence=[parent],
        evidence_card=[len(parent_states)],
        state_names={child: names[child], parent: parent_states},
    )


def _exam_cpd() -> TabularCPD:
    """P(ExamSuccess | Mastery_C1..3, Stress) from the (#mastered, stress) table.

    pgmpy column order: itertools.product over the parents' states, last parent
    varying fastest.
    """
    names = state_names()
    parents = exam_parents()
    p_pass = []
    for combo in itertools.product(*(names[p] for p in parents)):
        *masteries, stress = combo
        k = sum(m == "high" for m in masteries)
        p_pass.append(cfg.P_PASS_GIVEN_K_STRESS[k][stress])
    # "fail" row first to match cfg.EXAM_STATES order
    return TabularCPD(
        cfg.NODE_EXAM,
        len(cfg.EXAM_STATES),
        [[1 - p for p in p_pass], p_pass],
        evidence=parents,
        evidence_card=[len(names[p]) for p in parents],
        state_names={cfg.NODE_EXAM: cfg.EXAM_STATES, **{p: names[p] for p in parents}},
    )


def handcrafted_cpds() -> list[TabularCPD]:
    """Build every TabularCPD from the hand-crafted values in config.py."""
    cpds: list[TabularCPD] = []
    for c in cfg.CONCEPTS:
        cpds.append(_root_cpd(cfg.NODE_DIFFICULTY[c], cfg.P_DIFFICULTY))
        cpds.append(
            _binary_child_cpd(cfg.NODE_MASTERY[c], cfg.NODE_DIFFICULTY[c], cfg.P_MASTERY_HIGH_GIVEN_DIFFICULTY)
        )
        cpds.append(_binary_child_cpd(cfg.NODE_QUIZ[c], cfg.NODE_MASTERY[c], cfg.P_QUIZ_HIGH_GIVEN_MASTERY))
    cpds.append(_root_cpd(cfg.NODE_DAYS, cfg.P_DAYS))
    cpds.append(_binary_child_cpd(cfg.NODE_STRESS, cfg.NODE_DAYS, cfg.P_STRESS_HIGH_GIVEN_DAYS))
    # SLEEP_STATES = [poor, good], so the second state is "good": P(good) = 1 - P(poor)
    p_sleep_good = {s: 1 - p for s, p in cfg.P_SLEEP_POOR_GIVEN_STRESS.items()}
    cpds.append(_binary_child_cpd(cfg.NODE_SLEEP, cfg.NODE_STRESS, p_sleep_good))
    cpds.append(_exam_cpd())
    return cpds


def build_handcrafted_model() -> BayesNet:
    """Return the full network with hand-crafted CPTs; passes check_model()."""
    model = BayesNet(network_edges())
    model.add_cpds(*handcrafted_cpds())
    model.check_model()
    return model
