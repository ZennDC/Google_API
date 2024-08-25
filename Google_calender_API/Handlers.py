import re

from googleapiclient.errors import HttpError

from Google_API.Google_calender_API.Objects import Event, TimedEvent, Calendar, CalendarList


class EventHandler:
    DATE_PATTERN = r'(\d{1,2}) (\w+) (\d{4})'
    TIME_PATTERN = r'\d{2}:\d{2}'
    NUM = {
        'januari': 1,
        'februari': 2,
        'maart': 3,
        'april': 4,
        'mei': 5,
        'juni': 6,
        'juli': 7,
        'augustus': 8,
        'september': 9,
        'oktober': 10,
        'november': 11,
        'december': 12
    }

    def __init__(self, service) -> 'EventHandler':
        self.service = service

    def planEvent(self, calendar_id: str, event_obj: Event | TimedEvent) -> None:
        try:
            created_event = self.service.events().insert(calendarId=calendar_id, body=event_obj).execute()

            print(f"Event created: {created_event['id']}")
        except HttpError as error:
            print(f"An error occurred: {error}")

    def convert_date(self, date: str) -> str:
        date_match = re.findall(self.DATE_PATTERN, date)[0]
        if not date_match:
            raise ValueError(f'Incorrect date: {date}')
        else:
            try:
                day = int(date_match[0])
                _month = date_match[1]
                month = self.NUM[_month]
                year = int(date_match[2])
            except KeyError as e:
                print(f"Error: Month name '{_month}' not found in self.NUM dictionary.")
            except ValueError as e:
                print(f"Error: Unable to convert to integer - {e}")
            except IndexError as e:
                print(f"Error: Date tuple does not have expected structure - {e}")
            else:
                return f'{day}/{month}/{year}'

    def convert_time(self, time_str: str) -> tuple[str, str]:
        time_match = re.findall(self.TIME_PATTERN, time_str)
        try:
            start_time = time_match[0]
            end_time = time_match[1]
        except IndexError as e:
                print(f"Error: Date tuple does not have expected structure - {e}")
        else:
            return start_time, end_time

    @staticmethod
    def is_greater(time1: str, time2: str) -> bool:
        try:
            # Extract hours and minutes from time1 and time2
            h1, m1 = map(int, time1.split(':'))
            h2, m2 = map(int, time2.split(':'))

            # Convert times to total minutes
            total_minutes1 = h1 * 60 + m1
            total_minutes2 = h2 * 60 + m2

            # Compare total minutes
            return True if total_minutes1 >= total_minutes2 else False

        except ValueError:
            # Handle ValueError if time1 or time2 are not in the correct format
            print("Invalid time format. Please use 'hh:mm'.")


class CalendarHandler:
    def __init__(self, service) -> 'CalendarHandler':
        self.service = service

    def get_calendar_id(self, calendar_name: str) -> str | None:
        try:
            calendar_list = self.service.calendarList().list().execute()

            # Check if calendar with specific name exists
            for calendar in calendar_list.get('items', []):
                if calendar['summary'] == calendar_name:
                    return calendar['id']
        
            return None
        except HttpError as error:
            print(f"An error occurred: {error}")

    def create_calendar(self, calendar_obj: Calendar) -> str:
        try:
            created_calendar = self.service.calendars().insert(body=calendar_obj).execute()
            return created_calendar['id']

            print(f"Event created: {created_calendar['id']}")
        except HttpError as error:
            print(f"An error occurred: {error}")

    def clear_calendar(self, calendar_name: str) -> None:
        try:
            id = self.get_calendar_id(calendar_name)
            if id:
                self.service.calendars().clear(id).execute()
            else:
                print(f'Calendar {calendar_name} does not exist.')
        except HttpError as error:
            print(f"An error occurred: {error}")

    def delete_calendar(self, calendar_name: str) -> None:
        try:
            id = self.get_calendar_id(calendar_name)
            if id:
                self.service.calendars().delete(calendarId=id).execute()
            else:
                print(f'Calendar {calendar_name} does not exist.')
        except HttpError as error:
            print(f"An error occurred: {error}")

    def get_calendar(self, calendar_name: str) -> dict:
        try:
            id = self.get_calendar_id(calendar_name)
            if id:
                calendar = self.service.calendars().get(calendarId=id).execute()
                return calendar
            else:
                print(f'Calendar {calendar_name} does not exist.')
        except HttpError as error:
            print(f"An error occurred: {error}")

    def update_calendar(self, calendar_name: str, body: dict) -> None:
        try:
            id = self.get_calendar_id(calendar_name)
            if id:
                self.service.calendars().update(calendarId=id, body=body).execute()
            else:
                print(f'Calendar {calendar_name} does not exist.')
        except HttpError as error:
            print(f"An error occurred: {error}")

    #functions based on calendarList
    def delete_calendar_from_list(self, calendar_name: str) -> None:
        try:
            id = self.get_calendar_id(calendar_name)
            if id:
                self.service.calendarList().delete(calendarId=id).execute()
            else:
                print(f'Calendar {calendar_name} does not exist.')
        except HttpError as error:
            print(f"An error occurred: {error}")

    def get_calendar_list_entry(self, calendar_name: str) -> dict:
        try:
            id = self.get_calendar_id(calendar_name)
            if id:
                calendar_list_entry = self.service.calendarList().get(calendarId=id).execute()
                return calendar_list_entry
            else:
                print(f'Calendar {calendar_name} does not exist.')
        except HttpError as error:
            print(f"An error occurred: {error}")

    def add_existing_calendar(self, calendar_list_entry: dict) -> dict:
        try:
            self.service.calendarList().insert(body=calendar_list_entry).execute()

        except HttpError as error:
            print(f"An error occurred: {error}")

    def list_all_calendars(self) -> list:
        page_token = None
        calendars = []
        while True:
            calendar_list = self.service.calendarList().list(pageToken=page_token).execute()
            for calendar_list_entry in calendar_list['items']:
                calendars.append(calendar_list_entry['summary'])
            page_token = calendar_list.get('nextPageToken')
            if not page_token:
                break

    def update_calendar(self, calendar_name: str, body: dict) -> None:
        try:
            id = self.get_calendar_id(calendar_name)
            if id:
                self.service.calendarList().update(calendarId=body['id'], body=body).execute()
            else:
                print(f'Calendar {calendar_name} does not exist.')
        except HttpError as error:
            print(f"An error occurred: {error}")

    