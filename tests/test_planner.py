from dataclasses import replace
from datetime import date, datetime, timedelta

import pytest

from study_planner import config as cfg
from study_planner.calendar_api import CalendarEvent, Exam, IcsCalendarClient, InMemoryCalendarClient
from study_planner.network import build_handcrafted_model
from study_planner.planner import StudyPlanner
from study_planner.scenarios import SCENARIOS

TODAY = date(2026, 11, 9)
STRUGGLING, ADVANCED, WEAK_SPOT = SCENARIOS[0], SCENARIOS[1], SCENARIOS[2]


@pytest.fixture(scope="module")
def model():
    return build_handcrafted_model()


def exam_in(days, course="COSC 329 Final Exam"):
    return Exam(course, TODAY + timedelta(days=days))


def planner_events(cal):
    return [e for e in cal.events if e.is_planner_event]


def busy(start_hour, end_hour):
    return CalendarEvent("Class", datetime(2026, 11, 9, start_hour), datetime(2026, 11, 9, end_hour))


def test_struggling_student_gets_the_five_hour_block(model):
    cal = InMemoryCalendarClient()
    result = StudyPlanner(model, cal).plan_today(TODAY, exam_in(2), STRUGGLING.evidence)
    assert result.decision.best.key == "intense"
    (session,) = planner_events(cal)
    assert session.summary.startswith(cfg.EVENT_TAG)
    assert (session.start, session.end) == (datetime(2026, 11, 9, 10), datetime(2026, 11, 9, 15))
    assert result.events_created == [session]
    assert "Exam: COSC 329 Final Exam" in session.description and "2 days left" in session.description


def test_days_until_exam_comes_from_the_calendar_not_the_evidence(model):
    cal = InMemoryCalendarClient()
    stale = replace(STRUGGLING.evidence, days_until_exam=99)
    result = StudyPlanner(model, cal).plan_today(TODAY, exam_in(2), stale)
    assert result.evidence.days_until_exam == 2
    assert result.decision.best.key == "intense"


def test_rest_day_clears_planner_sessions_but_not_the_students_own_events(model):
    cal = InMemoryCalendarClient([
        CalendarEvent(f"{cfg.EVENT_TAG} Old plan", datetime(2026, 11, 9, 10), datetime(2026, 11, 9, 11)),
        busy(13, 14),
    ])
    result = StudyPlanner(model, cal).plan_today(TODAY, exam_in(14), ADVANCED.evidence)
    assert result.decision.best.key == "rest"
    assert result.events_created == [] and result.events_cleared == 1
    assert [e.summary for e in cal.events] == ["Class"]


def test_running_twice_replaces_instead_of_stacking(model):
    cal = InMemoryCalendarClient()
    planner = StudyPlanner(model, cal)
    planner.plan_today(TODAY, exam_in(2), STRUGGLING.evidence)
    again = planner.plan_today(TODAY, exam_in(2), STRUGGLING.evidence)
    assert len(planner_events(cal)) == 1
    assert again.events_cleared == 1


def test_changed_circumstances_change_the_calendar(model):
    cal = InMemoryCalendarClient()
    planner = StudyPlanner(model, cal)
    planner.plan_today(TODAY, exam_in(2), STRUGGLING.evidence)
    planner.plan_today(TODAY, exam_in(14), ADVANCED.evidence)
    assert planner_events(cal) == []


def test_focused_session_names_the_weak_concept(model):
    cal = InMemoryCalendarClient()
    result = StudyPlanner(model, cal).plan_today(TODAY, exam_in(7), WEAK_SPOT.evidence)
    assert result.decision.best.key == "focused"
    (session,) = planner_events(cal)
    assert session.end - session.start == timedelta(hours=2.5)
    assert "weakest concept: C3" in session.description


def test_session_avoids_existing_events(model):
    cal = InMemoryCalendarClient([busy(10, 12), busy(13, 14)])
    planner = StudyPlanner(model, cal)
    assert planner.find_slot(TODAY, 1) == datetime(2026, 11, 9, 12)
    assert planner.find_slot(TODAY, 5) == datetime(2026, 11, 9, 14)
    result = planner.plan_today(TODAY, exam_in(2), STRUGGLING.evidence)
    assert result.events_created[0].start == datetime(2026, 11, 9, 14)
    assert result.events_created[0].end == datetime(2026, 11, 9, 19)


def test_fully_booked_day_falls_back_to_the_default_start(model):
    cal = InMemoryCalendarClient([busy(8, 23)])
    assert StudyPlanner(model, cal).find_slot(TODAY, 5) == datetime(2026, 11, 9, cfg.DEFAULT_STUDY_START_HOUR)


def test_exam_in_the_past_is_rejected(model):
    with pytest.raises(ValueError, match="past"):
        StudyPlanner(model, InMemoryCalendarClient()).plan_today(TODAY, exam_in(-1), STRUGGLING.evidence)


def test_plan_upcoming_handles_each_exam_nearest_first(model):
    cal = InMemoryCalendarClient([
        CalendarEvent("Bio Final Exam", datetime(2026, 11, 23, 9), datetime(2026, 11, 23, 11)),
        CalendarEvent("STAT Midterm", datetime(2026, 11, 11, 9), datetime(2026, 11, 11, 10)),
        CalendarEvent("Old Exam", datetime(2026, 11, 2, 9), datetime(2026, 11, 2, 10)),
        busy(9, 10),
    ])
    evidence = {"stat midterm": STRUGGLING.evidence, "*": ADVANCED.evidence}
    results = StudyPlanner(model, cal).plan_upcoming(TODAY, evidence)
    assert [r.exam.course for r in results] == ["STAT Midterm", "Bio Final Exam"]
    assert [r.decision.best.key for r in results] == ["intense", "rest"]
    assert len(planner_events(cal)) == 1  # the rest day for Bio did not wipe STAT's session


def test_plan_upcoming_skips_exams_without_evidence_and_clears_old_sessions_once(model):
    cal = InMemoryCalendarClient([
        CalendarEvent("Bio Final Exam", datetime(2026, 11, 23, 9), datetime(2026, 11, 23, 11)),
        CalendarEvent(f"{cfg.EVENT_TAG} Yesterday's plan", datetime(2026, 11, 9, 16), datetime(2026, 11, 9, 17)),
    ])
    assert StudyPlanner(model, cal).plan_upcoming(TODAY, {"COSC 329 Final Exam": STRUGGLING.evidence}) == []
    assert planner_events(cal) == []  # stale planner session was still cleared


def test_plan_upcoming_with_no_exams(model):
    assert StudyPlanner(model, InMemoryCalendarClient()).plan_upcoming(TODAY, {"*": ADVANCED.evidence}) == []


def test_planner_output_can_be_exported_to_ics(model, tmp_path):
    cal = IcsCalendarClient(tmp_path / "plan.ics")
    StudyPlanner(model, cal).plan_today(TODAY, exam_in(2), STRUGGLING.evidence)
    cal.save()
    reloaded = IcsCalendarClient.load(tmp_path / "plan.ics")
    (session,) = [e for e in reloaded.events if e.is_planner_event]
    assert (session.start, session.end) == (datetime(2026, 11, 9, 10), datetime(2026, 11, 9, 15))
