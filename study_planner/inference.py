"""Inference queries with pgmpy VariableElimination (branch MF-00004).

Query variables (docs/MODEL.md §3): Mastery_C1..3, Stress, ExamSuccess.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pgmpy.inference import VariableElimination

from study_planner import config as cfg
from study_planner.network import BayesNet


@dataclass
class StudentEvidence:
    """What we know about a student today. None = not observed."""

    difficulty: dict[str, str]                       # concept -> easy/medium/hard
    days_until_exam: int
    quiz: dict[str, str | None] = field(default_factory=dict)  # concept -> low/high
    sleep: str | None = None                          # poor/good

    @property
    def days_state(self) -> str:
        """DaysLeft bucket (few / some / many) for days_until_exam."""
        return cfg.days_bucket(self.days_until_exam)

    def to_pgmpy(self) -> dict[str, str]:
        """Convert to the {node: state} dict pgmpy expects (skip unobserved)."""
        evidence = {cfg.NODE_DIFFICULTY[c]: state for c, state in self.difficulty.items()}
        evidence[cfg.NODE_DAYS] = self.days_state
        for concept, state in self.quiz.items():
            if state is not None:
                evidence[cfg.NODE_QUIZ[concept]] = state
        if self.sleep is not None:
            evidence[cfg.NODE_SLEEP] = self.sleep
        return evidence


@dataclass
class Posteriors:
    p_mastery_high: dict[str, float]   # concept -> P(Mastery=high | e)
    p_stress_high: float               # P(Stress=high | e)
    p_pass: float                      # P(ExamSuccess=pass | e)


def _marginal(engine: VariableElimination, variable: str, state: str, evidence: dict[str, str]) -> float:
    """P(variable = state | evidence) by variable elimination."""
    factor = engine.query([variable], evidence=evidence, show_progress=False)
    return float(factor.get_value(**{variable: state}))


def query(model: BayesNet, evidence: StudentEvidence) -> Posteriors:
    """Run VariableElimination for every query variable (docs/MODEL.md §3)."""
    engine = VariableElimination(model)
    e = evidence.to_pgmpy()
    return Posteriors(
        p_mastery_high={c: _marginal(engine, cfg.NODE_MASTERY[c], "high", e) for c in cfg.CONCEPTS},
        p_stress_high=_marginal(engine, cfg.NODE_STRESS, "high", e),
        p_pass=_marginal(engine, cfg.NODE_EXAM, "pass", e),
    )
