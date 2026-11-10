import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from importlib import resources
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def load_template(name: str) -> dict:
    """Loads a JSON template bundled with google_calendar_api.

    Args:
        name: Name of the template file (e.g. 'event.json', 'calendar.json', 'calendarList.json').
    """
    if not name.endswith(".json"):
        name = f"{name}.json"
    template_file = resources.files(
        "google_api.google_calendar_api.templates"
    ).joinpath(name)
    return json.loads(template_file.read_text(encoding="utf-8"))


def convert_date(
    date: str,
    add_day: bool = False,
    reverse: bool = False,
    input_format: str = "%d/%m/%Y",
    output_format: str = "%Y-%m-%d",
) -> str:
    """Convert a date string from one format to another, optionally adding or subtracting a day."""
    try:
        if not reverse:
            date_obj = datetime.strptime(date, input_format)
            if add_day:
                date_obj += timedelta(days=1)
            return date_obj.strftime(output_format)
        else:
            date_obj = datetime.strptime(date, output_format)
            if add_day:
                date_obj += timedelta(days=1)
            return date_obj.strftime(input_format)
    except ValueError as e:
        raise ValueError(
            f"Invalid date value or format: {date}. Required format: {input_format if not reverse else output_format}"
        ) from e


def convert_time(
    time_str: str,
    reverse: bool = False,
    input_format: str | None = None,
    output_format: str = "%H:%M:00",
) -> str:
    """Convert a time string between formats.

    Supports custom format string or attempts standard time formats (%H:%M, %H:%M:%S, %Hu%M).
    """
    if reverse:
        try:
            fmt = input_format or "%Hu%M"
            time_obj = datetime.strptime(time_str, output_format)
            return time_obj.strftime(fmt)
        except ValueError as e:
            raise ValueError(
                f"Invalid time value or format: {time_str}. Required format: {output_format}"
            ) from e

    # Forward conversion
    candidate_formats = (
        [input_format] if input_format else ["%H:%M:%S", "%H:%M", "%Hu%M"]
    )
    for fmt in candidate_formats:
        try:
            time_obj = datetime.strptime(time_str, fmt)
            # If user provided a specific output_format or if default %H:%M:00 is used but input had seconds
            target_output = output_format
            if (
                input_format is None
                and fmt == "%H:%M:%S"
                and output_format == "%H:%M:00"
            ):
                target_output = "%H:%M:%S"
            return time_obj.strftime(target_output)
        except ValueError:
            continue

    expected = input_format if input_format else "%H:%M, %H:%M:%S, or %Hu%M"
    raise ValueError(
        f"Invalid time value or format: {time_str}. Required format: {expected}"
    )


def validate_time_zone(tz: str) -> bool:
    """Validate whether tz string is a recognized IANA time zone using zoneinfo."""
    try:
        ZoneInfo(tz)
        return True
    except (ZoneInfoNotFoundError, ValueError):
        return False


@dataclass
class Calendar:
    title: str
    time_zone: str = "Europe/Brussels"
    description: str = ""
    location: str = ""
    id: str = ""
    kind: str = ""
    etag: str = ""
    conference_properties: dict = field(default_factory=dict)

    def build(self) -> dict:
        calendar_obj = {
            "summary": self.title,
            "timeZone": self.time_zone,
        }
        if self.description:
            calendar_obj["description"] = self.description
        if self.location:
            calendar_obj["location"] = self.location
        return calendar_obj

    @classmethod
    def from_json(cls, json_obj: dict) -> "Calendar":
        try:
            return cls(
                title=json_obj["summary"],
                time_zone=json_obj.get("timeZone", "Europe/Brussels"),
                description=json_obj.get("description", ""),
                location=json_obj.get("location", ""),
                id=json_obj.get("id", ""),
                kind=json_obj.get("kind", ""),
                etag=json_obj.get("etag", ""),
                conference_properties=json_obj.get("conferenceProperties", {}),
            )
        except KeyError as e:
            raise ValueError(f"Wrong kind of json_obj: {e} does not exist.") from e


@dataclass
class CalendarList:
    id: str
    color_id: str = ""
    background_color: str = ""
    foreground_color: str = ""
    hidden: bool = False
    selected: bool = False
    summary_override: str = ""
    default_reminders: list = field(default_factory=list)
    notification_settings: dict = field(default_factory=dict)

    def build(self) -> dict:
        obj: dict[str, Any] = {"id": self.id}
        if self.color_id:
            obj["colorId"] = self.color_id
        if self.background_color:
            obj["backgroundColor"] = self.background_color
        if self.foreground_color:
            obj["foregroundColor"] = self.foreground_color
        if self.hidden:
            obj["hidden"] = self.hidden
        if self.selected:
            obj["selected"] = self.selected
        if self.summary_override:
            obj["summaryOverride"] = self.summary_override
        if self.default_reminders:
            obj["defaultReminders"] = self.default_reminders
        if self.notification_settings:
            obj["notificationSettings"] = self.notification_settings
        return obj

    @classmethod
    def from_json(cls, json_obj: dict) -> "CalendarList":
        return cls(
            id=json_obj["id"],
            color_id=json_obj.get("colorId", ""),
            background_color=json_obj.get("backgroundColor", ""),
            foreground_color=json_obj.get("foregroundColor", ""),
            hidden=json_obj.get("hidden", False),
            selected=json_obj.get("selected", False),
            summary_override=json_obj.get("summaryOverride", ""),
            default_reminders=json_obj.get("defaultReminders", []),
            notification_settings=json_obj.get("notificationSettings", {}),
        )


@dataclass
class Event:
    title: str = ""
    start_date: str = ""
    end_date: str = ""
    time_zone: str = "Europe/Brussels"
    date_format: str = "%d/%m/%Y"
    location: str = ""
    description: str = ""
    summary: str = ""
    recurrence: list[str] = field(default_factory=list)
    attendees: list[dict | str] = field(default_factory=list)
    reminders: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.title and self.summary:
            self.title = self.summary
        elif not self.summary and self.title:
            self.summary = self.title

        self._start_date_iso = (
            convert_date(self.start_date, input_format=self.date_format)
            if self.start_date
            else ""
        )
        self._end_date_iso = (
            convert_date(self.end_date, input_format=self.date_format)
            if self.end_date
            else ""
        )

    def _base_payload(self) -> dict:
        payload: dict[str, Any] = {
            "summary": self.title,
        }
        if self.location:
            payload["location"] = self.location
        if self.description:
            payload["description"] = self.description
        if self.recurrence:
            payload["recurrence"] = (
                [self.recurrence]
                if isinstance(self.recurrence, str)
                else list(self.recurrence)
            )
        if self.attendees:
            formatted_attendees = []
            for attendee in self.attendees:
                if isinstance(attendee, str):
                    formatted_attendees.append({"email": attendee})
                elif isinstance(attendee, dict):
                    formatted_attendees.append(attendee)
            payload["attendees"] = formatted_attendees
        if self.reminders:
            payload["reminders"] = self.reminders
        return payload

    def build(self) -> dict:
        event_obj = self._base_payload()
        event_obj["start"] = {"date": self._start_date_iso, "timeZone": self.time_zone}
        event_obj["end"] = {"date": self._end_date_iso, "timeZone": self.time_zone}
        return event_obj


@dataclass
class TimedEvent(Event):
    start_time: str = ""
    end_time: str = ""
    time_format: str | None = None

    def __post_init__(self):
        super().__post_init__()
        self._start_time_iso = (
            convert_time(self.start_time, input_format=self.time_format)
            if self.start_time
            else "00:00:00"
        )
        self._end_time_iso = (
            convert_time(self.end_time, input_format=self.time_format)
            if self.end_time
            else "00:00:00"
        )

    def build(self) -> dict:
        event_obj = self._base_payload()
        event_obj["start"] = {
            "dateTime": f"{self._start_date_iso}T{self._start_time_iso}",
            "timeZone": self.time_zone,
        }
        event_obj["end"] = {
            "dateTime": f"{self._end_date_iso}T{self._end_time_iso}",
            "timeZone": self.time_zone,
        }
        return event_obj
