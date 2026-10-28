"""Calendar abstraction shared by Google, .ics and in-memory backends (branch MF-00005)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime

from study_planner import config as cfg


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


@dataclass
class Exam:
    course: str
    exam_date: date


class CalendarClient(ABC):
    @abstractmethod
    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]: ...

    @abstractmethod
    def create_event(self, event: CalendarEvent) -> CalendarEvent: ...

    @abstractmethod
    def delete_event(self, event: CalendarEvent) -> None: ...

    def list_exams(self, start: datetime, end: datetime) -> list[Exam]:
        """Find exams: events whose summary contains 'exam' or 'midterm' (case-insensitive).

        TODO(MF-00005)
        """
        raise NotImplementedError("MF-00005")

    def clear_planner_events(self, day: date) -> int:
        """Delete only [BayesPlanner] events on `day`; return how many were removed.

        TODO(MF-00005)
        """
        raise NotImplementedError("MF-00005")
