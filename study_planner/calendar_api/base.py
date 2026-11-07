"""Calendar abstraction shared by Google, .ics and in-memory backends (branch MF-00005).

All datetimes handled by the planner are *naive local time* in cfg.TIMEZONE.
Backends convert to and from timezone-aware values at their own boundary.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from study_planner import config as cfg

EXAM_KEYWORDS = ("exam", "midterm", "final")


def local_tz() -> ZoneInfo:
    return ZoneInfo(cfg.TIMEZONE)


def to_local_naive(value: date | datetime) -> datetime:
    """Normalise a date / aware datetime / naive datetime to naive local time."""
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(local_tz()).replace(tzinfo=None)
        return value
    return datetime.combine(value, time.min)  # all-day event -> midnight


def to_local_aware(value: datetime) -> datetime:
    """Attach the planner's time zone to a naive local datetime."""
    return value.replace(tzinfo=local_tz())


@dataclass
class CalendarEvent:
    summary: str
    start: datetime
    end: datetime
    description: str = ""
    event_id: str | None = None

    @property
    def is_planner_event(self) -> bool:
        """Only events created by the planner may ever be deleted."""
        return self.summary.startswith(cfg.EVENT_TAG)

    def overlaps(self, start: datetime, end: datetime) -> bool:
        return self.start < end and self.end > start


@dataclass
class Exam:
    course: str
    exam_date: date


class CalendarClient(ABC):
    @abstractmethod
    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        """Events overlapping [start, end), sorted by start time."""

    @abstractmethod
    def create_event(self, event: CalendarEvent) -> CalendarEvent:
        """Store the event and return it with its event_id set."""

    @abstractmethod
    def delete_event(self, event: CalendarEvent) -> None:
        """Remove the event. Backends must refuse anything that is not a planner event."""

    def list_exams(self, start: datetime, end: datetime) -> list[Exam]:
        """Find exams: events whose summary contains 'exam', 'midterm' or 'final'.

        Planner events (which may mention the exam in their title) are ignored.
        Returned in date order.
        """
        exams = []
        for event in self.list_events(start, end):
            title = event.summary.lower()
            if event.is_planner_event or not any(word in title for word in EXAM_KEYWORDS):
                continue
            exams.append(Exam(event.summary, event.start.date()))
        return sorted(exams, key=lambda e: e.exam_date)

    def clear_planner_events(self, day: date) -> int:
        """Delete only [BayesPlanner] events on `day`; return how many were removed."""
        start = datetime.combine(day, time.min)
        removed = 0
        for event in self.list_events(start, start + timedelta(days=1)):
            if event.is_planner_event:
                self.delete_event(event)
                removed += 1
        return removed
