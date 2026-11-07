"""Action effects, utility and expected-utility decision (branch MF-00004).

See docs/MODEL.md §4-5.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

from study_planner import config as cfg
from study_planner.inference import Posteriors
from study_planner.network import BayesNet


@dataclass
class Decision:
    best: cfg.Action
    expected_utility: dict[str, float]   # action key -> EU
    target_concept: str                  # weakest concept (used by 'focused')
    posteriors: Posteriors


def utility(exam_state: str, stress_state: str) -> float:
    """U(ExamSuccess, Stress) from config.UTILITY."""
    return cfg.UTILITY[exam_state][stress_state]


def weakest_concept(post: Posteriors) -> str:
    """Concept with the lowest P(Mastery=high | e); the first one wins ties."""
    return min(cfg.CONCEPTS, key=lambda c: post.p_mastery_high[c])


def apply_action(post: Posteriors, action: cfg.Action, days_state: str) -> tuple[dict[str, float], float]:
    """Return (P'(Mastery_Ci=high) per concept, P'(Stress=high)) after the action.

    The boost closes a fraction of the remaining gap, scaled by how urgent studying
    is today: p' = p + boost * (1 - p), boost = action.mastery_boost * URGENCY[days].
    """
    boost = action.mastery_boost * cfg.URGENCY[days_state]
    targets = cfg.CONCEPTS if action.target == "all" else [weakest_concept(post)]
    mastery = dict(post.p_mastery_high)
    for c in targets:
        mastery[c] = mastery[c] + boost * (1.0 - mastery[c])
    stress = min(1.0, max(0.0, post.p_stress_high + action.stress_delta))
    return mastery, stress


def p_pass_given(model: BayesNet, masteries: tuple[str, ...], stress: str) -> float:
    """P(ExamSuccess=pass | Mastery_C1..3, Stress) read from the model's CPD."""
    cpd = model.get_cpds(cfg.NODE_EXAM)
    query = {cfg.NODE_EXAM: "pass", cfg.NODE_STRESS: stress}
    query.update({cfg.NODE_MASTERY[c]: m for c, m in zip(cfg.CONCEPTS, masteries)})
    return float(cpd.get_value(**query))


def expected_utility(model: BayesNet, post: Posteriors, action: cfg.Action, days_state: str) -> float:
    """EU(a) = sum over exam, stress of P'_a(exam, stress) * U(exam, stress) - time cost.

    Reads P(pass | m1, m2, m3, s) from the model's ExamSuccess CPD, so hand-crafted
    and learned models both work. The mastery marginals are treated as independent
    (the approximation stated in docs/MODEL.md §5).
    """
    mastery, p_stress_high = apply_action(post, action, days_state)
    p_stress = {"low": 1.0 - p_stress_high, "high": p_stress_high}
    eu = 0.0
    for combo in itertools.product(("low", "high"), repeat=len(cfg.CONCEPTS)):
        p_combo = 1.0
        for concept, state in zip(cfg.CONCEPTS, combo):
            p_high = mastery[concept]
            p_combo *= p_high if state == "high" else 1.0 - p_high
        for stress, p_s in p_stress.items():
            p_pass = p_pass_given(model, combo, stress)
            eu += p_combo * p_s * (p_pass * utility("pass", stress) + (1.0 - p_pass) * utility("fail", stress))
    return eu - cfg.TIME_COST_PER_HOUR * action.hours


def decide(model: BayesNet, post: Posteriors, days_state: str) -> Decision:
    """Compute EU of every action in cfg.ACTIONS and return the argmax."""
    eus = {a.key: expected_utility(model, post, a, days_state) for a in cfg.ACTIONS}
    best = max(cfg.ACTIONS, key=lambda a: eus[a.key])
    return Decision(best, eus, weakest_concept(post), post)
