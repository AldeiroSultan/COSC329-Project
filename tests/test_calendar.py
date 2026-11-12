from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from study_planner import config as cfg
from study_planner.calendar_api import (
    CalendarEvent,
    Exam,
    IcsCalendarClient,
    InMemoryCalendarClient,
)
from study_planner.calendar_api.google_calendar import GoogleCalendarClient

DAY = date(2026, 11, 5)
START, END = datetime(2026, 11, 1), datetime(2026, 12, 1)


def event(summary, hour, hours=1, day=5):
    return CalendarEvent(summary, datetime(2026, 11, day, hour), datetime(2026, 11, day, hour + hours))


def planner_event(hour, **kwargs):
    return event(f"{cfg.EVENT_TAG} Study", hour, **kwargs)


# Offsets come from the time zone database so the tests do not hard-code PST/PDT.
def local_iso(naive):
    return naive.replace(tzinfo=ZoneInfo(cfg.TIMEZONE)).isoformat()


def utc_to_local(naive_utc):
    return naive_utc.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(cfg.TIMEZONE)).replace(tzinfo=None)


# ------------------------------------------------------------------ in-memory
def test_create_assigns_id_and_list_sorts_and_filters_by_overlap():
    cal = InMemoryCalendarClient()
    late = cal.create_event(event("Late", 15))
    cal.create_event(event("Early", 9))
    cal.create_event(event("Other day", 9, day=7))
    assert late.event_id
    assert [e.summary for e in cal.list_events(datetime(2026, 11, 5), datetime(2026, 11, 6))] == ["Early", "Late"]
    # an event that only touches the window edge does not overlap it
    assert cal.list_events(datetime(2026, 11, 5, 10), datetime(2026, 11, 5, 15)) == []


def test_clear_only_removes_planner_events():
    mine = planner_event(10)
    theirs = event("Dentist", 14)
    cal = InMemoryCalendarClient([mine, theirs])
    assert cal.clear_planner_events(DAY) == 1
    assert [e.summary for e in cal.events] == ["Dentist"]


def test_clear_leaves_other_days_alone():
    cal = InMemoryCalendarClient([planner_event(10), planner_event(10, day=6)])
    assert cal.clear_planner_events(DAY) == 1
    assert len(cal.events) == 1 and cal.events[0].start.day == 6


def test_delete_refuses_events_the_planner_did_not_create():
    cal = InMemoryCalendarClient([event("Dentist", 14)])
    with pytest.raises(PermissionError):
        cal.delete_event(cal.events[0])
    assert len(cal.events) == 1


def test_list_exams_finds_exams_in_date_order_and_ignores_the_rest():
    cal = InMemoryCalendarClient([
        event("COSC 329 Final Exam", 9, day=20),
        event("MATH midterm", 9, day=8),
        event("Dentist", 14),
        planner_event(10),
        CalendarEvent(f"{cfg.EVENT_TAG} Light review for the exam", datetime(2026, 11, 6, 10), datetime(2026, 11, 6, 11)),
    ])
    assert cal.list_exams(START, END) == [
        Exam("MATH midterm", date(2026, 11, 8)),
        Exam("COSC 329 Final Exam", date(2026, 11, 20)),
    ]


# ------------------------------------------------------------------ .ics
def test_ics_save_and_load_round_trip(tmp_path):
    path = tmp_path / "out" / "plan.ics"
    cal = IcsCalendarClient(path)
    created = cal.create_event(CalendarEvent(f"{cfg.EVENT_TAG} Light review", datetime(2026, 11, 5, 10), datetime(2026, 11, 5, 11),
                                             "Exam in 5 days\nP(pass): 54%"))
    assert cal.save() == path
    assert b"TZID=America/Vancouver" in path.read_bytes()

    loaded = IcsCalendarClient.load(path)
    assert len(loaded.events) == 1
    got = loaded.events[0]
    assert (got.summary, got.start, got.end, got.description, got.event_id) == (
        created.summary, created.start, created.end, created.description, created.event_id
    )


def test_ics_load_reads_all_day_and_utc_events(tmp_path):
    path = tmp_path / "export.ics"
    # write bytes: text mode on Windows would turn \r\n into \r\r\n
    path.write_bytes((
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//test//EN\r\n"
        "BEGIN:VEVENT\r\nUID:a\r\nDTSTAMP:20261101T000000Z\r\nDTSTART;VALUE=DATE:20261110\r\nSUMMARY:STAT 251 Midterm Exam\r\nEND:VEVENT\r\n"
        "BEGIN:VEVENT\r\nUID:b\r\nDTSTAMP:20261101T000000Z\r\nDTSTART:20261109T180000Z\r\nDTEND:20261109T190000Z\r\nSUMMARY:Lab\r\nEND:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    ).encode("utf-8"))
    cal = IcsCalendarClient.load(path)
    assert cal.list_exams(START, END) == [Exam("STAT 251 Midterm Exam", date(2026, 11, 10))]
    lab = next(e for e in cal.events if e.summary == "Lab")
    assert lab.start == utc_to_local(datetime(2026, 11, 9, 18))
    assert lab.end - lab.start == timedelta(hours=1)


# ------------------------------------------------------------------ Google (fake service)
class FakeRequest:
    def __init__(self, result):
        self.result = result

    def execute(self):
        return self.result


class FakeEvents:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def list(self, **kwargs):
        self.calls.append(("list", kwargs))
        return FakeRequest(self.pages[len(self.calls) - 1])

    def insert(self, **kwargs):
        self.calls.append(("insert", kwargs))
        return FakeRequest({"id": "g123"})

    def delete(self, **kwargs):
        self.calls.append(("delete", kwargs))
        return FakeRequest(None)


class FakeService:
    def __init__(self, pages=()):
        self._events = FakeEvents(list(pages))

    def events(self):
        return self._events


def test_google_create_event_sends_local_time_zone():
    service = FakeService()
    client = GoogleCalendarClient(service=service)
    created = client.create_event(planner_event(10, hours=5))
    (name, call), = service.events().calls
    assert name == "insert" and call["calendarId"] == "primary"
    assert call["body"]["start"] == {"dateTime": local_iso(datetime(2026, 11, 5, 10)), "timeZone": "America/Vancouver"}
    assert call["body"]["end"]["dateTime"] == local_iso(datetime(2026, 11, 5, 15))
    assert call["body"]["summary"].startswith(cfg.EVENT_TAG)
    assert created.event_id == "g123"


def test_google_list_events_parses_timed_all_day_and_paged_results():
    pages = [
        {"items": [{"id": "1", "summary": "Lab", "start": {"dateTime": "2026-11-09T18:00:00Z"}, "end": {"dateTime": "2026-11-09T19:00:00Z"}}],
         "nextPageToken": "next"},
        {"items": [{"id": "2", "summary": "COSC 329 Exam", "start": {"date": "2026-11-10"}, "end": {"date": "2026-11-11"}}]},
    ]
    service = FakeService(pages)
    client = GoogleCalendarClient(service=service)
    events = client.list_events(datetime(2026, 11, 9), datetime(2026, 11, 12))
    assert [(e.summary, e.start, e.event_id) for e in events] == [
        ("Lab", utc_to_local(datetime(2026, 11, 9, 18)), "1"),
        ("COSC 329 Exam", datetime(2026, 11, 10), "2"),
    ]
    assert service.events().calls[1][1]["pageToken"] == "next"
    assert service.events().calls[0][1]["singleEvents"] is True


def test_google_events_feed_exam_detection():
    page = {"items": [{"id": "2", "summary": "COSC 329 Exam", "start": {"date": "2026-11-10"}, "end": {"date": "2026-11-11"}}]}
    client = GoogleCalendarClient(service=FakeService([page]))
    assert client.list_exams(datetime(2026, 11, 9), datetime(2026, 11, 12)) == [Exam("COSC 329 Exam", date(2026, 11, 10))]


def test_google_delete_only_planner_events():
    service = FakeService()
    client = GoogleCalendarClient(service=service)
    with pytest.raises(PermissionError):
        client.delete_event(CalendarEvent("Dentist", datetime(2026, 11, 5, 14), datetime(2026, 11, 5, 15), event_id="x"))
    assert service.events().calls == []
    client.delete_event(CalendarEvent(f"{cfg.EVENT_TAG} Study", datetime(2026, 11, 5, 10), datetime(2026, 11, 5, 11), event_id="g9"))
    assert service.events().calls == [("delete", {"calendarId": "primary", "eventId": "g9"})]


def test_google_without_credentials_gives_a_helpful_error(tmp_path):
    # Explicit paths keep this test independent of a developer's saved OAuth token.
    # Patching TOKEN_FILE cannot change a default argument bound at import time.
    with pytest.raises(FileNotFoundError, match="GOOGLE_SETUP"):
        GoogleCalendarClient._authenticate(
            credentials_file=tmp_path / "missing.json",
            token_file=tmp_path / "token.json",
        )
