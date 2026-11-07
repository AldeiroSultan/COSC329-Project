"""Google Calendar API v3 backend (branch MF-00005; OAuth setup in TI-00003).

Needs `credentials.json` (OAuth Desktop client) in the repo root — git-ignored.
First run opens a browser for consent and stores `token.json` — also git-ignored.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from study_planner import config as cfg
from study_planner.calendar_api.base import (
    CalendarClient,
    CalendarEvent,
    to_local_aware,
    to_local_naive,
)

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
CREDENTIALS_FILE = cfg.ROOT / "credentials.json"
TOKEN_FILE = cfg.ROOT / "token.json"


class GoogleCalendarClient(CalendarClient):
    def __init__(
        self,
        calendar_id: str = "primary",
        credentials_file: Path = CREDENTIALS_FILE,
        service=None,
    ) -> None:
        """`service` lets tests inject a fake; otherwise we run the OAuth flow."""
        self.calendar_id = calendar_id
        self.service = service if service is not None else self._authenticate(credentials_file)

    @staticmethod
    def _authenticate(credentials_file: Path, token_file: Path = TOKEN_FILE):
        """Return an authorized `googleapiclient` service (opens a browser the first time)."""
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        creds = None
        if token_file.exists():
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not credentials_file.exists():
                    raise FileNotFoundError(
                        f"{credentials_file} not found. Follow docs/GOOGLE_SETUP.md, "
                        "or use IcsCalendarClient for an offline calendar."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
                creds = flow.run_local_server(port=0)
            token_file.write_text(creds.to_json(), encoding="utf-8")
        return build("calendar", "v3", credentials=creds)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _parse(item: dict) -> CalendarEvent:
        """Google event resource -> CalendarEvent (naive local time)."""
        start = item["start"].get("dateTime") or item["start"]["date"]
        end = item["end"].get("dateTime") or item["end"]["date"]
        return CalendarEvent(
            summary=item.get("summary", ""),
            start=to_local_naive(datetime.fromisoformat(start)),
            end=to_local_naive(datetime.fromisoformat(end)),
            description=item.get("description", ""),
            event_id=item["id"],
        )

    @staticmethod
    def _body(event: CalendarEvent) -> dict:
        """CalendarEvent -> Google event resource."""
        return {
            "summary": event.summary,
            "description": event.description,
            "start": {"dateTime": to_local_aware(event.start).isoformat(), "timeZone": cfg.TIMEZONE},
            "end": {"dateTime": to_local_aware(event.end).isoformat(), "timeZone": cfg.TIMEZONE},
        }

    # ------------------------------------------------------------------ CalendarClient
    def list_events(self, start: datetime, end: datetime) -> list[CalendarEvent]:
        events: list[CalendarEvent] = []
        page_token = None
        while True:
            response = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=to_local_aware(start).isoformat(),
                timeMax=to_local_aware(end).isoformat(),
                singleEvents=True,
                orderBy="startTime",
                pageToken=page_token,
            ).execute()
            events.extend(self._parse(item) for item in response.get("items", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                return events

    def create_event(self, event: CalendarEvent) -> CalendarEvent:
        created = self.service.events().insert(calendarId=self.calendar_id, body=self._body(event)).execute()
        return CalendarEvent(event.summary, event.start, event.end, event.description, created["id"])

    def delete_event(self, event: CalendarEvent) -> None:
        if not event.is_planner_event:
            raise PermissionError(f"Refusing to delete a non-planner event: {event.summary!r}")
        self.service.events().delete(calendarId=self.calendar_id, eventId=event.event_id).execute()
