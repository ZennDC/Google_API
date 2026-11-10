from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from Google_calender_API.handlers import CalendarHandler
from OAuth import get_credentials

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def main():
    try:
        creds = get_credentials(scopes=SCOPES)
        service = build("calendar", "v3", credentials=creds)
        cal_handler = CalendarHandler(service)

        calendar_id = cal_handler.get_calendar_id("primary")
        print(f"Primary calendar retrieved: {calendar_id}")

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
