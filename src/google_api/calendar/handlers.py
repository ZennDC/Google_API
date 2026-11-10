import logging
import re
from datetime import datetime, time
from typing import ClassVar

from googleapiclient.errors import HttpError

from .objects import Calendar, Event, TimedEvent

logger = logging.getLogger("google_api")


class EventHandler:
    """Handles event operations for Google Calendar."""

    # Retained for backwards compatibility with Dutch calendar text representations
    DUTCH_MONTHS: ClassVar[dict[str, int]] = {
        "januari": 1,
        "februari": 2,
        "maart": 3,
        "april": 4,
        "mei": 5,
        "juni": 6,
        "juli": 7,
        "augustus": 8,
        "september": 9,
        "oktober": 10,
        "november": 11,
        "december": 12,
    }
    DATE_PATTERN = r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})"
    TIME_PATTERN = r"\d{1,2}:\d{2}"

    def __init__(self, service) -> None:
        self.service = service

    def close(self) -> None:
        """Closes the underlying Google API HTTP client resource if supported."""
        if hasattr(self.service, "close"):
            self.service.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def plan_event(
        self, calendar_id: str, event_obj: Event | TimedEvent | dict
    ) -> dict:
        try:
            body = event_obj.build() if hasattr(event_obj, "build") else event_obj
            created_event = (
                self.service.events()
                .insert(calendarId=calendar_id, body=body)
                .execute()
            )
            logger.info(f"Event created: {created_event['id']}")
            return created_event
        except HttpError as error:
            logger.error(f"Failed to create event in calendar {calendar_id}: {error}")
            raise

    def get_event(self, calendar_id: str, event_id: str) -> dict:
        """Retrieves a single event by ID."""
        try:
            return (
                self.service.events()
                .get(calendarId=calendar_id, eventId=event_id)
                .execute()
            )
        except HttpError as error:
            logger.error(
                f"Failed to fetch event {event_id} from calendar {calendar_id}: {error}"
            )
            raise

    def update_event(
        self,
        calendar_id: str,
        event_id: str,
        event_obj: Event | TimedEvent | dict,
        patch: bool = True,
    ) -> dict:
        """Updates an existing event using events().patch or events().update."""
        try:
            body = event_obj.build() if hasattr(event_obj, "build") else event_obj
            if patch:
                updated_event = (
                    self.service.events()
                    .patch(calendarId=calendar_id, eventId=event_id, body=body)
                    .execute()
                )
            else:
                updated_event = (
                    self.service.events()
                    .update(calendarId=calendar_id, eventId=event_id, body=body)
                    .execute()
                )
            logger.info(f"Event updated: {updated_event.get('id', event_id)}")
            return updated_event
        except HttpError as error:
            logger.error(
                f"Failed to update event {event_id} in calendar {calendar_id}: {error}"
            )
            raise

    def convert_date(self, date_str: str) -> str:
        """Parses dates from standard formats (%d/%m/%Y, %Y-%m-%d) or Dutch natural language (e.g. '15 januari 2026').

        Returns date formatted as 'D/M/YYYY'.
        """
        stripped = date_str.strip()
        # Attempt standard numeric formats first
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
            try:
                parsed_dt = datetime.strptime(stripped, fmt)
                return f"{parsed_dt.day}/{parsed_dt.month}/{parsed_dt.year}"
            except ValueError:
                pass

        # Match natural language tokens
        match = re.search(self.DATE_PATTERN, stripped)
        if not match:
            raise ValueError(f"Incorrect date format: {date_str}")

        day_str, month_token, year_str = match.groups()
        month_lower = month_token.lower()
        if month_lower not in self.DUTCH_MONTHS:
            logger.error(f"Month name '{month_token}' not found in dictionary.")
            raise KeyError(f"Unknown month name: {month_token}")

        day = int(day_str)
        month = self.DUTCH_MONTHS[month_lower]
        year = int(year_str)
        return f"{day}/{month}/{year}"

    def convert_time(self, time_str: str) -> tuple[str, str]:
        """Extracts start and end times matching HH:MM from a string."""
        time_match = re.findall(self.TIME_PATTERN, time_str)
        if len(time_match) < 2:
            raise ValueError(
                f"Time string does not contain start and end times: {time_str}"
            )
        return time_match[0], time_match[1]

    @staticmethod
    def is_greater(time1: str, time2: str) -> bool:
        """Compares two time strings using datetime.time objects.

        Supports ISO formats like 'HH:MM' or 'HH:MM:SS'.
        Returns True if time1 >= time2.
        """
        t1 = time.fromisoformat(time1.strip())
        t2 = time.fromisoformat(time2.strip())
        return t1 >= t2

    def get_events(
        self,
        calendar_id: str,
        day: str,
        time_zone: str = "Europe/Brussels",
    ) -> list[dict]:
        """Retrieves events for a given calendar and day or ISO timestamp range, paginating through all results.

        If `day` is already an ISO timestamp (contains 'T'), it is passed directly as timeMin.
        If `day` is a date (YYYY-MM-DD or DD/MM/YYYY), the day boundaries are computed
        and queried using the specified target timeZone.
        """
        if "T" in day:
            time_min = day
            time_max = None
        else:
            # Normalize day into YYYY-MM-DD
            if "/" in day:
                d, m, y = day.split("/")
                iso_day = f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
            else:
                iso_day = day

            time_min = f"{iso_day}T00:00:00Z"
            time_max = f"{iso_day}T23:59:59Z"

        request_kwargs = {
            "calendarId": calendar_id,
            "timeMin": time_min,
            "singleEvents": True,
            "orderBy": "startTime",
            "timeZone": time_zone,
        }
        if time_max:
            request_kwargs["timeMax"] = time_max

        events: list[dict] = []
        page_token = None
        while True:
            if page_token:
                request_kwargs["pageToken"] = page_token
            try:
                events_result = self.service.events().list(**request_kwargs).execute()
            except HttpError as error:
                logger.error(
                    f"Failed to fetch events for calendar {calendar_id}: {error}"
                )
                raise
            events.extend(events_result.get("items", []))
            page_token = events_result.get("nextPageToken")
            if not page_token:
                break

        return events

    def delete_event(self, calendar_id: str, event_id: str) -> None:
        self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        logger.info(f"Deleted event {event_id} from calendar {calendar_id}")

    def remove_duplicates(self, calendar_id: str, day: str) -> None:
        events = self.get_events(calendar_id, day)
        seen = set()
        for event in events:
            summary = event.get("summary")
            start = event.get("start", {}).get("dateTime")
            key = (summary, start)
            if key in seen:
                self.delete_event(calendar_id, event["id"])
            else:
                seen.add(key)


class CalendarHandler:
    def __init__(self, service) -> None:
        self.service = service

    def find_calendar_id_by_name(self, calendar_name: str) -> str | None:
        """Finds a calendar ID by summary/name, paginating through all available calendars."""
        if calendar_name == "primary":
            return "primary"

        page_token = None
        while True:
            try:
                response = (
                    self.service.calendarList().list(pageToken=page_token).execute()
                )
            except HttpError as error:
                logger.error(
                    f"Error fetching calendar list while looking for '{calendar_name}': {error}"
                )
                raise

            for calendar in response.get("items", []):
                if (
                    calendar.get("summary") == calendar_name
                    or calendar.get("id") == calendar_name
                ):
                    return calendar.get("id")

            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return None

    def get_calendar_id(self, calendar_name: str) -> str | None:
        """Convenience alias for find_calendar_id_by_name."""
        return self.find_calendar_id_by_name(calendar_name)

    def _resolve_calendar_id(self, calendar_id_or_name: str) -> str | None:
        """Resolves calendar ID directly or falls back to name lookup."""
        if calendar_id_or_name == "primary" or "@" in calendar_id_or_name:
            return calendar_id_or_name
        cal_id = self.find_calendar_id_by_name(calendar_id_or_name)
        return cal_id or calendar_id_or_name

    def create_calendar(self, calendar_obj: Calendar | dict) -> str:
        try:
            body = (
                calendar_obj if isinstance(calendar_obj, dict) else calendar_obj.build()
            )
            created_calendar = self.service.calendars().insert(body=body).execute()
            logger.info(f"Calendar created: {created_calendar['id']}")
            return created_calendar["id"]
        except HttpError as error:
            logger.error(f"Failed to create calendar: {error}")
            raise

    def clear_calendar(self, calendar_id: str) -> None:
        cal_id = self._resolve_calendar_id(calendar_id)
        if not cal_id:
            logger.warning(f"Calendar {calendar_id} does not exist.")
            return
        try:
            self.service.calendars().clear(calendarId=cal_id).execute()
            logger.info(f"Cleared calendar: {calendar_id}")
        except HttpError as error:
            logger.error(f"Failed to clear calendar {calendar_id}: {error}")
            raise

    def delete_calendar(self, calendar_id: str) -> None:
        cal_id = self._resolve_calendar_id(calendar_id)
        if not cal_id:
            logger.warning(f"Calendar {calendar_id} does not exist.")
            return
        try:
            self.service.calendars().delete(calendarId=cal_id).execute()
            logger.info(f"Deleted calendar: {calendar_id}")
        except HttpError as error:
            logger.error(f"Failed to delete calendar {calendar_id}: {error}")
            raise

    def get_calendar(self, calendar_id: str) -> dict | None:
        cal_id = self._resolve_calendar_id(calendar_id)
        if not cal_id:
            logger.warning(f"Calendar {calendar_id} does not exist.")
            return None
        try:
            return self.service.calendars().get(calendarId=cal_id).execute()
        except HttpError as error:
            logger.error(f"Failed to get calendar {calendar_id}: {error}")
            raise

    def update_calendar(self, calendar_id: str, body: dict) -> None:
        cal_id = self._resolve_calendar_id(calendar_id)
        if not cal_id:
            logger.warning(f"Calendar {calendar_id} does not exist.")
            return
        try:
            self.service.calendars().update(calendarId=cal_id, body=body).execute()
            logger.info(f"Updated calendar metadata for: {calendar_id}")
        except HttpError as error:
            logger.error(f"Failed to update calendar {calendar_id}: {error}")
            raise

    def delete_calendar_from_list(self, calendar_id: str) -> None:
        cal_id = self._resolve_calendar_id(calendar_id)
        if not cal_id:
            logger.warning(f"Calendar {calendar_id} does not exist.")
            return
        try:
            self.service.calendarList().delete(calendarId=cal_id).execute()
            logger.info(f"Deleted calendar from list: {calendar_id}")
        except HttpError as error:
            logger.error(f"Failed to delete calendar from list {calendar_id}: {error}")
            raise

    def get_calendar_list_entry(self, calendar_id: str) -> dict | None:
        cal_id = self._resolve_calendar_id(calendar_id)
        if not cal_id:
            logger.warning(f"Calendar {calendar_id} does not exist.")
            return None
        try:
            return self.service.calendarList().get(calendarId=cal_id).execute()
        except HttpError as error:
            logger.error(
                f"Failed to get calendar list entry for {calendar_id}: {error}"
            )
            raise

    def add_existing_calendar(self, calendar_list_entry: dict) -> dict:
        try:
            result = (
                self.service.calendarList().insert(body=calendar_list_entry).execute()
            )
            logger.info(
                f"Added existing calendar to list: {calendar_list_entry.get('id')}"
            )
            return result
        except HttpError as error:
            logger.error(f"Failed to add existing calendar to list: {error}")
            raise

    def list_all_calendars(self) -> list[dict]:
        page_token = None
        calendars = []
        while True:
            calendar_list = (
                self.service.calendarList().list(pageToken=page_token).execute()
            )
            calendars.extend(calendar_list.get("items", []))
            page_token = calendar_list.get("nextPageToken")
            if not page_token:
                break
        return calendars

    def update_calendar_list_entry(self, calendar_id: str, body: dict) -> None:
        """Updates the user's personal calendar entry (colors, notifications, hidden state)."""
        cal_id = self._resolve_calendar_id(calendar_id)
        if not cal_id:
            logger.warning(f"Calendar {calendar_id} does not exist.")
            return
        try:
            self.service.calendarList().update(calendarId=cal_id, body=body).execute()
            logger.info(f"Updated calendar list entry for: {calendar_id}")
        except HttpError as error:
            logger.error(
                f"Failed to update calendar list entry for {calendar_id}: {error}"
            )
            raise

    def close(self) -> None:
        """Closes the underlying Google API HTTP client resource if supported."""
        if hasattr(self.service, "close"):
            self.service.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
