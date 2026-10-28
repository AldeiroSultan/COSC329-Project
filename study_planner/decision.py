"""Action effects, utility and expected-utility decision (branch MF-00004).

See docs/MODEL.md §4-5.
"""

from __future__ import annotations

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


def apply_action(post: Posteriors, action: cfg.Action, days_state: str) -> tuple[dict[str, float], float]:
    """Return (P'(Mastery_Ci=high) per concept, P'(Stress=high)) after the action.

    TODO(MF-00004): boost = action.mastery_boost * cfg.URGENCY[days_state];
    p' = p + boost * (1 - p) on targeted concepts; stress clipped to [0, 1].
    """
    raise NotImplementedError("MF-00004")


def expected_utility(model: BayesNet, post: Posteriors, action: cfg.Action, days_state: str) -> float:
    """EU(a) = sum over exam, stress of P'_a(exam, stress) * U(exam, stress) - time cost.

    TODO(MF-00004): read P(pass | m1, m2, m3, s) from the model's ExamSuccess CPD so
    hand-crafted and learned models both work.
    """
    raise NotImplementedError("MF-00004")


def decide(model: BayesNet, post: Posteriors, days_state: str) -> Decision:
    """Compute EU of every action in cfg.ACTIONS and return the argmax.

    TODO(MF-00004)
    """
    raise NotImplementedError("MF-00004")
