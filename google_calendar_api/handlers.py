import re
from typing import ClassVar

from googleapiclient.errors import HttpError

from ..logging_config import logger
from .objects import Calendar, Event, TimedEvent


class EventHandler:
    DATE_PATTERN = r"(\d{1,2}) (\w+) (\d{4})"
    TIME_PATTERN = r"\d{2}:\d{2}"
    NUM: ClassVar[dict[str, int]] = {
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

    def __init__(self, service) -> "EventHandler":
        self.service = service

    def planEvent(self, calendar_id: str, event_obj: Event | TimedEvent) -> dict:
        try:
            created_event = (
                self.service.events()
                .insert(calendarId=calendar_id, body=event_obj)
                .execute()
            )
            logger.info(f"Event created: {created_event['id']}")
            return created_event
        except HttpError as error:
            logger.error(f"Failed to create event in calendar {calendar_id}: {error}")
            raise

    def convert_date(self, date: str) -> str:
        matches = re.findall(self.DATE_PATTERN, date)
        if not matches:
            raise ValueError(f"Incorrect date format: {date}")
        date_match = matches[0]
        try:
            day = int(date_match[0])
            _month = date_match[1].lower()
            month = self.NUM[_month]
            year = int(date_match[2])
            return f"{day}/{month}/{year}"
        except KeyError:
            logger.error(f"Month name '{date_match[1]}' not found in dictionary.")
            raise
        except (ValueError, IndexError) as e:
            logger.error(f"Unable to parse date structure from '{date}': {e}")
            raise

    def convert_time(self, time_str: str) -> tuple[str, str]:
        time_match = re.findall(self.TIME_PATTERN, time_str)
        if len(time_match) < 2:
            raise ValueError(
                f"Time string does not contain start and end times: {time_str}"
            )
        return time_match[0], time_match[1]

    @staticmethod
    def is_greater(time1: str, time2: str) -> bool:
        h1, m1 = map(int, time1.split(":"))
        h2, m2 = map(int, time2.split(":"))
        total_minutes1 = h1 * 60 + m1
        total_minutes2 = h2 * 60 + m2
        return total_minutes1 >= total_minutes2

    def getEvents(self, calendar_id: str, day: str) -> list[dict]:
        start_of_day = f"{day}T00:00:00Z"
        end_of_day = f"{day}T23:59:59Z"

        events_result = (
            self.service.events()
            .list(
                calendarId=calendar_id,
                timeMin=start_of_day,
                timeMax=end_of_day,
                singleEvents=True,
                orderBy="startTime",
                timeZone="UTC",
            )
            .execute()
        )
        return events_result.get("items", [])

    def delEvent(self, calendar_id: str, event_id: str) -> None:
        self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        logger.info(f"Deleted event {event_id} from calendar {calendar_id}")

    def removeDuplicates(self, calendar_id: str, day: str) -> None:
        events = self.getEvents(calendar_id, day)
        seen = set()
        for event in events:
            summary = event.get("summary")
            start = event.get("start", {}).get("dateTime")
            key = (summary, start)
            if key in seen:
                self.delEvent(calendar_id, event["id"])
            else:
                seen.add(key)


class CalendarHandler:
    def __init__(self, service) -> "CalendarHandler":
        self.service = service

    def get_calendar_id(self, calendar_name: str) -> str | None:
        try:
            calendar_list = self.service.calendarList().list().execute()
            for calendar in calendar_list.get("items", []):
                if calendar["summary"] == calendar_name:
                    return calendar["id"]
            return None
        except HttpError as error:
            logger.error(f"Error fetching calendar ID for '{calendar_name}': {error}")
            raise

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

    def clear_calendar(self, calendar_name: str) -> None:
        id = self.get_calendar_id(calendar_name)
        if not id:
            logger.warning(f"Calendar {calendar_name} does not exist.")
            return
        try:
            self.service.calendars().clear(calendarId=id).execute()
            logger.info(f"Cleared calendar: {calendar_name}")
        except HttpError as error:
            logger.error(f"Failed to clear calendar {calendar_name}: {error}")
            raise

    def delete_calendar(self, calendar_name: str) -> None:
        id = self.get_calendar_id(calendar_name)
        if not id:
            logger.warning(f"Calendar {calendar_name} does not exist.")
            return
        try:
            self.service.calendars().delete(calendarId=id).execute()
            logger.info(f"Deleted calendar: {calendar_name}")
        except HttpError as error:
            logger.error(f"Failed to delete calendar {calendar_name}: {error}")
            raise

    def get_calendar(self, calendar_name: str) -> dict | None:
        id = self.get_calendar_id(calendar_name)
        if not id:
            logger.warning(f"Calendar {calendar_name} does not exist.")
            return None
        try:
            return self.service.calendars().get(calendarId=id).execute()
        except HttpError as error:
            logger.error(f"Failed to get calendar {calendar_name}: {error}")
            raise

    def update_calendar(self, calendar_name: str, body: dict) -> None:
        id = self.get_calendar_id(calendar_name)
        if not id:
            logger.warning(f"Calendar {calendar_name} does not exist.")
            return
        try:
            self.service.calendars().update(calendarId=id, body=body).execute()
            logger.info(f"Updated calendar metadata for: {calendar_name}")
        except HttpError as error:
            logger.error(f"Failed to update calendar {calendar_name}: {error}")
            raise

    def delete_calendar_from_list(self, calendar_name: str) -> None:
        id = self.get_calendar_id(calendar_name)
        if not id:
            logger.warning(f"Calendar {calendar_name} does not exist.")
            return
        try:
            self.service.calendarList().delete(calendarId=id).execute()
            logger.info(f"Deleted calendar from list: {calendar_name}")
        except HttpError as error:
            logger.error(
                f"Failed to delete calendar from list {calendar_name}: {error}"
            )
            raise

    def get_calendar_list_entry(self, calendar_name: str) -> dict | None:
        id = self.get_calendar_id(calendar_name)
        if not id:
            logger.warning(f"Calendar {calendar_name} does not exist.")
            return None
        try:
            return self.service.calendarList().get(calendarId=id).execute()
        except HttpError as error:
            logger.error(
                f"Failed to get calendar list entry for {calendar_name}: {error}"
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

    def update_calendar_list_entry(self, calendar_name: str, body: dict) -> None:
        """Updates the user's personal calendar entry (colors, notifications, hidden state)."""
        id = self.get_calendar_id(calendar_name)
        if not id:
            logger.warning(f"Calendar {calendar_name} does not exist.")
            return
        try:
            self.service.calendarList().update(calendarId=id, body=body).execute()
            logger.info(f"Updated calendar list entry for: {calendar_name}")
        except HttpError as error:
            logger.error(
                f"Failed to update calendar list entry for {calendar_name}: {error}"
            )
            raise
