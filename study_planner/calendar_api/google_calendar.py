"""Google Calendar API v3 backend (branch MF-00005; OAuth setup in TI-00003).

Needs `credentials.json` (OAuth Desktop client) in the repo root — git-ignored.
First run opens a browser for consent and stores `token.json` — also git-ignored.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from study_planner import config as cfg
from study_planner.calendar_api.base import CalendarClient, CalendarEvent

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
CREDENTIALS_FILE = cfg.ROOT / "credentials.json"
TOKEN_FILE = cfg.ROOT / "token.json"


class GoogleCalendarClient(CalendarClient):
    def __init__(self, calendar_id: str = "primary", credentials_file: Path = CREDENTIALS_FILE) -> None:
        self.calendar_id = calendar_id
        self.service = self._authenticate(credentials_file)

    @staticmethod
    def _authenticate(credentials_file: Path):
        """Return an authorized `googleapiclient` service.

        TODO(MF-00005): google_auth_oauthlib.flow.InstalledAppFlow.run_local_server,
        cache creds in TOKEN_FILE, refresh when expired, build("calendar", "v3", credentials=creds).
        """
        raise NotImplementedError("MF-00005")

    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        # TODO(MF-00005): events().list(timeMin, timeMax, singleEvents=True, orderBy="startTime")
        raise NotImplementedError("MF-00005")

    def create_event(self, event: CalendarEvent) -> CalendarEvent:
        # TODO(MF-00005): events().insert with timeZone=cfg.TIMEZONE
        raise NotImplementedError("MF-00005")

    def delete_event(self, event: CalendarEvent) -> None:
        # TODO(MF-00005): refuse unless event.is_planner_event
        raise NotImplementedError("MF-00005")
