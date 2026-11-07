"""Glue: calendar exams -> evidence -> decision -> calendar events (branch MF-00005)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta

from study_planner import config as cfg
from study_planner.calendar_api.base import CalendarClient, CalendarEvent, Exam
from study_planner.decision import Decision, decide
from study_planner.inference import StudentEvidence, query
from study_planner.network import BayesNet

LAST_END_HOUR = 22          # study sessions must end by 22:00
SLOT_STEP = timedelta(minutes=30)
EXAM_LOOKAHEAD_DAYS = 60


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

    # ------------------------------------------------------------------ scheduling helpers
    def find_slot(self, day: date, hours: float) -> datetime:
        """Earliest free start time for a `hours`-long session on `day`.

        Tries every 30 minutes from DEFAULT_STUDY_START_HOUR until LAST_END_HOUR and
        returns the first slot that overlaps no existing event. If the day is too full,
        falls back to the default start time (the student can move it).
        """
        default = datetime.combine(day, time(cfg.DEFAULT_STUDY_START_HOUR))
        length = timedelta(hours=hours)
        latest_end = datetime.combine(day, time(LAST_END_HOUR))
        busy = self.calendar.list_events(datetime.combine(day, time.min), datetime.combine(day, time.min) + timedelta(days=1))
        start = default
        while start + length <= latest_end:
            if not any(event.overlaps(start, start + length) for event in busy):
                return start
            start += SLOT_STEP
        return default

    def _describe(self, exam: Exam, evidence: StudentEvidence, decision: Decision) -> str:
        post = decision.posteriors
        lines = [
            f"Exam: {exam.course} on {exam.exam_date:%a %b %d} ({evidence.days_until_exam} days left)",
            f"P(pass) if nothing changes: {post.p_pass:.0%}; P(high stress): {post.p_stress_high:.0%}",
            "Mastery: " + ", ".join(f"{c} {p:.0%}" for c, p in post.p_mastery_high.items()),
        ]
        if decision.best.target == "weakest":
            lines.append(f"Focus on the weakest concept: {decision.target_concept}")
        lines.append("Expected utility: " + ", ".join(f"{k} {v:.1f}" for k, v in decision.expected_utility.items()))
        return "\n".join(lines)

    def _plan(self, today: date, exam: Exam, evidence: StudentEvidence, clear: bool) -> PlanResult:
        days_left = (exam.exam_date - today).days
        if days_left < 0:
            raise ValueError(f"Exam {exam.course!r} on {exam.exam_date} is already in the past")
        evidence = replace(evidence, days_until_exam=days_left)

        decision = decide(self.model, query(self.model, evidence), evidence.days_state)

        # Replace any earlier plan for today instead of stacking sessions; for a rest
        # day this is the whole action ("clear the calendar").
        cleared = self.calendar.clear_planner_events(today) if clear else 0
        created: list[CalendarEvent] = []
        if decision.best.hours > 0:
            start = self.find_slot(today, decision.best.hours)
            created.append(self.calendar.create_event(CalendarEvent(
                summary=f"{cfg.EVENT_TAG} {decision.best.label}",
                start=start,
                end=start + timedelta(hours=decision.best.hours),
                description=self._describe(exam, evidence, decision),
            )))
        return PlanResult(exam, evidence, decision, created, cleared)

    # ------------------------------------------------------------------ public API
    def plan_today(self, today: date, exam: Exam, evidence: StudentEvidence) -> PlanResult:
        """Decide today's action for one exam and write it to the calendar.

        days_until_exam is taken from the exam date, whatever `evidence` says.
        """
        return self._plan(today, exam, evidence, clear=True)

    def plan_upcoming(self, today: date, evidence_by_course: dict[str, StudentEvidence]) -> list[PlanResult]:
        """Plan every upcoming exam found in the calendar, nearest first.

        Exams are matched to evidence by course name (event title, case-insensitive);
        use the key "*" for evidence that applies to any exam. Exams with no matching
        evidence are skipped. Today's planner sessions are cleared once up front, then
        each exam gets its own decision and session.
        """
        lookup = {name.lower(): ev for name, ev in evidence_by_course.items()}
        start = datetime.combine(today, time.min)
        exams = self.calendar.list_exams(start, start + timedelta(days=EXAM_LOOKAHEAD_DAYS))

        results: list[PlanResult] = []
        cleared = self.calendar.clear_planner_events(today)
        for exam in exams:
            evidence = lookup.get(exam.course.lower(), lookup.get("*"))
            if evidence is None:
                continue
            result = self._plan(today, exam, evidence, clear=False)
            results.append(result)
        if results:
            results[0].events_cleared = cleared
        return results
