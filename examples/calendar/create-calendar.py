from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from google_calendar_api.handlers import CalendarHandler
from google_calendar_api.objects import Calendar
from oauth import get_credentials

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def main():
    try:
        creds = get_credentials(SCOPES)
        service = build("calendar", "v3", credentials=creds)
        cal_handler = CalendarHandler(service)

        calendar_name = "Test Calendar"
        existing_id = cal_handler.get_calendar_id(calendar_name)
        if existing_id:
            print(f'Calendar "{calendar_name}" already exists with ID: {existing_id}')
        else:
            new_calendar = Calendar(calendar_name).build()
            new_id = cal_handler.create_calendar(new_calendar)
            print(f'Created calendar "{calendar_name}" with ID: {new_id}')

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
