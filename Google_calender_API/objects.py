import re
from datetime import datetime, timedelta

import pytz


def convert_date(
    date: str,
    add_day: bool = False,
    reverse: bool = False,
    input_format: str = "%d/%m/%Y",
    output_format: str = "%Y-%m-%d",
) -> str:
    """
    Convert a date string from one format to another, optionally adding or subtracting a day.

    Args:
    - date (str): The date string to convert.
    - add_day (bool): Whether to add a day (or subtract if reverse is True).
    - reverse (bool): Whether to convert from output_format to input_format.
    - input_format (str): The format of the input date string.
    - output_format (str): The format of the output date string.

    Returns:
    - str: The converted date string.

    Raises:
    - ValueError: If the date string does not match the expected format.
    """
    try:
        if not reverse:
            date_obj = datetime.strptime(date, input_format)
            if add_day:
                date_obj += timedelta(days=1)
            converted_date = date_obj.strftime(output_format)
        else:
            date_obj = datetime.strptime(date, output_format)
            if add_day:
                date_obj += timedelta(days=1)
            converted_date = date_obj.strftime(input_format)

        return converted_date
    except ValueError as e:
        raise ValueError(
            f"Invalid date value or format: {date}. Required format: {input_format if not reverse else output_format}"
        ) from e


def convert_time(
    time: str,
    reverse: bool = False,
    input_format: str = "%Hu%M",
    output_format: str = "%H:%M:%S",
) -> str:
    """
    Converts a time from one format to another.

    Args:
    - time (str): The time string to convert.
    - reverse (bool): Whether to convert from output_format to input_format.
    - input_format (str): The format of the input time string.
    - output_format (str): The format of the output time string.

    Returns:
    - str: The converted time string.

    Raises:
    - ValueError: If the time string does not match the expected format.
    """
    try:
        if not reverse:
            time_obj = datetime.strptime(time, input_format)
            converted_time = time_obj.strftime(output_format)
        else:
            time_obj = datetime.strptime(time, output_format)
            converted_time = time_obj.strftime(input_format)

        return converted_time
    except ValueError as e:
        raise ValueError(
            f"Invalid date value or format: {time}. Required format: {input_format if not reverse else output_format}"
        ) from e


def validate_time_zone(time_zone: str) -> bool:
    """
    Returns True if the time zone exists and False if it doesn't.

    Args:
    - time_zone (str): The time zone string to validate.

    Returns:
    - bool: True if the time zone exists, False otherwise.
    """
    try:
        pytz.timezone(time_zone)
        return True
    except pytz.UnknownTimeZoneError:
        return False


def validate_string(var) -> bool:
    """
    Validate if the given variable is a string.

    Args:
    - var: The variable to check.

    Returns:
    - bool: True if var is a string, False otherwise.
    """
    return isinstance(var, str)


def validate_int(var) -> bool:
    """
    Validate if the given variable is an integer.

    Args:
    - var: The variable to check.

    Returns:
    - bool: True if var is an integer, False otherwise.
    """
    return isinstance(var, str)


def validate_bool(var) -> bool:
    """
    Validate if the given variable is a boolean.

    Args:
    - var: The variable to check.

    Returns:
    - bool: True if var is a boolean, False otherwise.
    """
    return isinstance(var, bool)


def validate_hex_color(s: str) -> bool:
    """
    Validate if the input string is a hexadecimal color code.

    Args:
    - s (str): The string to validate.

    Returns:
    - bool: True if the string is a valid hex color code, False otherwise.
    """
    # Regular expression to match hex color codes
    hex_color_pattern = re.compile(r"^#(?:[0-9a-fA-F]{3}){1,2}$")
    return bool(hex_color_pattern.match(s))


class Calendar:
    def __init__(self, title: str, time_zone: str = "Europe/Brussels") -> None:
        self.title = title
        self.timeZone = time_zone

        self.description = ""
        self.location = ""

        self._kind = ""
        self._etag = ""
        self._id = ""
        self._conferenceProperties = ""

    @property
    def title(self) -> str:
        """
        Getter method for title.
        """
        return self._title

    @title.setter
    def title(self, title: str) -> None:
        """
        Setter method for title.
        """
        if validate_string(title):
            self._title = title
        else:
            raise ValueError(f"Not a string: {title}")

    @property
    def timeZone(self) -> str:
        """
        Getter method for timeZone.
        """
        return self._time_zone

    @timeZone.setter
    def timeZone(self, time_zone: str) -> None:
        """
        Setter method for timeZone.
        """
        if validate_time_zone(time_zone):
            self._time_zone = time_zone
        else:
            raise ValueError(f"Invalid time zone: {time_zone}")

    @property
    def description(self) -> str:
        """
        Getter method for description.
        """
        if self._description:
            return self._description

    @description.setter
    def description(self, description: str) -> None:
        """
        Setter method for description.
        """
        if validate_string(description):
            self._description = description
        else:
            raise ValueError(f"Not a string: {description}")

    @property
    def location(self) -> str:
        """
        Getter method for location.
        """
        if self._location:
            return self._location

    @location.setter
    def location(self, location: str) -> None:
        """
        Setter method for location.
        """
        if validate_string(location):
            self._location = location
        else:
            raise ValueError(f"Not a string: {location}")

    @property
    def kind(self) -> str | None:
        """
        Getter method for kind.
        """
        if self._kind:
            return self._kind

    @property
    def etag(self) -> str | None:
        """
        Getter method for etag.
        """
        if self._etag:
            return self._etag

    @property
    def id(self) -> str | None:
        """
        Getter method for id.
        """
        if self._id:
            return self._id

    @property
    def conferenceProperties(self) -> str | None:
        """
        Getter method for conferenceProperties.
        """
        if self._conferenceProperties:
            return self._conferenceProperties

    def build(self) -> dict:
        """
        Returns the calendar object as a JSON object.

        Returns:
        - dict: The calendar object.
        """
        calendar_obj = {
            "summary": self._title,
            "timeZone": self._time_zone,
        }
        if self._description:
            calendar_obj["description"] = self._description
        if self._location:
            calendar_obj["location"] = self._location

        return calendar_obj

    @classmethod
    def from_json(cls, json_obj: dict) -> "Calendar":
        """
        Constructs a new calendar object from a json object.

        Args:
        - json_obj (dict): The json object from an existing calendar.

        Returns:
        - Calendar: A calendar object.

        Raises:
        - ValueError: If the json object does not have the necessary elements.
        """
        try:
            obj = cls(json_obj["summary"], json_obj["timeZone"])
            obj._kind = json_obj["kind"]
            obj._etag = json_obj["etag"]
            obj._id = json_obj["id"]

            if "conferenceProperties" in json_obj:
                obj._conferenceProperties = json_obj["conferenceProperties"]
            if "description" in json_obj:
                obj.description = json_obj["description"]
            if "location" in json_obj:
                obj.location = json_obj["location"]

            return cls
        except KeyError as e:
            raise ValueError(f"Wrong kind of json_obj: {e} does not exist.")


class CalendarList:
    def __init__(self, id: str) -> None:
        self._id = id

        self._colorId = ""
        self._backgroundColor = ""
        self._foregroundColor = ""
        self._hidden = ""
        self._selected = ""
        self._summaryOverride = ""
        self._defaultReminders = ""
        self._notificationSettings = ""

        self._accessRole = ""
        self._conferenceProperties = ""
        self._deleted = ""
        self._description = ""
        self._etag = ""
        self._kind = ""
        self._location = ""
        self._primary = ""
        self._summary = ""
        self._timeZone = ""

    @property
    def id(self) -> str:
        return self._id

    @property
    def colorId(self) -> str | None:
        if self._colorId:
            return self._colorId

    @colorId.setter
    def colorId(self, colorId: int) -> None:
        if validate_int(colorId):
            self._colorId = colorId
        else:
            return ValueError(f"Not an integer: {colorId}")

    @property
    def backgroundColor(self) -> str | None:
        if self._backgroundColor:
            return self._backgroundColor

    @backgroundColor.setter
    def backgroundColor(self, backgroundColor: str) -> None:
        if validate_hex_color(backgroundColor):
            self._backgroundColor = backgroundColor
        else:
            return ValueError(f"Not a valid hex color code: {backgroundColor}")

    @property
    def foregroundColor(self) -> str | None:
        if self._foregroundColor:
            return self._foregroundColor

    @foregroundColor.setter
    def foregroundColor(self, foregroundColor: str) -> None:
        if validate_hex_color(foregroundColor):
            self._foregroundColor = foregroundColor
        else:
            return ValueError(f"Not a valid hex color code: {foregroundColor}")

    @property
    def hidden(self) -> bool | None:
        if self._hidden:
            return self._hidden

    @hidden.setter
    def hidden(self, is_hidden: bool) -> None:
        if validate_bool(is_hidden):
            self._hidden = is_hidden
        else:
            return ValueError(f"Not a boolean: {is_hidden}")

    @property
    def selected(self) -> bool | None:
        if self._selected:
            return self._selected

    @selected.setter
    def selected(self, is_selected: bool) -> None:
        if validate_bool(is_selected):
            self._selected = is_selected
        else:
            return ValueError(f"Not a boolean: {is_selected}")

    @property
    def summaryOverride(self) -> bool | None:
        if self._summaryOverride:
            return self._summaryOverride

    @summaryOverride.setter
    def summaryOverride(self, is_overridden: bool) -> None:
        if validate_bool(is_overridden):
            self._summaryOverride = is_overridden
        else:
            return ValueError(f"Not a boolean: {is_overridden}")

    @property
    def defaultReminders(self) -> list | None:
        if self._defaultReminders:
            return self._defaultReminders

    @defaultReminders.setter
    def defaultReminders(self, reminders: list) -> None:
        self._defaultReminders = reminders

    @property
    def notificationSettings(self) -> list | None:
        if self._defaultReminders:
            return self._defaultReminders

    @notificationSettings.setter
    def notificationSettings(self, settings: list) -> None:
        self._notificationSettings = settings

    @property
    def accessRole(self) -> str:
        return self._accessRole

    @property
    def conferenceProperties(self) -> str:
        return self._conferenceProperties

    @property
    def deleted(self) -> str:
        return self._deleted

    @property
    def description(self) -> str:
        return self._description

    @property
    def etag(self) -> str:
        return self._etag

    @property
    def kind(self) -> str:
        return self._kind

    @property
    def location(self) -> str:
        return self._location

    @property
    def primary(self) -> str:
        return self._primary

    @property
    def summary(self) -> str:
        return self._summary

    @property
    def timeZone(self) -> str:
        return self._timeZone

    @classmethod
    def from_json(cls, json_obj: dict) -> "CalendarList":
        """
        Constructs a new CalendarList instance from a json object.

        Args:
        - json_obj (dict): The json object from an existing CalendarListEntry.

        Returns:
        - CalendarList: A CalendarList instance.

        Raises:
        - ValueError: If the json object does not have the necessary elements.
        """
        try:
            obj = cls(json_obj["summary"], json_obj["timeZone"])
            obj._id = json_obj["id"]
            obj._etag = json_obj["etag"]
            obj._kind = json_obj["kind"]

            if "accessRole" in json_obj:
                obj._accessRole = json_obj["accessRole"]
            if "conferenceProperties" in json_obj:
                obj._conferenceProperties = json_obj["conferenceProperties"]
            if "deleted" in json_obj:
                obj._deleted = json_obj["deleted"]
            if "description" in json_obj:
                obj._description = json_obj["description"]
            if "location" in json_obj:
                obj._location = json_obj["location"]
            if "primary" in json_obj:
                obj._primary = json_obj["primary"]
            if "colorId" in json_obj:
                obj._colorId = json_obj["colorId"]
            if "backgroundColor" in json_obj:
                obj._backgroundColor = json_obj["backgroundColor"]
            if "foregroundColor" in json_obj:
                obj._foregroundColor = json_obj["foregroundColor"]
            if "hidden" in json_obj:
                obj._hidden = json_obj["hidden"]
            if "selected" in json_obj:
                obj._selected = json_obj["selected"]
            if "summaryOverride" in json_obj:
                obj._summaryOverride = json_obj["summaryOverride"]
            if "defaultReminders" in json_obj:
                obj._defaultReminders = json_obj["defaultReminders"]
            if "notificationSettings" in json_obj:
                obj._notificationSettings = json_obj["notificationSettings"]

            return obj
        except KeyError as e:
            raise ValueError(f"Wrong kind of json_obj: {e} does not exist.")

    def build(self) -> dict:
        """
        Returns the calendar list entry object as a JSON object.

        Returns:
        - dict: The calendar list entry object.
        """
        calendar_list_entry_obj = {
            "id": self._id,
        }

        if self._colorId:
            calendar_list_entry_obj["colorId"] = self._colorId
        if self._backgroundColor:
            calendar_list_entry_obj["backgroundColor"] = self._backgroundColor
        if self._foregroundColor:
            calendar_list_entry_obj["foregroundColor"] = self._foregroundColor
        if self._hidden:
            calendar_list_entry_obj["hidden"] = self._hidden
        if self._selected:
            calendar_list_entry_obj["selected"] = self._selected
        if self._summaryOverride:
            calendar_list_entry_obj["summaryOverride"] = self._summaryOverride
        if self._defaultReminders:
            calendar_list_entry_obj["defaultReminders"] = self._defaultReminders
        if self._notificationSettings:
            calendar_list_entry_obj["notificationSettings"] = self._notificationSettings

        return calendar_list_entry_obj


class Event:
    def __init__(
        self,
        title: str,
        start_date: str,
        end_date: str,
        time_zone: str = "Europe/Brussels",
        date_format: str = "%d/%m/%Y",
    ) -> None:
        self.date_format = date_format

        self.title = title
        self.timeZone = time_zone
        self.start_date = start_date
        self.end_date = end_date

        self._location = ""

    @property
    def title(self) -> str:
        """
        Getter method for title.
        """
        return self._title

    @title.setter
    def title(self, title: str) -> None:
        """
        Setter method for title.
        """
        self._title = title

    @property
    def timeZone(self) -> str:
        """
        Getter method for timeZone.
        """
        return self._time_zone

    @timeZone.setter
    def timeZone(self, time_zone: str) -> None:
        """
        Setter method for timeZone.
        """
        if validate_time_zone(time_zone):
            self._time_zone = time_zone
        else:
            raise ValueError(f"Invalid time zone: {time_zone}")

    @property
    def start_date(self) -> str:
        """
        Getter method for start_date.
        """
        return convert_date(
            self._start_date, reverse=True, input_format=self.date_format
        )

    @start_date.setter
    def start_date(self, start_date: str) -> None:
        """
        Setter method for start_date.
        """
        self._start_date = convert_date(start_date, input_format=self.date_format)

    @property
    def end_date(self) -> str:
        """
        Getter method for end_date.
        """
        return convert_date(
            self._end_date, add_day=True, reverse=True, input_format=self.date_format
        )

    @end_date.setter
    def end_date(self, end_date: str) -> None:
        """
        Setter method for end_date.
        """
        self._end_date = convert_date(
            end_date, add_day=True, input_format=self.date_format
        )

    @property
    def location(self) -> str:
        """
        Getter method for location.
        """
        return self._location

    @location.setter
    def location(self, location: str) -> None:
        """
        Setter method for location.
        """
        self._location = location

    def build(self) -> dict:
        """
        Returns the event object as a JSON object.

        Returns:
        - dict: The event object.
        """
        event_obj = {
            "summary": self._title,
            "start": {"date": self._start_date, "timeZone": self._time_zone},
            "end": {"date": self._end_date, "timeZone": self._time_zone},
        }
        if self._location:
            event_obj["location"] = self._location

        return event_obj


class TimedEvent(Event):
    def __init__(
        self,
        title: str,
        start_date: str,
        start_time: str,
        end_date: str,
        end_time: str,
        time_zone: str = "Europe/Brussels",
        date_format: str = "%d/%m/%Y",
        time_format: str = "%Hu%M",
    ) -> None:
        super().__init__(
            title, start_date, end_date, time_zone=time_zone, date_format=date_format
        )
        self.time_format = time_format

        self.start_time = start_time
        self.end_time = end_time

    @property
    def start_time(self) -> str:
        """
        Getter method for start_time.
        """
        return convert_time(
            self._start_time, reverse=True, input_format=self.time_format
        )

    @start_time.setter
    def start_time(self, start_time: str) -> None:
        """
        Setter method for start_time.
        """
        self._start_time = convert_time(start_time, input_format=self.time_format)

    @property
    def end_date(self) -> str:
        """
        Getter method for end_date.
        """
        return convert_date(self._end_date, reverse=True, input_format=self.date_format)

    @end_date.setter
    def end_date(self, end_date: str) -> None:
        """
        Setter method for end_date.
        """
        self._end_date = convert_date(end_date, input_format=self.date_format)

    @property
    def end_time(self) -> str:
        """
        Getter method for end_time.
        """
        return convert_time(self._end_time, reverse=True, input_format=self.time_format)

    @end_time.setter
    def end_time(self, end_time: str) -> None:
        """
        Setter method for end_time.
        """
        self._end_time = convert_time(end_time, input_format=self.time_format)

    def build(self):
        """
        Returns the timed event object as a dictionary.

        Returns:
            dict: The timed event object.
        """
        event_obj = super().build()

        event_obj["start"].pop("date")
        event_obj["start"]["dateTime"] = f"{self._start_date}T{self._start_time}"

        event_obj["end"].pop("date")
        event_obj["end"]["dateTime"] = f"{self._end_date}T{self._end_time}"

        return event_obj


if __name__ == "__main__":
    # Example usage of the Calendar and Event classes
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    SCOPES = ["https://www.googleapis.com/auth/calendar"]
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    service = build("calendar", "v3", credentials=creds)

    d = "23/06/2024"
    d2 = "23/06/2024"

    t = "22u40"
    t2 = "22u55"

    # calendar = Calendar('title').build()
    event_obj = Event("event", d, d2).build()

    # created_event = service.events().insert(calendarId='primary', body=event_obj).execute()
    # print(created_event)

    calendar = service.calendars().get(calendarId="primary").execute()
    print(calendar)
    page_token = None
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        for calendar_list_entry in calendar_list["items"]:
            print(calendar_list_entry["summary"])
        page_token = calendar_list.get("nextPageToken")
        if not page_token:
            break

    calendar_list_entry = service.calendarList().get(calendarId="primary").execute()
    print(calendar_list_entry)
