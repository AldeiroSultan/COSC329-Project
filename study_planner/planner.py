"""Glue: calendar exams -> evidence -> decision -> calendar events (branch MF-00005)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from study_planner.calendar_api.base import CalendarClient, CalendarEvent, Exam
from study_planner.decision import Decision
from study_planner.inference import StudentEvidence
from study_planner.network import BayesNet


@dataclass
class PlanResult:
    exam: Exam
    evidence: StudentEvidence
    decision: Decision
    events_created: list[CalendarEvent]
    events_cleared: int


class StudyPlanner:
    def __init__(self, model: BayesNet, calendar: CalendarClient) -> None:
        self.model = model
        self.calendar = calendar

    def plan_today(self, today: date, exam: Exam, evidence: StudentEvidence) -> PlanResult:
        """Decide today's action for one exam and write it to the calendar.

        TODO(MF-00005):
        1. evidence.days_until_exam = (exam.exam_date - today).days
        2. inference.query -> decision.decide
        3. 'rest' -> calendar.clear_planner_events(today)
           otherwise create a '[BayesPlanner] <label>' event at cfg.DEFAULT_STUDY_START_HOUR
           lasting action.hours; 'focused' names the target concept in the description.
        """
        raise NotImplementedError("MF-00005")

    def plan_upcoming(self, today: date, evidence_by_course: dict[str, StudentEvidence]) -> list[PlanResult]:
        """Run plan_today for the nearest exam found in the calendar.

        TODO(MF-00005)
        """
        raise NotImplementedError("MF-00005")
