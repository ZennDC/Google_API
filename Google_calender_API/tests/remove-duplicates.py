import datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from Google_calender_API.handlers import EventHandler
from OAuth import get_credentials

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def main():
    try:
        creds = get_credentials(SCOPES)
        service = build("calendar", "v3", credentials=creds)
        event_handler = EventHandler(service)

        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime(
            "%d/%m/%Y"
        )
        print(f"Checking for and removing duplicates on: {tomorrow}")
        event_handler.removeDuplicates("primary", tomorrow)
        print("Duplicate check complete.")

    except HttpError as error:
        print(f"An error occurred: {error}")


if __name__ == "__main__":
    main()
