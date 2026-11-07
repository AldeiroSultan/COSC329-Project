"""Simulated student types for the demo (branch MF-00006). See docs/MODEL.md §6."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, timedelta

from study_planner import config as cfg
from study_planner.calendar_api import CalendarClient, Exam, InMemoryCalendarClient
from study_planner.inference import StudentEvidence, query
from study_planner.learning import build_learned_model
from study_planner.network import BayesNet, build_handcrafted_model
from study_planner.planner import StudyPlanner

DEMO_EXAM_NAME = "COSC 329 Final Exam"
QUIZ_PASS_LEVEL = 0.5   # a practice quiz comes back 'high' once true mastery reaches this


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


def get_model(handcrafted: bool = False) -> BayesNet:
    """The learned model (MF-00003) if the dataset exists, otherwise the hand-crafted one."""
    if handcrafted or not cfg.STUDENTS_CSV.exists():
        return build_handcrafted_model()
    return build_learned_model()


def simulate_two_weeks(
    scenario: Scenario,
    model: BayesNet | None = None,
    start_days: int = 14,
    calendar: CalendarClient | None = None,
    today: date | None = None,
) -> list[dict]:
    """Run the planner once per day as the exam approaches.

    The student has a hidden *true mastery* per concept, starting at the network's
    belief for the scenario. Each day:
      1. the planner sees the evidence (difficulty, days left, latest practice quizzes),
         decides, and writes the session to `calendar`;
      2. the student studies, and true mastery rises by the action's boost:
         m' = m + boost * (1 - m) on the targeted concepts. This real learning does
         not depend on how close the exam is; urgency only affects how the planner
         values studying;
      3. tomorrow's practice quizzes come back 'high' once true mastery >= 0.5, and
         that new evidence changes the next decision.
    Quizzes are only taken on concepts the scenario gives a quiz result for, and sleep
    stays as in the scenario. Fully deterministic.

    Returns one row per day: day (1-based), date, days_left, action, hours, eu (of the
    chosen action), p_pass (P(pass | evidence), before acting), mastery (true), quiz.
    """
    model = model if model is not None else get_model()
    calendar = calendar if calendar is not None else InMemoryCalendarClient()
    today = today or date.today()
    exam = Exam(DEMO_EXAM_NAME, today + timedelta(days=start_days))
    planner = StudyPlanner(model, calendar)

    start = replace(scenario.evidence, days_until_exam=start_days)
    mastery = dict(query(model, start).p_mastery_high)
    quiz = {c: s for c, s in scenario.evidence.quiz.items() if s is not None}
    quizzed = list(quiz)

    rows = []
    for day in range(1, start_days + 1):
        result = planner.plan_today(today + timedelta(days=day - 1), exam, replace(start, quiz=dict(quiz)))
        action, decision = result.decision.best, result.decision
        rows.append({
            "day": day,
            "date": today + timedelta(days=day - 1),
            "days_left": result.evidence.days_until_exam,
            "action": action.key,
            "hours": action.hours,
            "eu": decision.expected_utility[action.key],
            "p_pass": decision.posteriors.p_pass,
            "mastery": dict(mastery),
            "quiz": dict(quiz),
        })

        targets = cfg.CONCEPTS if action.target == "all" else [decision.target_concept]
        for c in targets:
            mastery[c] += action.mastery_boost * (1.0 - mastery[c])
        quiz = {c: "high" if mastery[c] >= QUIZ_PASS_LEVEL else "low" for c in quizzed}
    return rows
