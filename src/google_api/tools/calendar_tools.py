from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Any
from zoneinfo import ZoneInfo

from ..calendar.handlers import CalendarHandler, EventHandler
from ..calendar.objects import Event, TimedEvent, validate_time_zone
from ..oauth.factory import CALENDAR_SCOPES, get_calendar_service
from ._base import _BaseToolGroup, tool_action
from ._utils import (
    DEFAULT_TIME_ZONE,
    TOOL_HANDLED_ERRORS,
    clamp_int,
    err,
    handle_tool_exception,
    ok,
    parse_iso_datetime,
)


def _resolve_calendar_id_strict(
    calendar_handler: CalendarHandler, calendar_name: str
) -> str | None:
    name = calendar_name.strip() or "primary"
    if name == "primary" or "@" in name:
        return name
    return calendar_handler.find_calendar_id_by_name(name)


def _compact_event(raw: dict[str, Any]) -> dict[str, Any]:
    start_obj = raw.get("start", {})
    end_obj = raw.get("end", {})
    all_day = "date" in start_obj and "dateTime" not in start_obj
    attendees = [
        att["email"]
        for att in raw.get("attendees", [])
        if isinstance(att, dict) and att.get("email")
    ]
    return {
        "id": raw.get("id", ""),
        "title": raw.get("summary") or "(No Title)",
        "start": start_obj.get("dateTime") or start_obj.get("date") or "",
        "end": end_obj.get("dateTime") or end_obj.get("date") or "",
        "all_day": all_day,
        "location": raw.get("location", ""),
        "attendees": attendees,
    }


def _fetch_events_range(
    event_handler: EventHandler,
    calendar_id: str,
    time_min: str,
    time_max: str,
    time_zone: str,
    max_results: int | None = None,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    page_token: str | None = None

    while True:
        kwargs: dict[str, Any] = {
            "calendarId": calendar_id,
            "timeMin": time_min,
            "timeMax": time_max,
            "singleEvents": True,
            "orderBy": "startTime",
            "timeZone": time_zone,
        }
        if max_results is not None:
            remaining = max_results - len(events)
            if remaining <= 0:
                break
            kwargs["maxResults"] = remaining
        if page_token:
            kwargs["pageToken"] = page_token

        result = event_handler.service.events().list(**kwargs).execute()
        events.extend(result.get("items", []))
        if max_results is not None and len(events) >= max_results:
            return events[:max_results]

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    return events


class CalendarTools(_BaseToolGroup):
    """Encapsulated, LLM-ready Google Calendar tools with OAuth lifecycle management."""

    def __init__(
        self,
        token_file: str | None = None,
        client_secret_file: str | None = None,
        default_time_zone: str = DEFAULT_TIME_ZONE,
        headless: bool = False,
        save_token: bool = True,
        event_handler: EventHandler | None = None,
        calendar_handler: CalendarHandler | None = None,
        lock: Any | None = None,
        auth_callback: Callable[[], dict[str, Any] | None] | None = None,
    ) -> None:
        super().__init__(
            token_file=token_file,
            client_secret_file=client_secret_file,
            headless=headless,
            save_token=save_token,
            lock=lock,
            auth_callback=auth_callback,
        )
        self.default_time_zone = default_time_zone
        self._event_handler = event_handler
        self._calendar_handler = calendar_handler
        self.is_authenticated = self._has_handlers()

    @property
    def default_time_zone(self) -> str:
        """Default IANA time zone used when a calendar tool receives an empty time_zone."""
        return self._default_time_zone

    @default_time_zone.setter
    def default_time_zone(self, value: str) -> None:
        if not validate_time_zone(value):
            raise ValueError(f"Invalid IANA time zone: '{value}'.")
        self._default_time_zone = value

    def _required_scopes(self) -> list[str]:
        return list(CALENDAR_SCOPES)

    def _has_handlers(self) -> bool:
        return self._event_handler is not None and self._calendar_handler is not None

    def _build_handlers_from_credentials(self, creds: Any) -> None:
        if self._event_handler is None or self._calendar_handler is None:
            service = get_calendar_service(credentials=creds)
            if self._event_handler is None:
                self._event_handler = EventHandler(service)
            if self._calendar_handler is None:
                self._calendar_handler = CalendarHandler(service)

    def _iter_handlers(self) -> tuple[Any, ...]:
        return (self._event_handler, self._calendar_handler)

    def _clear_handlers(self) -> None:
        self._event_handler = None
        self._calendar_handler = None

    def get_tools(self) -> list[Callable[..., dict[str, Any]]]:
        """Returns the list of bound Google Calendar agent tool methods."""
        return [
            self.schedule_event,
            self.list_events,
            self.check_availability,
            self.delete_event,
        ]

    @tool_action(read_only=False)
    def schedule_event(
        self,
        title: str,
        start: str,
        end: str,
        description: str = "",
        location: str = "",
        attendees: list[str] | None = None,
        calendar_name: str = "primary",
        time_zone: str = "",
    ) -> dict[str, Any]:
        """Schedules a timed or all-day Google Calendar event.

        Args:
            title: Title/summary of the event.
            start: ISO-8601 start datetime ('YYYY-MM-DDTHH:MM') or all-day date ('YYYY-MM-DD').
            end: ISO-8601 end datetime ('YYYY-MM-DDTHH:MM') or all-day date ('YYYY-MM-DD').
            description: Optional event description.
            location: Optional event location or meeting link.
            attendees: Optional list of attendee email addresses.
            calendar_name: Target calendar summary name or ID (defaults to 'primary').
            time_zone: Optional IANA time zone (defaults to configured default, 'Europe/Brussels').

        Returns:
            Standard response dict with the created event ID, times, and link.
        """
        with self._lock:
            auth_err = self._ensure_ready()
            if auth_err is not None:
                return auth_err
            assert self._event_handler is not None
            assert self._calendar_handler is not None

            try:
                tz = time_zone or self._default_time_zone
                clean_title = title.strip()
                if not clean_title:
                    raise ValueError("Event 'title' cannot be empty.")
                if not validate_time_zone(tz):
                    raise ValueError(f"Invalid IANA time zone: '{tz}'.")

                start_dt, start_all_day = parse_iso_datetime(start, tz)
                end_dt, end_all_day = parse_iso_datetime(end, tz)
                if start_all_day != end_all_day:
                    raise ValueError(
                        "Both 'start' and 'end' must either be dates (YYYY-MM-DD) or datetimes (YYYY-MM-DDTHH:MM)."
                    )

                cal_id = _resolve_calendar_id_strict(
                    self._calendar_handler, calendar_name
                )
                if not cal_id:
                    return err(f"Calendar '{calendar_name}' not found.", "NOT_FOUND")

                target_tz = ZoneInfo(tz)
                attendee_list: list[dict[Any, Any] | str] = (
                    list(attendees) if attendees else []
                )

                if start_all_day:
                    if end_dt.date() < start_dt.date():
                        raise ValueError(
                            "'end' date cannot be earlier than 'start' date."
                        )
                    # Google Calendar all-day end.date is exclusive; bump single-day end by +1 day
                    api_end_date = (
                        end_dt.date() + timedelta(days=1)
                        if end_dt.date() == start_dt.date()
                        else end_dt.date()
                    )
                    event_obj: Event | TimedEvent = Event(
                        title=clean_title,
                        start_date=start_dt.date().isoformat(),
                        end_date=api_end_date.isoformat(),
                        time_zone=tz,
                        date_format="%Y-%m-%d",
                        location=location,
                        description=description,
                        attendees=attendee_list,
                    )
                else:
                    if end_dt <= start_dt:
                        raise ValueError("'end' must be after 'start'.")
                    start_local = start_dt.astimezone(target_tz)
                    end_local = end_dt.astimezone(target_tz)
                    event_obj = TimedEvent(
                        title=clean_title,
                        start_date=start_local.strftime("%Y-%m-%d"),
                        end_date=end_local.strftime("%Y-%m-%d"),
                        start_time=start_local.strftime("%H:%M:%S"),
                        end_time=end_local.strftime("%H:%M:%S"),
                        time_zone=tz,
                        date_format="%Y-%m-%d",
                        time_format="%H:%M:%S",
                        location=location,
                        description=description,
                        attendees=attendee_list,
                    )

                created = self._event_handler.plan_event(cal_id, event_obj)
                created_start = created.get("start", {})
                created_end = created.get("end", {})
                data = {
                    "id": created.get("id", ""),
                    "title": created.get("summary", clean_title),
                    "start": created_start.get("dateTime")
                    or created_start.get("date")
                    or start,
                    "end": created_end.get("dateTime")
                    or created_end.get("date")
                    or end,
                    "all_day": start_all_day,
                    "calendar_id": cal_id,
                    "html_link": created.get("htmlLink", ""),
                }
                return ok(data, f"Event '{data['title']}' scheduled successfully.")
            except TOOL_HANDLED_ERRORS as exc:
                return handle_tool_exception(exc, "Failed to schedule event")

    @tool_action(read_only=True)
    def list_events(
        self,
        start_date: str,
        end_date: str = "",
        calendar_name: str = "primary",
        time_zone: str = "",
        max_results: int = 20,
    ) -> dict[str, Any]:
        """Lists events on a calendar for a specific date or date range.

        Args:
            start_date: Start ISO date ('YYYY-MM-DD') or ISO datetime.
            end_date: Optional end ISO date or datetime (defaults to end of start_date).
            calendar_name: Target calendar summary name or ID (defaults to 'primary').
            time_zone: Optional IANA time zone (defaults to configured default, 'Europe/Brussels').
            max_results: Maximum number of events to return (1 to 50).

        Returns:
            Standard response dict with 'count' and compact 'events' list.
        """
        with self._lock:
            auth_err = self._ensure_ready()
            if auth_err is not None:
                return auth_err
            assert self._event_handler is not None
            assert self._calendar_handler is not None

            try:
                tz = time_zone or self._default_time_zone
                if not validate_time_zone(tz):
                    raise ValueError(f"Invalid IANA time zone: '{tz}'.")

                limit = clamp_int(max_results, 1, 50)
                start_dt, start_is_date = parse_iso_datetime(start_date, tz)
                if start_is_date:
                    start_dt = start_dt.replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )

                if end_date.strip():
                    end_dt, end_is_date = parse_iso_datetime(end_date, tz)
                    if end_is_date:
                        end_dt = end_dt.replace(
                            hour=23, minute=59, second=59, microsecond=0
                        )
                else:
                    end_dt = start_dt.replace(
                        hour=23, minute=59, second=59, microsecond=0
                    )

                if end_dt < start_dt:
                    raise ValueError("'end_date' cannot be earlier than 'start_date'.")

                cal_id = _resolve_calendar_id_strict(
                    self._calendar_handler, calendar_name
                )
                if not cal_id:
                    return err(f"Calendar '{calendar_name}' not found.", "NOT_FOUND")

                raw_events = _fetch_events_range(
                    event_handler=self._event_handler,
                    calendar_id=cal_id,
                    time_min=start_dt.isoformat(),
                    time_max=end_dt.isoformat(),
                    time_zone=tz,
                    max_results=limit,
                )
                events = [_compact_event(item) for item in raw_events]
                return ok(
                    {
                        "calendar_id": cal_id,
                        "count": len(events),
                        "events": events,
                    },
                    f"Found {len(events)} event(s).",
                )
            except TOOL_HANDLED_ERRORS as exc:
                return handle_tool_exception(exc, "Failed to list events")

    @tool_action(read_only=True)
    def check_availability(
        self,
        start: str,
        end: str,
        calendar_names: list[str] | None = None,
        time_zone: str = "",
    ) -> dict[str, Any]:
        """Checks if a time window is free across one or more calendars.

        Args:
            start: ISO-8601 window start ('YYYY-MM-DDTHH:MM' or 'YYYY-MM-DD').
            end: ISO-8601 window end ('YYYY-MM-DDTHH:MM' or 'YYYY-MM-DD').
            calendar_names: Optional list of calendar names or IDs (defaults to ['primary']).
            time_zone: Optional IANA time zone (defaults to configured default, 'Europe/Brussels').

        Returns:
            Standard response dict with 'available' boolean and any 'conflicts'.
        """
        with self._lock:
            auth_err = self._ensure_ready()
            if auth_err is not None:
                return auth_err
            assert self._event_handler is not None
            assert self._calendar_handler is not None

            try:
                tz = time_zone or self._default_time_zone
                if not validate_time_zone(tz):
                    raise ValueError(f"Invalid IANA time zone: '{tz}'.")

                start_dt, start_is_date = parse_iso_datetime(start, tz)
                end_dt, end_is_date = parse_iso_datetime(end, tz)
                if start_is_date:
                    start_dt = start_dt.replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                if end_is_date:
                    end_dt = end_dt.replace(
                        hour=23, minute=59, second=59, microsecond=0
                    )
                if end_dt <= start_dt:
                    raise ValueError("'end' must be after 'start'.")

                targets = list(calendar_names) if calendar_names else ["primary"]
                resolved_ids: list[str] = []
                for cal_name in targets:
                    cal_id = _resolve_calendar_id_strict(
                        self._calendar_handler, cal_name
                    )
                    if not cal_id:
                        return err(f"Calendar '{cal_name}' not found.", "NOT_FOUND")
                    resolved_ids.append(cal_id)

                time_min = start_dt.isoformat()
                time_max = end_dt.isoformat()
                conflicts: list[dict[str, Any]] = []

                for cal_id in resolved_ids:
                    items = _fetch_events_range(
                        event_handler=self._event_handler,
                        calendar_id=cal_id,
                        time_min=time_min,
                        time_max=time_max,
                        time_zone=tz,
                    )
                    for item in items:
                        if (
                            item.get("status") == "cancelled"
                            or item.get("transparency") == "transparent"
                        ):
                            continue
                        compact = _compact_event(item)
                        conflicts.append(
                            {
                                "calendar_id": cal_id,
                                "id": compact["id"],
                                "title": compact["title"],
                                "start": compact["start"],
                                "end": compact["end"],
                            }
                        )

                available = len(conflicts) == 0
                message = (
                    "Time slot is available."
                    if available
                    else f"Found {len(conflicts)} conflicting event(s)."
                )
                return ok(
                    {
                        "available": available,
                        "start": time_min,
                        "end": time_max,
                        "conflicts": conflicts,
                    },
                    message,
                )
            except TOOL_HANDLED_ERRORS as exc:
                return handle_tool_exception(exc, "Failed to check availability")

    @tool_action(read_only=False)
    def delete_event(
        self,
        event_id: str,
        calendar_name: str = "primary",
    ) -> dict[str, Any]:
        """Deletes a Google Calendar event by ID.

        Args:
            event_id: The calendar event ID to delete.
            calendar_name: Target calendar summary name or ID (defaults to 'primary').

        Returns:
            Standard response dict confirming deletion.
        """
        with self._lock:
            auth_err = self._ensure_ready()
            if auth_err is not None:
                return auth_err
            assert self._event_handler is not None
            assert self._calendar_handler is not None

            try:
                clean_id = event_id.strip()
                if not clean_id:
                    raise ValueError("event_id cannot be empty.")

                cal_id = _resolve_calendar_id_strict(
                    self._calendar_handler, calendar_name
                )
                if not cal_id:
                    return err(f"Calendar '{calendar_name}' not found.", "NOT_FOUND")

                self._event_handler.delete_event(cal_id, clean_id)
                return ok(
                    {"id": clean_id, "calendar_id": cal_id},
                    f"Event '{clean_id}' deleted successfully.",
                )
            except TOOL_HANDLED_ERRORS as exc:
                return handle_tool_exception(
                    exc, f"Failed to delete event '{event_id}'"
                )
