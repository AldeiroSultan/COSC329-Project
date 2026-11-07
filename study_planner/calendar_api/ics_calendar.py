"""Offline backend: writes events to a .ics file importable into any calendar (branch MF-00005)."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from icalendar import Calendar, Event

from study_planner.calendar_api.base import CalendarEvent, to_local_aware, to_local_naive
from study_planner.calendar_api.memory_calendar import InMemoryCalendarClient


class IcsCalendarClient(InMemoryCalendarClient):
    """Keeps events in memory and writes them with the `icalendar` package on save().

    Nothing touches the file until save() is called.
    """

    def __init__(self, path: Path, events: list[CalendarEvent] | None = None) -> None:
        super().__init__(events)
        self.path = Path(path)

    def save(self) -> Path:
        """Write all events to self.path (times carry the planner's time zone)."""
        cal = Calendar()
        cal.add("prodid", "-//COSC329 Bayesian Study Planner//EN")
        cal.add("version", "2.0")
        for event in sorted(self.events, key=lambda e: e.start):
            item = Event()
            item.add("uid", event.event_id)
            item.add("summary", event.summary)
            item.add("dtstart", to_local_aware(event.start))
            item.add("dtend", to_local_aware(event.end))
            item.add("dtstamp", datetime.now().astimezone())
            if event.description:
                item.add("description", event.description)
            cal.add_component(item)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(cal.to_ical())
        return self.path

    @classmethod
    def load(cls, path: Path) -> "IcsCalendarClient":
        """Read an existing .ics (e.g. exported from Google/Outlook) to pick up exam events.

        All-day events become midnight-to-midnight; events with no end last one day
        (all-day) or one hour.
        """
        cal = Calendar.from_ical(Path(path).read_bytes())
        events = []
        for item in cal.walk("VEVENT"):
            raw_start = item.get("dtstart").dt
            start = to_local_naive(raw_start)
            if item.get("dtend") is not None:
                end = to_local_naive(item.get("dtend").dt)
            else:
                all_day = not isinstance(raw_start, datetime)
                end = start + (timedelta(days=1) if all_day else timedelta(hours=1))
            events.append(CalendarEvent(
                summary=str(item.get("summary", "")),
                start=start,
                end=end,
                description=str(item.get("description", "")),
                event_id=str(item.get("uid")) if item.get("uid") else None,
            ))
        return cls(path, events)
