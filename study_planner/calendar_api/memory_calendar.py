"""In-memory calendar used by tests and the dashboard (branch MF-00005)."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime

from study_planner.calendar_api.base import CalendarClient, CalendarEvent


class InMemoryCalendarClient(CalendarClient):
    def __init__(self, events: list[CalendarEvent] | None = None) -> None:
        self.events: list[CalendarEvent] = []
        for event in events or []:
            self.events.append(event if event.event_id else replace(event, event_id=uuid.uuid4().hex))

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        return sorted((e for e in self.events if e.overlaps(start, end)), key=lambda e: e.start)

    def create_event(self, event: CalendarEvent) -> CalendarEvent:
        stored = replace(event, event_id=event.event_id or uuid.uuid4().hex)
        self.events.append(stored)
        return stored

    def delete_event(self, event: CalendarEvent) -> None:
        if not event.is_planner_event:
            raise PermissionError(f"Refusing to delete a non-planner event: {event.summary!r}")
        self.events = [e for e in self.events if e.event_id != event.event_id]
