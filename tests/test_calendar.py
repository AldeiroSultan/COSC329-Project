from datetime import date, datetime

import pytest

from study_planner import config as cfg
from study_planner.calendar_api import CalendarEvent, InMemoryCalendarClient

pytestmark = pytest.mark.skip(reason="implement in MF-00005")


def test_clear_only_removes_planner_events():
    mine = CalendarEvent(f"{cfg.EVENT_TAG} Study", datetime(2026, 11, 5, 10), datetime(2026, 11, 5, 11))
    theirs = CalendarEvent("Dentist", datetime(2026, 11, 5, 14), datetime(2026, 11, 5, 15))
    cal = InMemoryCalendarClient([mine, theirs])
    assert cal.clear_planner_events(date(2026, 11, 5)) == 1
    assert [e.summary for e in cal.events] == ["Dentist"]
