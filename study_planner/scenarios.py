"""Simulated student types for the demo (branch MF-00006). See docs/MODEL.md §6."""

from __future__ import annotations

from dataclasses import dataclass

from study_planner.inference import StudentEvidence


@dataclass
class Scenario:
    name: str
    description: str
    evidence: StudentEvidence
    expected_action: str


SCENARIOS: list[Scenario] = [
    Scenario(
        "struggling",
        "All concepts hard, every practice quiz low, exam in 2 days.",
        StudentEvidence({"C1": "hard", "C2": "hard", "C3": "hard"}, 2, {"C1": "low", "C2": "low", "C3": "low"}),
        "intense",
    ),
    Scenario(
        "advanced",
        "All concepts easy, every quiz high, exam in 14 days.",
        StudentEvidence({"C1": "easy", "C2": "easy", "C3": "easy"}, 14, {"C1": "high", "C2": "high", "C3": "high"}),
        "rest",
    ),
    Scenario(
        "one_weak_spot",
        "Two easy concepts, one hard concept with a low quiz, exam in 7 days.",
        StudentEvidence({"C1": "easy", "C2": "easy", "C3": "hard"}, 7, {"C3": "low"}),
        "focused",
    ),
    Scenario(
        "average_early",
        "Medium concepts, no quizzes yet, slept well, exam in 18 days.",
        StudentEvidence({"C1": "medium", "C2": "medium", "C3": "medium"}, 18, {}, sleep="good"),
        "light",
    ),
    Scenario(
        "burnt_out",
        "Medium concepts, quizzes fine, slept poorly, exam in 3 days.",
        StudentEvidence({"C1": "medium", "C2": "medium", "C3": "medium"}, 3,
                        {"C1": "high", "C2": "high", "C3": "high"}, sleep="poor"),
        "light",
    ),
]


def simulate_two_weeks(scenario: Scenario, start_days: int = 14) -> list[dict]:
    """Run the planner once per day as the exam approaches.

    After each study day, update the student's quiz evidence (e.g. a weak concept
    that was studied flips to 'high' with some probability) so the plan adapts.
    Returns one row per day: {day, days_left, action, eu, p_pass}.

    TODO(MF-00006)
    """
    raise NotImplementedError("MF-00006")
