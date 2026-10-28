"""In-memory calendar used by tests and the dashboard (branch MF-00005)."""

from __future__ import annotations

from datetime import datetime

from study_planner.calendar_api.base import CalendarClient, CalendarEvent


class InMemoryCalendarClient(CalendarClient):
    def __init__(self, events: list[CalendarEvent] | None = None) -> None:
        self.events: list[CalendarEvent] = list(events or [])

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        # TODO(MF-00005)
        raise NotImplementedError("MF-00005")

    def create_event(self, event: CalendarEvent) -> CalendarEvent:
        # TODO(MF-00005): assign an event_id
        raise NotImplementedError("MF-00005")

    def delete_event(self, event: CalendarEvent) -> None:
        # TODO(MF-00005)
        raise NotImplementedError("MF-00005")
