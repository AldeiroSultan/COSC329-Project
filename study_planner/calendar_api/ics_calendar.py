"""Offline backend: writes events to a .ics file importable into any calendar (branch MF-00005)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from study_planner.calendar_api.base import CalendarEvent
from study_planner.calendar_api.memory_calendar import InMemoryCalendarClient


class IcsCalendarClient(InMemoryCalendarClient):
    """Keeps events in memory and writes them with the `icalendar` package on save()."""

    def __init__(self, path: Path, events: list[CalendarEvent] | None = None) -> None:
        super().__init__(events)
        self.path = path

    def save(self) -> Path:
        """Write all events to self.path.

        TODO(MF-00005): icalendar.Calendar + Event (summary, dtstart, dtend, description, uid).
        """
        raise NotImplementedError("MF-00005")

    @classmethod
    def load(cls, path: Path) -> "IcsCalendarClient":
        """Read an existing .ics (e.g. exported from Google/Outlook) to pick up exam events.

        TODO(MF-00005)
        """
        raise NotImplementedError("MF-00005")
