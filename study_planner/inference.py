"""Inference queries with pgmpy VariableElimination (branch MF-00004).

Query variables (docs/MODEL.md §3): Mastery_C1..3, Stress, ExamSuccess.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from study_planner import config as cfg
from study_planner.network import BayesNet


@dataclass
class StudentEvidence:
    """What we know about a student today. None = not observed."""

    difficulty: dict[str, str]                       # concept -> easy/medium/hard
    days_until_exam: int
    quiz: dict[str, str | None] = field(default_factory=dict)  # concept -> low/high
    sleep: str | None = None                          # poor/good

    def to_pgmpy(self) -> dict[str, str]:
        """Convert to the {node: state} dict pgmpy expects (skip unobserved).

        TODO(MF-00004)
        """
        raise NotImplementedError("MF-00004")


@dataclass
class Posteriors:
    p_mastery_high: dict[str, float]   # concept -> P(Mastery=high | e)
    p_stress_high: float               # P(Stress=high | e)
    p_pass: float                      # P(ExamSuccess=pass | e)


def query(model: BayesNet, evidence: StudentEvidence) -> Posteriors:
    """Run VariableElimination for every query variable.

    TODO(MF-00004)
    """
    raise NotImplementedError("MF-00004")
